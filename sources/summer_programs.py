"""Source — youth development & summer program listings (mock data for testing)."""

from __future__ import annotations

from typing import Any

from sources.base import JobSource, ScrapeResult
from sources.normalize import build_job_record

MOCK_SUMMER_PROGRAMS: tuple[dict[str, str], ...] = (
    {
        "title": "SVG Ministry of Tourism Kids Camp",
        "company": "SVG Ministry of Tourism",
        "url": "https://www.gov.vc/youth/kids-camp",
    },
    {
        "title": "NTRC Caribbean Coding Workshop",
        "company": "NTRC",
        "url": "https://www.ntrc.gov.vc/coding-workshop",
    },
    {
        "title": "SVG Coast Guard Youth Program",
        "company": "SVG Coast Guard",
        "url": "https://www.coastguard.gov.vc/youth-program",
    },
)


class SummerProgramsSource(JobSource):
    label = "Youth Programs"
    slug = "summer-programs"
    listing_url = "mock://summer-programs"

    def scrape(self) -> ScrapeResult:
        programs: list[dict[str, Any]] = []
        for entry in MOCK_SUMMER_PROGRAMS:
            record = build_job_record(
                source_label=self.label,
                source_slug=self.slug,
                title=entry["title"],
                company=entry["company"],
                url=entry["url"],
                unique_part=entry["title"],
                listing_type="Summer Program",
            )
            programs.append(record)
        return ScrapeResult(
            source_label=self.label,
            source_url=self.listing_url,
            jobs=programs,
        )
