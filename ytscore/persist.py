"""Local JSON persistence for the download queue (survives Suite restarts)."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ytscore.queue import JobState, QueueJob

SCHEMA_VERSION = 1
RESTORED_MESSAGE = "Restored — press Start Queue to resume"

# Project-local (cwd), gitignored via `.ytsdownloader/`.
DEFAULT_STATE_DIR = ".ytsdownloader"
DEFAULT_STATE_FILE = "queue_state.json"


def default_queue_state_path() -> str:
    """Return the default path for queue state JSON (under `.ytsdownloader/`)."""
    return os.path.join(DEFAULT_STATE_DIR, DEFAULT_STATE_FILE)


def job_to_dict(job: QueueJob) -> Dict[str, Any]:
    return {
        "id": job.id,
        "url": job.url,
        "title": job.title,
        "media": job.media,
        "state": job.state.value if isinstance(job.state, JobState) else str(job.state),
        "progress": float(job.progress),
        "message": job.message or "",
        "path": job.path,
        "error": job.error,
        "index": job.index,
        "search_query": job.search_query,
    }


def normalize_restored_state(state: JobState) -> Tuple[JobState, Optional[str]]:
    """
    Map persisted states to safe restore values.

    RUNNING at crash/exit becomes QUEUED (not auto-started). Terminal and
    pending states are kept. Returns (state, override_message_or_None).
    """
    if state == JobState.RUNNING:
        return JobState.QUEUED, RESTORED_MESSAGE
    return state, None


def job_from_dict(data: Dict[str, Any], *, remap_running: bool = True) -> QueueJob:
    raw_state = str(data.get("state") or JobState.QUEUED.value).lower()
    try:
        state = JobState(raw_state)
    except ValueError:
        state = JobState.QUEUED

    message = str(data.get("message") or "")
    if remap_running:
        state, override = normalize_restored_state(state)
        if override is not None:
            message = override

    return QueueJob(
        id=str(data.get("id") or ""),
        url=str(data.get("url") or ""),
        title=str(data.get("title") or data.get("url") or ""),
        media=str(data.get("media") or "video"),
        state=state,
        progress=float(data.get("progress") or 0.0),
        message=message,
        path=data.get("path"),
        error=data.get("error"),
        index=data.get("index"),
        search_query=data.get("search_query"),
    )


def serialize_queue_snapshot(
    *,
    jobs: List[QueueJob],
    output_dir: str,
    watermark_path: str = "",
    output_format: str = "mp4",
) -> Dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "output_dir": output_dir,
        "watermark_path": watermark_path or "",
        "output_format": output_format or "mp4",
        "jobs": [job_to_dict(j) for j in jobs],
    }


def deserialize_queue_snapshot(
    data: Dict[str, Any],
    *,
    remap_running: bool = True,
) -> Tuple[List[QueueJob], Dict[str, Any]]:
    """Return (jobs, meta) where meta has output_dir / watermark_path / output_format."""
    jobs_raw = data.get("jobs") or []
    if not isinstance(jobs_raw, list):
        jobs_raw = []
    jobs = [
        job_from_dict(item, remap_running=remap_running)
        for item in jobs_raw
        if isinstance(item, dict) and item.get("url")
    ]
    for j in jobs:
        if not j.id:
            j.id = str(uuid.uuid4())
    meta = {
        "version": int(data.get("version") or SCHEMA_VERSION),
        "output_dir": str(data.get("output_dir") or ""),
        "watermark_path": str(data.get("watermark_path") or ""),
        "output_format": str(data.get("output_format") or "mp4"),
    }
    return jobs, meta


def save_queue_state(path: str, snapshot: Dict[str, Any]) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def load_queue_state(path: str) -> Optional[Dict[str, Any]]:
    if not path or not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        return None
    return data


def clear_queue_state_file(path: str) -> None:
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
