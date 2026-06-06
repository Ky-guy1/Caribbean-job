"""Job listing source plugins for the multi-source scraper."""

from sources.base import JobSource, ScrapeResult
from sources.caribbean_jobs import CaribbeanJobsSource
from sources.summer_programs import SummerProgramsSource
from sources.svg_gov import SvgGovSource

__all__ = [
    "JobSource",
    "ScrapeResult",
    "CaribbeanJobsSource",
    "SummerProgramsSource",
    "SvgGovSource",
]
