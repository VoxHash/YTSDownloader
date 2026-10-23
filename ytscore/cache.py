"""In-memory title cache with hit/miss stats."""

from __future__ import annotations

from typing import Dict, Optional


class TitleCache:
    def __init__(self) -> None:
        self._titles: Dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    def get(self, link: str) -> Optional[str]:
        title = self._titles.get(link)
        if title:
            self.hits += 1
            return title
        self.misses += 1
        return None

    def put(self, link: str, title: Optional[str]) -> None:
        if link and title and link not in self._titles:
            self._titles[link] = title

    def reset_stats(self) -> None:
        self.hits = 0
        self.misses = 0

    def status_text(self) -> str:
        total = self.hits + self.misses
        ratio = (self.hits / total * 100) if total else 0.0
        return f"Metadata cache - hits: {self.hits} | misses: {self.misses} | hit ratio: {ratio:.1f}%"


title_cache = TitleCache()
