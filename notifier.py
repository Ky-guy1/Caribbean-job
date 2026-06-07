import sqlite3
from datetime import datetime, timezone, timedelta
import urllib.parse
from pathlib import Path
import database as db

def run_alert_dispatcher():
    print("🚀 =================================================")
    print("🚀 CARIBBEAN FINDER — WHATSAPP ALERTS MATCHING ENGINE")
    print("🚀 =================================================\n")

    # 1. Fetch active subscribers using your newly created database helper functions
    subscribers = db.get_all_subscribers()
    
    if not subscribers:
        print("ℹ️  No active phone alert subscribers found in the database. Exiting worker.")
        return

    print(f"👥 Found {len(subscribers)} registered subscriber(s) to scan.")

    # 2. Retrieve jobs scraped within the last 24 hours to prevent duplicate spamming
    try:
        # Use your database path directly to connect safely
        conn = sqlite3.connect(db.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Calculate a threshold timestamp for the last 24 hours
        time_limit = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        cursor.execute('SELECT title, company, category, url FROM jobs WHERE scraped_at > ?', (time_limit,))
        fresh_jobs = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"❌ Error fetching latest listings from SQLite: {e}")
        return

    if not fresh_jobs:
        print("ℹ️  No fresh jobs or summer camps found within the last 24-hour window. Nothing to send today.\n")
        return

    print(f"💼 Total fresh listings collected in last 24 hours: {len(fresh_jobs)}\n")
    print("-------------------------------------------------")
    print("🔍 RUNNING BATCH CATEGORY MATCHES:")
    print("-------------------------------------------------")

    # 3. Process matches per subscriber
    alert_count = 0
    for sub in subscribers:
        phone = sub["phone"]
        user_cat = sub["category"]

        # Find matching items based on their dropdown selection
        matches = []
        for job in fresh_jobs:
            job_cat = job["category"] or "Other"
            # Match if category names line up or if the user subscribed to 'All'
            if user_cat.lower() == "all" or job_cat.lower() == user_cat.lower():
                matches.append(job)

        if not matches:
            print(f"   • User {phone} ({user_cat}): No new matches found today.")
            continue

        alert_count += 1
        print(f"   • 🎉 MATCH FOUND for {phone} under category '{user_cat}'!")
        print(f"     Found {len(matches)} item(s) matching their preference.")

        # 4. Construct a structured layout message text template
        message = f"🌴 *Caribbean Finder Live Alert!* 🌴\n\n"
        message += f"Hey! We found new opportunities matching your *{user_cat}* preferences:\n\n"
        
        # Limit to 3 items per message text blocks to stay brief
        for job in matches[:3]:
            message += f"💼 *{job['title']}*\n"
            message += f"🏢 {job['company']}\n"
            message += f"🔗 {job['url'] if job['url'] else 'https://onrender.com'}\n\n"
            
        message += "📱 Keep hunting! Refresh your dashboard to see more items."

        # 5. Free Text Gateway Preparation Router Block
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        encoded_text = urllib.parse.quote(message)
        
        # Free background click-to-chat setup route
                # 🆕 Added the missing forward slash right after wa.me
        whatsapp_click_url = f"https://wa.me{clean_phone}?text={encoded_text}"

        
        print(f"     Generated WhatsApp text template link:")
        print(f"     🔗 {whatsapp_click_url[:70]}...")
        print("     -------------------------------------------")

    print("\n=================================================")
    print(f"📊 ALERT DISPATCH RUN COMPLETE.")
    print(f"📊 Successfully prepared and matched {alert_count} alert message packet(s).")
    print("=================================================\n")

if __name__ == "__main__":
    run_alert_dispatcher()

