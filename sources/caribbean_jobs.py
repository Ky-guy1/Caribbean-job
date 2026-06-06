"""Source #1 — CaribbeanJobs.com regional listings."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from sources.base import JobSource, ScrapeResult
from sources.normalize import build_job_record, clean_text

SITE_BASE = "https://www.caribbeanjobs.com"
LISTING_URL = (
    f"{SITE_BASE}/ShowResults.aspx"
    "?Keywords=&Page=1&PerPage=25&SortBy=Most+Recent"
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class CaribbeanJobsSource(JobSource):
    label = "CaribbeanJobs"
    slug = "caribbeanjobs"
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
        )
        response.raise_for_status()
        return response.text

    def _parse_mock(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for listing in soup.select("div.job-listing"):
            title_el = listing.select_one("h2.job-title")
            company_el = listing.select_one("p.company-name")
            if not (title_el and company_el):
                continue
            title = clean_text(title_el.get_text(strip=True))
            company = clean_text(company_el.get_text(strip=True))
            key = (title, company)
            if key in seen:
                continue
            seen.add(key)
            jobs.append(
                build_job_record(
                    source_label=self.label,
                    source_slug=self.slug,
                    title=title,
                    company=company,
                    url=None,
                    unique_part=f"{title}|{company}",
                )
            )
        return jobs

    def _parse_live(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for listing in soup.select("div.job-result"):
            title_el = listing.select_one("div.job-result-title h2 a")
            company_el = listing.select_one("div.job-result-title h3 a")
            if not (title_el and company_el):
                continue

            title = clean_text(title_el.get_text(strip=True))
            company = clean_text(company_el.get_text(strip=True))
            key = (title, company)
            if key in seen:
                continue
            seen.add(key)

            href = title_el.get("href")
            url = urljoin(SITE_BASE, href) if href else None
            match = re.search(r"-Job-(\d+)\.aspx", href or "", re.IGNORECASE)
            unique = match.group(1) if match else f"{title}|{company}"

            jobs.append(
                build_job_record(
                    source_label=self.label,
                    source_slug=self.slug,
                    title=title,
                    company=company,
                    url=url,
                    unique_part=unique,
                )
            )
        return jobs

    def scrape(self) -> ScrapeResult:
        try:
            html = self._fetch_html()
            soup = BeautifulSoup(html, "html.parser")
            jobs = self._parse_mock(soup) if self.use_local_mock else self._parse_live(soup)
            return ScrapeResult(
                source_label=self.label,
                source_url="mock_jobs.html" if self.use_local_mock else self.listing_url,
                jobs=jobs,
            )
        except Exception as exc:
            return ScrapeResult(
                source_label=self.label,
                source_url=self.listing_url,
                jobs=[],
                error=str(exc),
            )
