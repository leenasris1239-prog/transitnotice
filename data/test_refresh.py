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
XML.write_text("""<?xml version='1.0'?>
<rss><channel>
<item><title>BUS 501 - Test</title><description>Detour test</description><link>http://x</link><pubDate>Mon, 26 Oct 2026</pubDate></item>
<item><title>BUS 501 - Test</title><description>Detour test</description><link>http://x</link><pubDate>Mon, 26 Oct 2026</pubDate></item>
</channel></rss>""", encoding="utf-8")
run_refresh()
conn = sqlite3.connect(DB)
count = conn.execute("SELECT COUNT(*) FROM advisories WHERE advisory_text LIKE '%Detour test%'").fetchone()[0]
conn.close()
print(f"-> Passed if count == 1, got {count}\n")
restore()

print("Test 4: Unavailable source (empty XML)")
XML.write_text("", encoding="utf-8")
run_refresh()
print("-> Passed if no crash, failure logged\n")
restore()

print("All tests done. Backup restored.")