"""
WhatsApp alert broadcaster via Twilio.

Reads subscribers from SQLite, matches jobs from jobs.json by category,
and sends WhatsApp messages through the Twilio API.

HOW TO RUN:
  1. Paste your Twilio credentials below (or set env vars).
  2. Join the WhatsApp sandbox: send the join code to +1 415 523 8886
     from the phone numbers you want to test.
  3. python scraper.py
  4. python notifier.py

Requires: pip install -r requirements.txt
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import database as db

# --- Twilio credentials (paste your keys here) ---
TWILIO_ACCOUNT_SID = "AC9a3b14b54b8ce9c97c9cc62f69b32cdf"
TWILIO_AUTH_TOKEN = "6530af2a11ea18c7b5d7b5c29d762442"
TWILIO_WHATSAPP_NUMBER = "+14155238886"
# -------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent
JOBS_JSON = PROJECT_DIR / "jobs.json"

CATEGORY_EMOJI = {
    "Tech": "💻",
    "Admin": "📋",
    "Retail": "🛒",
    "Other": "📌",
}

SOURCE_EMOJI = {
    "CaribbeanJobs": "🌐",
    "SVG Gov": "🏛️",
}


def _env_or_default(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def get_twilio_config() -> tuple[str, str, str]:
    return (
        _env_or_default("TWILIO_ACCOUNT_SID", TWILIO_ACCOUNT_SID),
        _env_or_default("TWILIO_AUTH_TOKEN", TWILIO_AUTH_TOKEN),
        _env_or_default("TWILIO_WHATSAPP_NUMBER", TWILIO_WHATSAPP_NUMBER),
    )


def credentials_configured() -> bool:
    sid, token, from_number = get_twilio_config()
    placeholders = (
        "YOUR_ACCOUNT_SID_HERE",
        "YOUR_AUTH_TOKEN_HERE",
        "",
    )
    return (
        sid not in placeholders
        and token not in placeholders
        and from_number.startswith("+")
    )


def mask_phone(phone: str) -> str:
    if len(phone) <= 6:
        return phone
    return phone[:5] + "..."


def whatsapp_address(phone: str) -> str:
    digits = phone.strip()
    if not digits.startswith("whatsapp:"):
        if not digits.startswith("+"):
            digits = f"+{digits}"
        digits = f"whatsapp:{digits}"
    return digits


def job_key(job: dict[str, Any]) -> str:
    external_id = job.get("external_id")
    if external_id:
        return str(external_id)
    return f"{job['title']}|{job['company']}"


def load_jobs() -> tuple[list[dict[str, Any]], str | None]:
    if not JOBS_JSON.is_file():
        raise FileNotFoundError(
            f"{JOBS_JSON.name} not found. Run python scraper.py first."
        )

    payload = json.loads(JOBS_JSON.read_text(encoding="utf-8"))
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise ValueError("jobs.json is missing a valid 'jobs' array.")
    return jobs, payload.get("scraped_at")


def jobs_for_category(jobs: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    return [j for j in jobs if j.get("category") == category]


def build_message(job: dict[str, Any], category: str) -> str:
    """WhatsApp-friendly alert body with emojis and light formatting."""
    cat_emoji = CATEGORY_EMOJI.get(category, "🔔")
    source = job.get("source", "Caribbean Finder")
    src_emoji = SOURCE_EMOJI.get(source, "📍")
    title = job["title"]
    company = job["company"]
    url = job.get("url")

    lines = [
        "🌴 *Caribbean Finder*",
        f"{cat_emoji} *New {category} job alert!*",
        "",
        f"💼 *{title}*",
        f"🏢 {company}",
        f"{src_emoji} Source: {source}",
    ]

    if url:
        lines.extend(["", "🔗 *Apply now:*", url])
    else:
        lines.extend(["", "🔗 Details available on the job board."])

    lines.extend(["", "—", "Reply STOP anytime to unsubscribe (coming soon)."])

    return "\n".join(lines)


def send_whatsapp(phone: str, category: str, job: dict[str, Any]) -> str:
    """Send a real WhatsApp message via Twilio. Returns message SID."""
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException

    sid, token, from_number = get_twilio_config()
    client = Client(sid, token)
    body = build_message(job, category)

    try:
        message = client.messages.create(
            from_=whatsapp_address(from_number),
            to=whatsapp_address(phone),
            body=body,
        )
        return message.sid
    except TwilioRestException as exc:
        raise RuntimeError(f"Twilio error {exc.code}: {exc.msg}") from exc


def send_whatsapp_simulation(phone: str, category: str, job: dict[str, Any]) -> None:
    masked = mask_phone(phone)
    title = job["title"]
    source = job.get("source", "Unknown")
    print(
        f"[SIMULATED] Would send {category} alert "
        f'"{title}" ({source}) to {masked}'
    )
    print("--- message preview ---")
    print(build_message(job, category))
    print("-----------------------")


def deliver_alert(phone: str, category: str, job: dict[str, Any], live: bool) -> None:
    masked = mask_phone(phone)
    title = job["title"]
    source = job.get("source", "Unknown")

    if live:
        message_sid = send_whatsapp(phone, category, job)
        print(
            f"[WHATSAPP SENT] {category} | {title} ({source}) -> {masked} | SID {message_sid}"
        )
    else:
        send_whatsapp_simulation(phone, category, job)


def run_broadcast() -> int:
    live = credentials_configured()
    if not live:
        print(
            "Twilio credentials not configured — running in SIMULATION mode.\n"
            "Paste TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN at the top of notifier.py\n"
            "or set them as environment variables.\n"
        )
    else:
        print(f"Twilio live mode — sending from whatsapp:{get_twilio_config()[2]}\n")

    db.init_db()
    subscribers = db.list_subscriptions()

    if not subscribers:
        print("No subscribers in database. Add some via the job board UI first.")
        return 0

    jobs, scraped_at = load_jobs()
    if not jobs:
        print("No jobs in jobs.json. Run python scraper.py first.")
        return 0

    print(f"Loaded {len(jobs)} job(s) from {JOBS_JSON.name}")
    if scraped_at:
        print(f"Scrape timestamp: {scraped_at}")
    print(f"Checking {len(subscribers)} subscriber(s)...\n")

    sent_count = 0
    error_count = 0

    for sub in subscribers:
        phone = sub["phone"]
        category = sub["category"]
        matches = jobs_for_category(jobs, category)

        if not matches:
            print(f"[SKIP] No {category} jobs for {mask_phone(phone)}")
            continue

        for job in matches:
            key = job_key(job)
            if db.was_alert_sent(phone, key):
                continue

            try:
                deliver_alert(phone, category, job, live=live)
                db.record_alert_sent(phone, key, category)
                sent_count += 1
            except RuntimeError as exc:
                error_count += 1
                print(f"[ERROR] {mask_phone(phone)}: {exc}", file=sys.stderr)

    mode = "sent" if live else "simulated"
    print(f"\nDone. {sent_count} alert(s) {mode}.")
    if error_count:
        print(f"{error_count} delivery error(s) — see messages above.", file=sys.stderr)
    if sent_count == 0 and error_count == 0:
        print("No new matches (already notified or no category overlap).")

    return sent_count


def main() -> None:
    try:
        run_broadcast()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
