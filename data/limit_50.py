import sqlite3
from pathlib import Path

DB = Path("transit.db")
KEEP = 50

conn = sqlite3.connect(DB)

# Keep the newest 50 advisories using SQLite internal rowid.
keep_hashes = [
    row[0]
    for row in conn.execute(
        """
        SELECT notice_id
        FROM advisories
        ORDER BY rowid DESC
        LIMIT ?
        """,
        (KEEP,)
    )
]

if keep_hashes:
    placeholders = ",".join("?" for _ in keep_hashes)
    deleted = conn.execute(
        f"DELETE FROM advisories WHERE notice_id NOT IN ({placeholders})",
        keep_hashes
    ).rowcount
else:
    deleted = 0

# Keep alert history for notices that still exist.
conn.execute(
    """
    DELETE FROM alert_log
    WHERE notice_id NOT IN (SELECT notice_id FROM advisories)
    """
)

conn.commit()
conn.close()

print(f"Kept latest {KEEP} advisories. Deleted {deleted} older advisories.")