import sqlite3
from scraper import extract_window

conn = sqlite3.connect("transit.db")
rows = conn.execute(
    "SELECT notice_id, summary FROM advisories"
).fetchall()

updated = 0
for notice_id, summary in rows:
    start, end = extract_window(summary or "")
    if start:
        conn.execute(
            "UPDATE advisories SET effective_start = ?, effective_end = ? "
            "WHERE notice_id = ?",
            (start, end, notice_id)
        )
        updated += 1

conn.commit()
conn.close()
print(f"Backfill complete. Updated {updated} advisories.")