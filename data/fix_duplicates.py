import sqlite3
from pathlib import Path

DB = Path("transit.db")
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Keep lowest id per content_hash, delete rest
cur.execute("""
DELETE FROM advisories
WHERE id NOT IN (
    SELECT MIN(id) FROM advisories GROUP BY content_hash
)
""")
deleted = cur.rowcount
conn.commit()
print(f"Deleted {deleted} duplicate rows")

total = cur.execute("SELECT COUNT(*) FROM advisories").fetchone()[0]
print(f"Remaining advisories: {total}")
conn.close()