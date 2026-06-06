"""
Multi-source Caribbean job scraper engine.

Source #1 — CaribbeanJobs.com (regional private-sector listings)
Source #2 — SVG Public Service Commission (psc.gov.vc government vacancies)

HOW TO RUN:
  pip install -r requirements.txt
  python scraper.py              # live scrape both sources
  python server.py               # job board UI

  USE_LOCAL_FILE = True          # use mock_jobs.html + mock_svg_vacancies.html

Note: Respect each site's terms of use and robots.txt.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import database as db
from sources import CaribbeanJobsSource, ScrapeResult, SvgGovSource
from sources.base import JobSource

PROJECT_DIR = Path(__file__).resolve().parent
JOBS_JSON = PROJECT_DIR / "jobs.json"
MOCK_CARIBBEAN_HTML = PROJECT_DIR / "mock_jobs.html"
MOCK_SVG_HTML = PROJECT_DIR / "mock_svg_vacancies.html"

# Set True to read local HTML mocks instead of live websites.
USE_LOCAL_FILE = False

SCHEMA_VERSION = 2


def get_sources() -> list[JobSource]:
    return [
        CaribbeanJobsSource(
            use_local_mock=USE_LOCAL_FILE,
            mock_path=MOCK_CARIBBEAN_HTML,
        ),
        SvgGovSource(
            use_local_mock=USE_LOCAL_FILE,
            mock_path=MOCK_SVG_HTML,
        ),
    ]


def run_engine(sources: list[JobSource]) -> list[ScrapeResult]:
    results: list[ScrapeResult] = []
    for source in sources:
        print(f"-- {source.label} --")
        print(f"   URL: {source.listing_url}")
        result = source.scrape()
        if result.ok:
            print(f"   OK: {len(result.jobs)} job(s)")
        else:
            print(f"   FAILED: {result.error}")
        results.append(result)
        print()
    return results


def merge_jobs(results: list[ScrapeResult]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for result in results:
        for job in result.jobs:
            ext_id = job["external_id"]
            if ext_id in seen_ids:
                continue
            seen_ids.add(ext_id)
            merged.append(job)
    return merged


def build_export_payload(
    jobs: list[dict[str, Any]],
    results: list[ScrapeResult],
    scraped_at: str,
) -> dict[str, Any]:
    by_category: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for job in jobs:
        by_category[job["category"]] = by_category.get(job["category"], 0) + 1
        by_source[job["source"]] = by_source.get(job["source"], 0) + 1

    source_meta = []
    for r in results:
        source_meta.append(
            {
                "id": r.source_label,
                "url": r.source_url,
                "count": len(r.jobs),
                "status": "ok" if r.ok else "error",
                "error": r.error,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "scraped_at": scraped_at,
        "count": len(jobs),
        "sources": source_meta,
        "summary": {
            "by_category": by_category,
            "by_source": by_source,
        },
        "jobs": jobs,
    }


def persist_jobs(jobs: list[dict[str, Any]], scraped_at: str, payload: dict[str, Any]) -> None:
    JOBS_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    db.init_db()
    db.upsert_jobs(jobs, scraped_at)


def main() -> None:
    scraped_at = datetime.now(timezone.utc).isoformat()
    mode = "LOCAL MOCK" if USE_LOCAL_FILE else "LIVE"
    print(f"Caribbean Finder - multi-source scrape [{mode}]\n")

    results = run_engine(get_sources())
    jobs = merge_jobs(results)

    successes = [r for r in results if r.ok and r.jobs]
    if not jobs:
        errors = [r.error for r in results if r.error]
        print("No jobs collected from any source.", file=sys.stderr)
        if errors:
            for err in errors:
                print(f"  • {err}", file=sys.stderr)
        raise SystemExit(1)

    payload = build_export_payload(jobs, results, scraped_at)
    persist_jobs(jobs, scraped_at, payload)

    print(f"Saved {payload['count']} job(s) -> {JOBS_JSON.name}, {db.DB_PATH.name}")
    print(f"By source: {payload['summary']['by_source']}")
    print(f"By category: {payload['summary']['by_category']}\n")

    for i, job in enumerate(jobs, start=1):
        print(
            f"{i}. [{job['source']}] [{job['category']}] "
            f"{job['title']} @ {job['company']}"
        )

    failed = [r for r in results if not r.ok]
    if failed:
        print(f"\nWarning: {len(failed)} source(s) failed; partial data saved.")

    subs = db.subscription_count()
    if subs:
        print(f"\n{subs} WhatsApp alert subscription(s) ready for notifier.py")

    print("\nNext: python server.py -> http://localhost:8000")


if __name__ == "__main__":
    main()
