import sqlite3
from datetime import datetime, timezone
import database as db

def inject_real_scholarships():
    print("⏳ Connecting to caribbean_finder.db to inject real scholarships...")
    
    # Connect using your existing database path rules
    conn = sqlite3.connect(db.DB_PATH)
    cursor = conn.cursor()
    
    scraped_time = datetime.now(timezone.utc).isoformat()
    
    # Real current higher-education scholarships for St. Vincent
    scholarships = [
        (
            "sch-taiwan-2026",
            "Taiwan (ROC) International Higher Education Scholarship Program",
            "Government of the Republic of China (Taiwan)",
            "Kingstown, St. Vincent / Taiwan",
            "Tech",
            "SVG Ministry of Education",
            "Scholarship",
            "https://studyintaiwan.org",
            scraped_time
        ),
        (
            "sch-chevening-2026",
            "Chevening UK Government Scholarships (Fully Funded Master's)",
            "UK Foreign, Commonwealth & Development Office",
            "Kingstown, St. Vincent / UK",
            "Admin",
            "British High Commission Kingstown",
            "Scholarship",
            "https://chevening.org",
            scraped_time
        ),
        (
            "sch-uwi-2026",
            "UWI Open Merit Scholarships (Undergraduate Programs)",
            "The University of the West Indies",
            "Kingstown, St. Vincent",
            "Other",
            "UWI Global Campus SVG",
            "Scholarship",
            "https://uwi.edu",
            scraped_time
        ),
        (
            "sch-oas-2026",
            "OAS Academic Scholarship Program (Graduate & Development Research)",
            "Organization of American States (OAS)",
            "Kingstown, St. Vincent",
            "Admin",
            "OAS Official Portal",
            "Scholarship",
            "https://oas.org",
            scraped_time
        )
    ]
    
    inserted_count = 0
    for sch in scholarships:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO jobs (external_id, title, company, location, category, source, listing_type, url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sch)
            inserted_count += 1
        except Exception as e:
            print(f"❌ Failed to insert {sch[1]}: {e}")
            
    conn.commit()
    conn.close()
    print(f"\n🎉 Success! Beautifully injected {inserted_count} real scholarships directly into SQLite database.")

if __name__ == "__main__":
    inject_real_scholarships()
