"""Local session analytics counters (no network telemetry)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


def format_duration(seconds: float) -> str:
    """Human-readable duration for status bar (e.g. 12.4s, 1m05.0s)."""
    if seconds < 0:
        seconds = 0.0
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    rem = seconds - (minutes * 60)
    return f"{minutes}m{rem:04.1f}s"


@dataclass
class SessionAnalytics:
    """In-memory success / error / timing counters for the current Suite session."""

    success_count: int = 0
    error_count: int = 0
    last_duration_s: Optional[float] = None
    _duration_sum: float = field(default=0.0, repr=False)
    _timed_count: int = field(default=0, repr=False)

    def reset(self) -> None:
        self.success_count = 0
        self.error_count = 0
        self.last_duration_s = None
        self._duration_sum = 0.0
        self._timed_count = 0

    def record_success(self, duration_s: Optional[float] = None) -> None:
        self.success_count += 1
        self._note_duration(duration_s)

    def record_failure(self, duration_s: Optional[float] = None) -> None:
        self.error_count += 1
        self._note_duration(duration_s)

    def _note_duration(self, duration_s: Optional[float]) -> None:
        if duration_s is None or duration_s < 0:
            return
        self.last_duration_s = float(duration_s)
        self._duration_sum += float(duration_s)
        self._timed_count += 1

    @property
    def average_duration_s(self) -> Optional[float]:
        if self._timed_count <= 0:
            return None
        return self._duration_sum / self._timed_count

    def format_status(self) -> str:
        """Compact status-bar text: OK / Err / Last / Avg."""
        parts = [f"OK:{self.success_count}", f"Err:{self.error_count}"]
        if self.last_duration_s is not None:
            parts.append(f"Last:{format_duration(self.last_duration_s)}")
        avg = self.average_duration_s
        if avg is not None:
            parts.append(f"Avg:{format_duration(avg)}")
        return "  ".join(parts)
