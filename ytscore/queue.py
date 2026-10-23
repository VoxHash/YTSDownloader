"""Concurrent download queue with retries, playlist pacing, and progress callbacks."""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Set

from ytscore.backoff import compute_backoff_seconds
from ytscore.downloader import download_item, search_and_download_audio
from ytscore.settings import Settings


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueJob:
    id: str
    url: str
    title: str = ""
    media: str = "video"  # video | audio | search_audio
    state: JobState = JobState.QUEUED
    progress: float = 0.0
    message: str = ""
    path: Optional[str] = None
    error: Optional[str] = None
    index: Optional[int] = None
    search_query: Optional[str] = None
    # Per-job export options. None = inherit queue defaults at download time.
    watermark_path: Optional[str] = None
    output_format: Optional[str] = None


Listener = Callable[[QueueJob], None]


@dataclass
class DownloadQueue:
    settings: Settings
    output_dir: str
    watermark_path: str = ""
    output_format: str = "mp4"
    _jobs: Dict[str, QueueJob] = field(default_factory=dict)
    _order: List[str] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _executor: Optional[ThreadPoolExecutor] = field(default=None, repr=False)
    _futures: Dict[str, Future] = field(default_factory=dict, repr=False)
    _listeners: List[Listener] = field(default_factory=list, repr=False)
    _running: bool = False
    _counter: int = 0
    # Playlist pacing: serialize job *starts* so concurrent workers still space work.
    _pace_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _next_start_at: float = field(default=0.0, repr=False)
    # Job ids that skip the next pace wait (force download / prioritize).
    _force_ids: Set[str] = field(default_factory=set, repr=False)

    def add_listener(self, cb: Listener) -> None:
        self._listeners.append(cb)

    def _emit(self, job: QueueJob) -> None:
        for cb in list(self._listeners):
            try:
                cb(job)
            except Exception:
                pass

    def jobs(self) -> List[QueueJob]:
        with self._lock:
            return [self._jobs[i] for i in self._order]

    def add(
        self,
        url: str,
        *,
        media: str = "video",
        title: str = "",
        search_query: Optional[str] = None,
        watermark_path: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> QueueJob:
        with self._lock:
            self._counter += 1
            job = QueueJob(
                id=str(uuid.uuid4()),
                url=url,
                title=title or url,
                media=media,
                index=self._counter,
                search_query=search_query,
                watermark_path=(
                    self.watermark_path if watermark_path is None else watermark_path
                ),
                output_format=(
                    self.output_format if output_format is None else output_format
                ),
            )
            self._jobs[job.id] = job
            self._order.append(job.id)
        self._emit(job)
        if self._running:
            self._submit(job)
        return job

    def add_many(
        self,
        urls: List[str],
        *,
        media: str = "video",
        watermark_path: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> List[QueueJob]:
        return [
            self.add(
                u,
                media=media,
                watermark_path=watermark_path,
                output_format=output_format,
            )
            for u in urls
        ]

    def get(self, job_id: str) -> Optional[QueueJob]:
        with self._lock:
            return self._jobs.get(job_id)

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def apply_export_options(
        self,
        job_ids: Optional[List[str]],
        *,
        media: str,
        watermark_path: str = "",
        output_format: str = "",
        only_states: Optional[List[JobState]] = None,
    ) -> int:
        """
        Update export options on jobs. If job_ids is None, all jobs (optionally
        filtered by only_states) are updated. Skips search_audio. Returns count.
        """
        touched: List[QueueJob] = []
        with self._lock:
            if job_ids is None:
                targets = [self._jobs[i] for i in self._order]
            else:
                targets = [self._jobs[i] for i in job_ids if i in self._jobs]
            for job in targets:
                if only_states is not None and job.state not in only_states:
                    continue
                if job.media == "search_audio":
                    continue
                job.media = media
                job.watermark_path = watermark_path or ""
                if output_format:
                    job.output_format = output_format
                touched.append(job)
        for job in touched:
            self._emit(job)
        return len(touched)

    def clear_terminal(self) -> int:
        """Remove DONE / FAILED / CANCELLED jobs. Returns how many were removed."""
        terminal = {JobState.DONE, JobState.FAILED, JobState.CANCELLED}
        with self._lock:
            keep_ids = [i for i in self._order if self._jobs[i].state not in terminal]
            removed = len(self._order) - len(keep_ids)
            self._order = keep_ids
            self._jobs = {i: self._jobs[i] for i in keep_ids}
            # Drop futures for removed ids (should already be idle).
            for jid in list(self._futures):
                if jid not in self._jobs:
                    self._futures.pop(jid, None)
            self._force_ids &= set(self._jobs)
        return removed

    def remove_jobs(self, job_ids: List[str]) -> int:
        """Remove specific jobs (cancels running futures). Returns how many were removed."""
        if not job_ids:
            return 0
        cancel_futs: List[Future] = []
        with self._lock:
            removed = 0
            for jid in job_ids:
                if jid not in self._jobs:
                    continue
                job = self._jobs[jid]
                if job.state == JobState.RUNNING:
                    job.state = JobState.CANCELLED
                fut = self._futures.pop(jid, None)
                if fut is not None:
                    cancel_futs.append(fut)
                del self._jobs[jid]
                if jid in self._order:
                    self._order.remove(jid)
                self._force_ids.discard(jid)
                removed += 1
        for fut in cancel_futs:
            fut.cancel()
        return removed

    def clear_all(self) -> int:
        """Remove every job and cancel in-flight futures. Returns how many were removed."""
        cancel_futs: List[Future] = []
        with self._lock:
            removed = len(self._order)
            cancel_futs = list(self._futures.values())
            self._futures.clear()
            self._jobs.clear()
            self._order.clear()
            self._force_ids.clear()
        for fut in cancel_futs:
            fut.cancel()
        return removed

    def force_download(self, job_id: str) -> bool:
        """
        Prioritize one job and start it immediately.

        Moves the job to the front of the queue, re-queues terminal states while
        preserving URL / media / export options, skips playlist pacing for that
        start, and ensures a worker pool is running so the job proceeds even if
        the queue was stopped. Returns False if the id is unknown.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if job.state == JobState.RUNNING:
                # Already in flight — skip remaining pace wait if still waiting.
                self._force_ids.add(job_id)
                return True

            if job.state != JobState.QUEUED:
                fut = self._futures.pop(job_id, None)
                if fut is not None:
                    fut.cancel()
                job.state = JobState.QUEUED
                job.progress = 0.0
                job.error = None
                job.path = None
            job.message = "Force download"
            if job_id in self._order:
                self._order.remove(job_id)
            self._order.insert(0, job_id)
            self._force_ids.add(job_id)

            if self._executor is None:
                self._running = True
                self._executor = ThreadPoolExecutor(max_workers=self.settings.max_workers)
            elif not self._running:
                # Executor may linger after a force-only path; keep accepting work.
                self._running = True

            existing = self._futures.get(job_id)
            need_submit = existing is None or existing.done()
            if need_submit and existing is not None:
                self._futures.pop(job_id, None)
            submit_job = job

        if need_submit:
            self._submit(submit_job)
        self._emit(job)
        return True

    def retry_jobs(
        self,
        job_ids: Optional[List[str]] = None,
        *,
        only_states: Optional[List[JobState]] = None,
    ) -> int:
        """
        Re-queue jobs for another attempt.

        Resets state/progress/error/message/path while preserving URL, title,
        media, search query, and export options. Default eligible states are
        FAILED and CANCELLED. If the queue is running, jobs are submitted.
        Returns how many jobs were re-queued.
        """
        eligible = set(only_states or (JobState.FAILED, JobState.CANCELLED))
        touched: List[QueueJob] = []
        with self._lock:
            if job_ids is None:
                targets = [self._jobs[i] for i in self._order]
            else:
                targets = [self._jobs[i] for i in job_ids if i in self._jobs]
            for job in targets:
                if job.state not in eligible:
                    continue
                # Drop any stale future handle (terminal jobs should already be idle).
                self._futures.pop(job.id, None)
                job.state = JobState.QUEUED
                job.progress = 0.0
                job.error = None
                job.path = None
                job.message = "Queued for retry"
                touched.append(job)
        for job in touched:
            self._emit(job)
            if self._running:
                self._submit(job)
        return len(touched)

    def retry_failed(self) -> int:
        """Re-queue every FAILED job. Returns how many were re-queued."""
        return self.retry_jobs(None, only_states=[JobState.FAILED])

    def restore_jobs(self, jobs: List[QueueJob]) -> None:
        """Replace queue contents with restored jobs (caller applies remap rules)."""
        with self._lock:
            self._jobs = {}
            self._order = []
            max_index = 0
            for job in jobs:
                self._jobs[job.id] = job
                self._order.append(job.id)
                if job.index is not None:
                    max_index = max(max_index, int(job.index))
            self._counter = max(self._counter, max_index)
            self._futures.clear()

    def start(self) -> None:
        with self._lock:
            if not self._running or self._executor is None:
                self._running = True
                self._executor = ThreadPoolExecutor(max_workers=self.settings.max_workers)
            pending = [
                self._jobs[i]
                for i in self._order
                if self._jobs[i].state == JobState.QUEUED and i not in self._futures
            ]
        for job in pending:
            self._submit(job)

    def stop(self) -> None:
        with self._lock:
            self._running = False
            ex = self._executor
            self._executor = None
            futures = list(self._futures.values())
            self._futures.clear()
            self._force_ids.clear()
        for fut in futures:
            fut.cancel()
        if ex:
            ex.shutdown(wait=False, cancel_futures=True)

    def _submit(self, job: QueueJob) -> None:
        with self._lock:
            if not self._executor or job.state not in (JobState.QUEUED,):
                return
            fut = self._executor.submit(self._run_job, job.id)
            self._futures[job.id] = fut

    def _wait_for_pace_slot(self, job: QueueJob) -> None:
        """Block until the shared playlist start slot is free, then reserve the next gap."""
        pace = max(0.0, float(self.settings.pace_seconds))
        while True:
            with self._lock:
                if job.id in self._force_ids:
                    self._force_ids.discard(job.id)
                    return
                if job.state == JobState.CANCELLED:
                    return
            with self._pace_lock:
                now = time.monotonic()
                wait = self._next_start_at - now
                if wait <= 0:
                    self._next_start_at = now + pace
                    return
            with self._lock:
                if job.state == JobState.CANCELLED:
                    return
                if job.id in self._force_ids:
                    self._force_ids.discard(job.id)
                    return
                job.message = f"Pacing {wait:.1f}s…"
            self._emit(job)
            time.sleep(min(wait, 0.25))

    def _extend_global_cooldown(self, seconds: float) -> None:
        """Push the next start slot out (used after rate-limit failures)."""
        if seconds <= 0:
            return
        with self._pace_lock:
            now = time.monotonic()
            self._next_start_at = max(self._next_start_at, now + seconds)

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.state == JobState.CANCELLED:
                return
            job.state = JobState.RUNNING
            job.message = "Waiting for pace slot…"
        self._emit(job)

        self._wait_for_pace_slot(job)
        with self._lock:
            if job.state == JobState.CANCELLED:
                return
            job.message = "Downloading…"
        self._emit(job)

        def hook(d: dict) -> None:
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes") or 0
                pct = (done / total * 100.0) if total else 0.0
                with self._lock:
                    job.progress = min(99.0, pct)
                    job.message = d.get("_percent_str") or f"{pct:.1f}%"
                self._emit(job)

        try:
            if job.media == "search_audio" or job.search_query:
                result = search_and_download_audio(
                    job.search_query or job.url,
                    self.output_dir,
                    self.settings,
                    progress_hook=hook,
                )
            else:
                wm = (
                    self.watermark_path
                    if job.watermark_path is None
                    else job.watermark_path
                )
                fmt = job.output_format or self.output_format
                result = download_item(
                    job.url,
                    self.output_dir,
                    self.settings,
                    media=job.media,
                    index=job.index,
                    watermark_path=wm,
                    output_format=fmt,
                    progress_hook=hook,
                )
            with self._lock:
                if result.ok:
                    job.state = JobState.DONE
                    job.progress = 100.0
                    job.path = result.path
                    job.title = result.title or job.title
                    job.message = "Done"
                    job.error = None
                else:
                    job.state = JobState.FAILED
                    job.error = result.error
                    job.message = result.error or "Failed"
            if getattr(result, "rate_limited", False):
                # Extra cooldown so sibling playlist workers do not stampede.
                cool = compute_backoff_seconds(
                    1,
                    base=self.settings.backoff_base,
                    factor=self.settings.backoff_factor,
                    maximum=self.settings.backoff_max,
                    rate_limited=True,
                )
                self._extend_global_cooldown(cool)
                with self._lock:
                    if job.state == JobState.FAILED:
                        job.message = f"{job.message} (rate-limit cooldown {cool:.0f}s)"
        except Exception as exc:
            with self._lock:
                job.state = JobState.FAILED
                job.error = str(exc)
                job.message = str(exc)
        finally:
            with self._lock:
                self._futures.pop(job_id, None)
            self._emit(job)
