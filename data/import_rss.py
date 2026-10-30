import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

DB = Path("transit.db")
XML = Path("nj_bus_advisories.xml")

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS advisories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT NOT NULL,
    advisory_text TEXT NOT NULL,
    posted_at TEXT NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")

root = ET.parse(XML).getroot()

for item in root.findall(".//item"):
    title = (item.findtext("title") or "").strip()
    text = (item.findtext("description") or "").strip()
    link = (item.findtext("link") or "").strip()
    posted = (item.findtext("pubDate") or "").strip()

    if not title or not text or not link or not posted:
        continue

    route = title.split(" - ")[0].replace("BUS ", "").strip()
    source_name = "NJ TRANSIT Bus Advisories RSS"

    cur.execute("""
        INSERT OR IGNORE INTO advisories
        (route, advisory_text, posted_at, source_url, source_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (route, text, posted, link, source_name, datetime.utcnow().isoformat()))

conn.commit()
print("Imported advisories:", cur.execute("SELECT COUNT(*) FROM advisories").fetchone()[0])
conn.close()