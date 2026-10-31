import sqlite3, shutil, os
from pathlib import Path

DB = Path("transit.db")
XML = Path("nj_bus_advisories.xml")
BACKUP_DB = Path("transit_backup.db")
BACKUP_XML = Path("nj_bus_advisories_backup.xml")

shutil.copy(DB, BACKUP_DB)
shutil.copy(XML, BACKUP_XML)

def restore():
    shutil.copy(BACKUP_DB, DB)
    shutil.copy(BACKUP_XML, XML)

def run_refresh():
    os.system("py refresh_advisories.py")

print("Test 1: Malformed XML")
XML.write_text("<rss><item>broken", encoding="utf-8")
run_refresh()
print("-> Passed if no crash, failure logged\n")
restore()

print("Test 2: Missing field")
XML.write_text("""<?xml version='1.0'?>
<rss><channel><item><title>BUS 501</title></item></channel></rss>""", encoding="utf-8")
run_refresh()
print("-> Passed if skipped, failure logged\n")
restore()

print("Test 3: Duplicate advisory")
import scraper
scraper.DB = DB
scraper.init_db()

test_item = {
    "notice_id": "test-duplicate-1",
    "agency": "NJ TRANSIT",
    "route_id": "501",
    "area": "Newark",
    "source_url": "https://example.com/test-duplicate",
    "advisory_type": "detour",
    "summary": "BUS 501 - Test. Detour test",
    "published_at": "2026-10-26",
    "valid_from": "2026-10-26",
    "valid_to": "2026-10-31"
}

# Same notice twice in one refresh
scraper.save_notices([test_item, test_item])

conn = sqlite3.connect(DB)
count = conn.execute(
    "SELECT COUNT(*) FROM advisories WHERE summary LIKE '%Detour test%'"
).fetchone()[0]
conn.close()
print(f"-> Passed if count == 1, got {count}\n")
restore()

print("Test 4: Unavailable source (empty XML)")
XML.write_text("", encoding="utf-8")
run_refresh()
print("-> Passed if no crash, failure logged\n")
restore()

print("All tests done. Backup restored.")