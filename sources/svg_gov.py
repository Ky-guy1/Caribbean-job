"""Source #2 — St. Vincent & the Grenadines Public Service Commission vacancies."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from sources.base import JobSource, ScrapeResult
from sources.normalize import build_job_record, clean_text

SITE_BASE = "https://psc.gov.vc"
LISTING_URL = f"{SITE_BASE}/psc/index.php/vacancies"
DEFAULT_COMPANY = "SVG Public Service Commission"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class SvgGovSource(JobSource):
    label = "SVG Gov"
    slug = "svggov"
    listing_url = LISTING_URL

    def __init__(self, use_local_mock: bool = False, mock_path: Path | None = None) -> None:
        self.use_local_mock = use_local_mock
        self.mock_path = mock_path

    def _fetch_html(self) -> str:
        if self.use_local_mock:
            if not self.mock_path or not self.mock_path.is_file():
                raise FileNotFoundError(f"Mock file missing: {self.mock_path}")
            return self.mock_path.read_text(encoding="utf-8")

        response = requests.get(
            self.listing_url,
            headers=REQUEST_HEADERS,
            timeout=20,
            verify=True,
        )
        response.raise_for_status()
        return response.text

    def _parse_vacancy_links(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        seen_titles: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if "/Vacancies/" not in href or not href.lower().endswith(".pdf"):
                continue

            title = clean_text(anchor.get_text(strip=True))
            if not title or title.lower() in {"vacancies", "home"}:
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)

            url = urljoin(SITE_BASE, href)
            filename = href.rsplit("/", 1)[-1].replace(".pdf", "")
            jobs.append(
                build_job_record(
                    source_label=self.label,
                    source_slug=self.slug,
                    title=title,
                    company=DEFAULT_COMPANY,
                    url=url,
                    unique_part=filename,
                )
            )

        return jobs

    def scrape(self) -> ScrapeResult:
        try:
            html = self._fetch_html()
            soup = BeautifulSoup(html, "html.parser")
            jobs = self._parse_vacancy_links(soup)
            return ScrapeResult(
                source_label=self.label,
                source_url="mock_svg_vacancies.html" if self.use_local_mock else self.listing_url,
                jobs=jobs,
            )
        except Exception as exc:
            return ScrapeResult(
                source_label=self.label,
                source_url=self.listing_url,
                jobs=[],
                error=str(exc),
            )
