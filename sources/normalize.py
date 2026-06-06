"""Shared normalization helpers for all job sources."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_INVISIBLE_CHARS = "\u200b\u200c\u200d\ufeff"

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Tech": (
        "developer", "engineer", "software", "it ", " it", "data", "cloud",
        "cyber", "network", "programmer", "analyst", "technical", "devops",
        "support specialist", "application", "systems", "database",
    ),
    "Admin": (
        "admin", "clerk", "receptionist", "assistant", "hr ", "human resource",
        "office", "coordinator", "secretary", "accountant", "payroll",
        "finance manager", "executive assistant", "operations manager",
        "immigration", "counsel", "prosecution", "planner", "officer",
    ),
    "Retail": (
        "sales", "retail", "customer service", "call center", "cashier", "store",
        "shopper", "merchandis", "collections", "agent", "representative", "bpo",
    ),
}


def clean_text(value: str) -> str:
    for char in _INVISIBLE_CHARS:
        value = value.replace(char, "")
    return value.strip()


def infer_category(title: str, company: str = "") -> str:
    haystack = f"{title} {company}".lower()
    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in haystack:
                scores[category] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Other"


def make_external_id(source_slug: str, unique_part: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", unique_part).strip("-").lower()
    return f"{source_slug}:{safe or hashlib.sha256(unique_part.encode()).hexdigest()[:12]}"


VALID_LISTING_TYPES = frozenset({"Job", "Summer Program"})


def build_job_record(
    *,
    source_label: str,
    source_slug: str,
    title: str,
    company: str,
    url: str | None,
    unique_part: str,
    listing_type: str = "Job",
) -> dict[str, Any]:
    title = clean_text(title)
    company = clean_text(company)
    category = infer_category(title, company)
    if listing_type not in VALID_LISTING_TYPES:
        listing_type = "Job"
    return {
        "title": title,
        "company": company,
        "url": url,
        "category": category,
        "source": source_label,
        "listing_type": listing_type,
        "external_id": make_external_id(source_slug, unique_part),
    }
