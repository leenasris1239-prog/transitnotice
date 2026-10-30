import sqlite3
import xml.etree.ElementTree as ET
import hashlib
import re
from datetime import datetime, date
from pathlib import Path

DB = Path("transit.db")
XML = Path("nj_bus_advisories.xml")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Alerts table (delivery log + dedup)
cur.execute("""
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advisory_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    alert_status TEXT NOT NULL,
    alerted_at TEXT NOT NULL,
    FOREIGN KEY (advisory_id) REFERENCES advisories(id)
)
""")

def log_alert(advisory_id, event_type):
    # Dedup: same advisory + same event type = one alert only
    existing = cur.execute(
        "SELECT id FROM alerts WHERE advisory_id = ? AND event_type = ?",
        (advisory_id, event_type)
    ).fetchone()
    if existing:
        return False
    cur.execute("""
        INSERT INTO alerts (advisory_id, event_type, alert_status, alerted_at)
        VALUES (?, ?, 'delivered', ?)
    """, (advisory_id, event_type, datetime.now().isoformat()))
    print(f"[ALERT] {event_type.upper()} - advisory #{advisory_id}")
    return True

new_count = 0
revised_count = 0
unchanged_count = 0
errors = []

try:
    root = ET.parse(XML).getroot()
except ET.ParseError as e:
    print(f"[FAILURE] Malformed XML: {e}")
    errors.append(f"malformed_xml: {e}")
    root = None

if root:
    today = date.today()

    for item in root.findall(".//item"):
        try:
            title = (item.findtext("title") or "").strip()
            text = (item.findtext("description") or "").strip()
            link = (item.findtext("link") or "").strip()
            posted = (item.findtext("pubDate") or "").strip()

            if not title or not text or not link:
                print(f"[SKIP] Missing field: {title[:40]}")
                errors.append(f"missing_field: {title[:40]}")
                continue

            route = title.split(" - ")[0].replace("BUS ", "").strip()
            content_hash = hashlib.sha256(f"{route}|{text}".encode()).hexdigest()

            date_match = re.search(
                r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+([A-Z][a-z]+ \d{1,2}, \d{4})",
                text
            )
            valid_to = None
            if date_match:
                try:
                    valid_to = datetime.strptime(date_match.group(2), "%B %d, %Y").date().isoformat()
                except ValueError:
                    pass

            if "detour" in text.lower():
                advisory_type = "detour"
            elif "cancel" in text.lower():
                advisory_type = "cancellation"
            elif "delay" in text.lower():
                advisory_type = "delay"
            else:
                advisory_type = "other"

            existing = cur.execute(
                "SELECT id, content_hash FROM advisories WHERE content_hash = ?",
                (content_hash,)
            ).fetchone()

            now = datetime.now().isoformat()

            if existing is None:
                cur.execute("""
                    INSERT INTO advisories
                    (route, advisory_text, posted_at, source_url, source_name, created_at,
                     valid_to, status, observed_at, last_confirmed_at, content_hash, revision_id,
                     advisory_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (route, text, posted, link, "NJ TRANSIT Bus Advisories RSS", now,
                      valid_to, "active", now, now, content_hash, advisory_type))
                advisory_id = cur.lastrowid
                new_count += 1
                log_alert(advisory_id, "new")
            elif existing[1] != content_hash:
                cur.execute("""
                    UPDATE advisories
                    SET advisory_text = ?, valid_to = ?, advisory_type = ?,
                        revision_id = revision_id + 1,
                        last_confirmed_at = ?, status = ?
                    WHERE id = ?
                """, (text, valid_to, advisory_type, now, "active", existing[0]))
                revised_count += 1
                log_alert(existing[0], "revised")
            else:
                cur.execute("UPDATE advisories SET last_confirmed_at = ? WHERE id = ?",
                            (now, existing[0]))
                unchanged_count += 1
        except Exception as e:
            print(f"[FAILURE] Item parse error: {e}")
            errors.append(f"item_error: {e}")

    # Expire old advisories
    cur.execute("""
        UPDATE advisories SET status = 'expired'
        WHERE valid_to IS NOT NULL AND date(valid_to) < date('now') AND status != 'expired'
    """)

conn.commit()

print(f"\nSummary: {new_count} new, {revised_count} revised, {unchanged_count} unchanged")
print(f"Errors: {len(errors)}")
if errors:
    print("Failure log:")
    for e in errors:
        print(f"  - {e}")
conn.close()