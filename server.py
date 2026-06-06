"""
Local web server: job board UI + subscription API.

Run:
  python server.py
  Open http://localhost:8000
"""

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import database as db

PROJECT_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(PROJECT_DIR), static_url_path="")


@app.route("/")
def home():
    return send_from_directory(PROJECT_DIR, "index.html")


@app.get("/api/jobs")
def api_jobs():
    jobs = db.list_jobs()
    if not jobs:
        return jsonify({"scraped_at": None, "count": 0, "jobs": []})
    return jsonify(
        {
            "scraped_at": jobs[0]["scraped_at"],
            "count": len(jobs),
            "jobs": [
                {
                    "title": j["title"],
                    "company": j["company"],
                    "url": j["url"],
                    "category": j["category"],
                    "source": j.get("source", "CaribbeanJobs"),
                }
                for j in jobs
            ],
        }
    )


@app.post("/api/subscribe")
def api_subscribe():
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    category = (data.get("category") or "").strip()

    if not phone:
        return jsonify({"ok": False, "error": "Phone number is required."}), 400
    if not category:
        return jsonify({"ok": False, "error": "Please select a job category."}), 400

    try:
        result = db.add_subscription(phone, category)
        return jsonify({"ok": True, **result})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "subscriptions": db.subscription_count()})


import os

if __name__ == "__main__":
    # Read the dynamic port assigned by Render, fallback to 8000 if running locally
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
