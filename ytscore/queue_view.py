"""Pure helpers for large-queue Suite table paging, filters, and persist pacing.

Keeps O(n) Qt widget work off the hot progress path: filter/match in Python,
render only one page of matching rows, and debounce JSON snapshots by size.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from ytscore.queue import JobState, QueueJob

# Max QTableWidget rows rendered at once (filtered + paginated).
QUEUE_TABLE_PAGE_SIZE = 250

# Coalesce progress/UI signals onto the main thread.
UI_FLUSH_INTERVAL_MS = 300

# Persist debounce scales with queue size (main-thread serialize + disk write).
PERSIST_DEBOUNCE_SMALL_MS = 500
PERSIST_DEBOUNCE_LARGE_MS = 3500
PERSIST_LARGE_THRESHOLD = 400

# Minimum gap between progress-only listener emits (state changes always emit).
PROGRESS_EMIT_MIN_INTERVAL_S = 0.35


def job_matches_filters(
    job: QueueJob,
    state_want: str = "",
    needle: str = "",
) -> bool:
    """Return True if job passes the Suite state + search filters."""
    state_key = (state_want or "").strip().lower()
    if state_key:
        state_val = (
            job.state.value if isinstance(job.state, JobState) else str(job.state)
        ).lower()
        if state_val != state_key:
            return False
    text = (needle or "").strip().lower()
    if not text:
        return True
    hay = " ".join(
        [
            job.title or "",
            job.url or "",
            job.message or "",
            job.error or "",
            (job.media or ""),
            (
                job.state.value
                if isinstance(job.state, JobState)
                else str(job.state or "")
            ),
        ]
    ).lower()
    return text in hay


def filter_jobs(
    jobs: Sequence[QueueJob],
    state_want: str = "",
    needle: str = "",
) -> List[QueueJob]:
    """Filter jobs without touching Qt widgets."""
    if not state_want and not (needle or "").strip():
        return list(jobs)
    return [j for j in jobs if job_matches_filters(j, state_want, needle)]


def paginate_jobs(
    jobs: Sequence[QueueJob],
    page: int,
    page_size: int = QUEUE_TABLE_PAGE_SIZE,
) -> Tuple[List[QueueJob], int, int, int]:
    """
    Return (page_items, page_index, total_pages, matched_total).

    ``page`` is 0-based and clamped into range. Empty lists yield page 0 / 1 page.
    """
    size = max(1, int(page_size))
    total = len(jobs)
    pages = max(1, (total + size - 1) // size) if total else 1
    page_i = max(0, min(int(page), pages - 1))
    start = page_i * size
    end = start + size
    return list(jobs[start:end]), page_i, pages, total


def persist_debounce_ms(job_count: int) -> int:
    """Longer debounce for large queues so we do not rewrite huge JSON every tick."""
    if job_count >= PERSIST_LARGE_THRESHOLD:
        return PERSIST_DEBOUNCE_LARGE_MS
    return PERSIST_DEBOUNCE_SMALL_MS


def persist_json_indent(job_count: int) -> Optional[int]:
    """Pretty-print small queues; compact JSON for large N (faster + smaller)."""
    if job_count >= PERSIST_LARGE_THRESHOLD:
        return None
    return 2
