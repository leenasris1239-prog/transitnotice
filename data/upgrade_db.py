import sqlite3
from pathlib import Path

DB = Path("transit.db")
conn = sqlite3.connect(DB)
cur = conn.cursor()

cols = {
    "valid_from": "TEXT",
    "valid_to": "TEXT",
    "status": "TEXT DEFAULT 'active'",
    "observed_at": "TEXT",
    "last_confirmed_at": "TEXT",
    "content_hash": "TEXT",
    "revision_id": "INTEGER DEFAULT 1",
    "area": "TEXT",
    "advisory_type": "TEXT",
}

for col, ctype in cols.items():
    try:
        cur.execute(f"ALTER TABLE advisories ADD COLUMN {col} {ctype}")
        print(f"Added column: {col}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print(f"Already exists: {col}")
        else:
            raise

# Backfill existing rows
cur.execute("""
UPDATE advisories
SET observed_at = COALESCE(observed_at, created_at),
    last_confirmed_at = COALESCE(last_confirmed_at, created_at),
    status = COALESCE(status, 'active')
""")
conn.commit()

print("Schema upgrade complete")
conn.close()