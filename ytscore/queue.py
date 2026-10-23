"""Concurrent download queue with retries and progress callbacks."""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

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
            )
            self._jobs[job.id] = job
            self._order.append(job.id)
        self._emit(job)
        if self._running:
            self._submit(job)
        return job

    def add_many(self, urls: List[str], *, media: str = "video") -> List[QueueJob]:
        return [self.add(u, media=media) for u in urls]

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._executor = ThreadPoolExecutor(max_workers=self.settings.max_workers)
            pending = [self._jobs[i] for i in self._order if self._jobs[i].state == JobState.QUEUED]
        for job in pending:
            self._submit(job)

    def stop(self) -> None:
        with self._lock:
            self._running = False
            ex = self._executor
            self._executor = None
            futures = list(self._futures.values())
            self._futures.clear()
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

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.state == JobState.CANCELLED:
                return
            job.state = JobState.RUNNING
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
                result = download_item(
                    job.url,
                    self.output_dir,
                    self.settings,
                    media=job.media,
                    index=job.index,
                    watermark_path=self.watermark_path,
                    output_format=self.output_format,
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
            if self.settings.pace_seconds > 0:
                time.sleep(self.settings.pace_seconds)
        except Exception as exc:
            with self._lock:
                job.state = JobState.FAILED
                job.error = str(exc)
                job.message = str(exc)
        finally:
            with self._lock:
                self._futures.pop(job_id, None)
            self._emit(job)
