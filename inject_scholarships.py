import sqlite3
from datetime import datetime, timezone
import os

DB_PATH = "caribbean_finder.db"

def inject_real_scholarships():
    print("⏳ Connecting to caribbean_finder.db to inject real scholarships...")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file '{DB_PATH}' could not be found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Generate current ISO timestamp strings for both tracking fields
    current_time = datetime.now(timezone.utc).isoformat()
    
    # Real records mapped out with the mandatory created_at field included
    scholarships = [
        (
            "sch-taiwan-2026",
            "Taiwan (ROC) International Higher Education Scholarship Program",
            "Government of the Republic of China (Taiwan)",
            "Tech",
            "SVG Ministry of Education",
            "Scholarship",
            "https://studyintaiwan.org",
            current_time,  # For scraped_at
            current_time   # For created_at (Satisfies the NOT NULL constraint!)
        ),
        (
            "sch-chevening-2026",
            "Chevening UK Government Scholarships (Fully Funded Master's)",
            "UK Foreign, Commonwealth & Development Office",
            "Admin",
            "British High Commission Kingstown",
            "Scholarship",
            "https://chevening.org",
            current_time,
            current_time
        ),
        (
            "sch-uwi-2026",
            "UWI Open Merit Scholarships (Undergraduate Programs)",
            "The University of the West Indies",
            "Other",
            "UWI Global Campus SVG",
            "Scholarship",
            "https://uwi.edu",
            current_time,
            current_time
        ),
        (
            "sch-oas-2026",
            "OAS Academic Scholarship Program (Graduate & Development Research)",
            "Organization of American States (OAS)",
            "Admin",
            "OAS Official Portal",
            "Scholarship",
            "https://oas.org",
            current_time,
            current_time
        )
    ]
    
    inserted_count = 0
    for sch in scholarships:
        try:
            # 🎓 Perfect Constraint Match: Supplying both timestamp columns safely
            cursor.execute('''
                INSERT OR REPLACE INTO jobs (external_id, title, company, category, source, listing_type, url, scraped_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sch)
            inserted_count += 1
            print(f"✅ Successfully written: {sch[1]}")
        except Exception as e:
            print(f"❌ Failed to insert {sch[1]}: {e}")
            
    conn.commit()
    conn.close()
    print(f"\n🎉 Success! Beautifully injected {inserted_count} real scholarships directly into SQLite database.")

if __name__ == "__main__":
    inject_real_scholarships()
