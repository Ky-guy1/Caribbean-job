"""SQLite persistence for job listings and WhatsApp alert subscriptions."""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "caribbean_finder.db"

VALID_CATEGORIES = frozenset({"Tech", "Admin", "Retail"})

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT,
    category TEXT NOT NULL DEFAULT 'Other',
    scraped_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,
    category TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (phone, category)
);

CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(category);
CREATE INDEX IF NOT EXISTS idx_subscriptions_category ON subscriptions(category);

CREATE TABLE IF NOT EXISTS sent_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,
    job_external_id TEXT NOT NULL,
    category TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    UNIQUE (phone, job_external_id)
);
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()   
def save_subscriber(phone: str, category: str) -> bool:
        """Saves a new user subscription into the database using our connection manager."""
        created_at = utc_now_iso()
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # Inserts phone and category combination. Uses OR IGNORE to safely handle duplicates.
                cursor.execute('''
                    INSERT OR IGNORE INTO subscriptions (phone, category, created_at)
                    VALUES (?, ?, ?)
                ''', (phone, category, created_at))
                return True
        except Exception as e:
            print(f"Database error saving subscriber: {e}")
            return False
def get_all_subscribers() -> list[dict]:
        """Retrieves all active phone alerts and their matched categories."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT phone, category FROM subscriptions')
                rows = cursor.fetchall()
                return [{"phone": row["phone"], "category": row["category"]} for row in rows]
        except Exception as e:
            print(f"Database error reading subscribers: {e}")
            return []



def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Add columns introduced after initial release."""
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
    }
    if "source" not in columns:
        conn.execute(
            "ALTER TABLE jobs ADD COLUMN source TEXT NOT NULL DEFAULT 'CaribbeanJobs'"
        )
    if "listing_type" not in columns:
        conn.execute(
            "ALTER TABLE jobs ADD COLUMN listing_type TEXT NOT NULL DEFAULT 'Job'"
        )


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrate_schema(conn)


def normalize_phone(raw: str) -> str:
    """Keep digits and leading + for consistent storage."""
    cleaned = re.sub(r"[^\d+]", "", raw.strip())
    if cleaned.startswith("+"):
        digits = "+" + re.sub(r"\D", "", cleaned[1:])
    else:
        digits = re.sub(r"\D", "", cleaned)
    if len(digits.lstrip("+")) < 10:
        raise ValueError("Enter a valid phone number with at least 10 digits.")
    if not digits.startswith("+"):
        digits = f"+{digits}"
    return digits


def upsert_jobs(jobs: list[dict[str, Any]], scraped_at: str) -> int:
    """Insert or update scraped jobs. Returns number of rows touched."""
    init_db()
    now = utc_now_iso()
    count = 0
    with get_connection() as conn:
        for job in jobs:
            conn.execute(
                """
                INSERT INTO jobs (external_id, title, company, url, category, source, listing_type, scraped_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(external_id) DO UPDATE SET
                    title = excluded.title,
                    company = excluded.company,
                    url = excluded.url,
                    category = excluded.category,
                    source = excluded.source,
                    listing_type = excluded.listing_type,
                    scraped_at = excluded.scraped_at
                """,
                (
                    job.get("external_id"),
                    job["title"],
                    job["company"],
                    job.get("url"),
                    job.get("category", "Other"),
                    job.get("source", "CaribbeanJobs"),
                    job.get("listing_type", "Job"),
                    scraped_at,
                    now,
                ),
            )
            count += 1
    return count


def add_subscription(phone: str, category: str) -> dict[str, Any]:
    """Register a phone number for category alerts."""
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Category must be one of: {', '.join(sorted(VALID_CATEGORIES))}")

    normalized = normalize_phone(phone)
    init_db()
    created_at = utc_now_iso()

    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO subscriptions (phone, category, created_at)
                VALUES (?, ?, ?)
                """,
                (normalized, category, created_at),
            )
            is_new = True
        except sqlite3.IntegrityError:
            is_new = False

    return {
        "phone": normalized,
        "category": category,
        "created_at": created_at,
        "is_new": is_new,
        "message": (
            f"You're subscribed to {category} WhatsApp alerts!"
            if is_new
            else f"You're already subscribed to {category} alerts."
        ),
    }


def list_subscriptions() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT phone, category, created_at FROM subscriptions ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def list_jobs(limit: int = 100) -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT title, company, url, category, source, listing_type, scraped_at
            FROM jobs
            ORDER BY scraped_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def subscription_count() -> int:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM subscriptions").fetchone()
    return int(row["c"]) if row else 0


def was_alert_sent(phone: str, job_external_id: str) -> bool:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM sent_alerts
            WHERE phone = ? AND job_external_id = ?
            """,
            (phone, job_external_id),
        ).fetchone()
    return row is not None


def record_alert_sent(phone: str, job_external_id: str, category: str) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO sent_alerts (phone, job_external_id, category, sent_at)
            VALUES (?, ?, ?, ?)
            """,
            (phone, job_external_id, category, utc_now_iso()),
        )
