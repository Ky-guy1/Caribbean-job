"""Base contract for job listing sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScrapeResult:
    source_label: str
    source_url: str
    jobs: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class JobSource(ABC):
    """One scrape target (e.g. CaribbeanJobs.com, SVG PSC)."""

    label: str
    slug: str
    listing_url: str

    @abstractmethod
    def scrape(self) -> ScrapeResult:
        """Fetch and parse listings into normalized job dicts."""
