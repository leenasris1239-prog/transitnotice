import hashlib
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree
TIME_RE = re.compile(
    r"(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)\s*(?:to|until|through|-|–)\s*"
    r"(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)",
    re.IGNORECASE,
)

IMMEDIATE_RE = re.compile(r"effective\s+immediately", re.IGNORECASE)

def extract_window(text):
    text = text or ""
    if IMMEDIATE_RE.search(text):
        return "Immediately", None
    m = TIME_RE.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None

DB = Path("transit.db")
FEED_URL = "https://www.njtransit.com/rss/BusAdvisories_feed.xml"
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 15


def log(message):
    print(f"{datetime.now(timezone.utc).isoformat()} - {message}")


def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS advisories (
            notice_id TEXT PRIMARY KEY,
            agency TEXT NOT NULL,
            route_id TEXT,
            area TEXT,
            source_url TEXT NOT NULL,
            advisory_type TEXT,
            summary TEXT NOT NULL,
            published_at TEXT,
            valid_from TEXT,
            valid_to TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            observed_at TEXT NOT NULL,
            last_confirmed_at TEXT NOT NULL,
            content_hash TEXT NOT NULL UNIQUE,
            revision_id INTEGER NOT NULL DEFAULT 1,
            change_summary TEXT,
            alert_status TEXT NOT NULL DEFAULT 'none',
            alerted_at TEXT
        );

        CREATE TABLE IF NOT EXISTS alert_log (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            notice_id TEXT NOT NULL,
            change_type TEXT NOT NULL,
            dedupe_key TEXT NOT NULL UNIQUE,
            message TEXT NOT NULL,
            delivery_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            delivered_at TEXT
        );
    """)
    conn.commit()
    conn.close()


def fetch_feed():
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            request = Request(
                FEED_URL,
                headers={
                    "User-Agent": "TransitNoticeStudentProject/1.0",
                    "Accept": "application/rss+xml, application/xml, text/xml"
                }
            )
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return response.read()
        except Exception as error:
            last_error = error
            log(f"Fetch attempt {attempt} failed: {error}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 * attempt)

    raise RuntimeError(f"Could not refresh source: {last_error}")


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def parse_date(value):
    value = clean_text(value)

    if not value:
        return None

    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%d"
    ]

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue

    return None


def extract_fields(title, description):
    text = f"{title} {description}"

    routes = re.findall(r"\b(?:Bus\s*)?(?:Nos?\.?\s*)?(\d{1,4})\b", text)
    route_id = ",".join(dict.fromkeys(routes[:10])) if routes else None

    areas = [
        "Newark", "Jersey City", "Paterson", "Elizabeth", "Trenton",
        "Camden", "Hoboken", "Atlantic City", "Morristown", "Princeton",
        "Philadelphia", "Freehold", "Vineland", "Pitman", "Rahway",
        "Bayonne", "Hammonton", "Plainfield", "Roselle Park", "Toms River"
    ]
    area = next(
        (place for place in areas if place.lower() in text.lower()),
        None
    )

    lowered = text.lower()

    if "detour" in lowered:
        advisory_type = "detour"
    elif "delay" in lowered:
        advisory_type = "delay"
    elif "cancel" in lowered:
        advisory_type = "cancellation"
    elif "stop" in lowered:
        advisory_type = "stop change"
    elif "schedule" in lowered:
        advisory_type = "schedule change"
    else:
        advisory_type = "general"

    dates = re.findall(
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
        r"(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
        text,
        flags=re.I
    )

    month_names = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }

    parsed_dates = []

    for month_name, day, year in dates:
        try:
            parsed_dates.append(
                datetime(
                    int(year),
                    month_names[month_name.lower()],
                    int(day)
                ).date().isoformat()
            )
        except (KeyError, ValueError):
            continue

    valid_from = min(parsed_dates) if parsed_dates else None
    valid_to = max(parsed_dates) if parsed_dates else None

    return route_id, area, advisory_type, valid_from, valid_to


def calculate_status(valid_from, valid_to, today):
    if valid_to and valid_to < today:
        return "expired"

    if valid_from and valid_from > today:
        return "scheduled"

    return "active"


def record_alert(conn, notice_id, change_type, message, now):
    dedupe_key = hashlib.sha256(
        f"{notice_id}|{change_type}".encode("utf-8")
    ).hexdigest()

    existing_alert = conn.execute(
        "SELECT 1 FROM alert_log WHERE dedupe_key = ?",
        (dedupe_key,)
    ).fetchone()

    if existing_alert:
        return False

    conn.execute(
        """
        INSERT INTO alert_log (
            notice_id,
            change_type,
            dedupe_key,
            message,
            delivery_status,
            created_at,
            delivered_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            notice_id,
            change_type,
            dedupe_key,
            message,
            "Delivered",
            now,
            now
        )
    )

    return True

def save_notices(items):
    conn = sqlite3.connect(DB)
    now = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc).date().isoformat()

    new_count = 0
    revised_count = 0
    extended_count = 0
    withdrawn_count = 0
    alert_count = 0

    seen_notice_ids = []

    for item in items:
        seen_notice_ids.append(item["notice_id"])

        content_hash = hashlib.sha256(
            f"{item['notice_id']}|{item['summary']}".encode("utf-8")
        ).hexdigest()

        status = calculate_status(
            item["valid_from"],
            item["valid_to"],
            today
        )

        existing = conn.execute(
            """
            SELECT content_hash, valid_to
            FROM advisories
            WHERE notice_id = ?
            """,
            (item["notice_id"],)
        ).fetchone()

        if existing is None:
            start, end = extract_window(item["summary"])
            conn.execute(
                """
                INSERT INTO advisories (
                    notice_id, agency, route_id, area, source_url,
                    advisory_type, summary, published_at, valid_from,
                    valid_to, status, observed_at, last_confirmed_at,
                    content_hash, revision_id, change_summary,
                    alert_status, alerted_at, effective_start, effective_end
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(notice_id) DO NOTHING
                """,
                (
                    item["notice_id"], item["agency"], item["route_id"],
                    item["area"], item["source_url"], item["advisory_type"],
                    item["summary"], item["published_at"], item["valid_from"],
                    item["valid_to"], status, now, now, content_hash,
                    1, "New advisory observed", "pending", None,
                    start, end
                )
            )
            new_count += 1

            alert_created = record_alert(
                conn,
                item["notice_id"],
                "new",
                (
                    f"New {item['advisory_type']} advisory for route(s) "
                    f"{item['route_id'] or 'unknown'} in "
                    f"{item['area'] or 'unspecified area'}."
                ),
                now
            )

            if alert_created:
                alert_count += 1
                conn.execute(
                    """
                    UPDATE advisories
                    SET alert_status = 'sent', alerted_at = ?
                    WHERE notice_id = ?
                    """,
                    (now, item["notice_id"])
                )

        elif existing[0] != content_hash:
            old_valid_to = existing[1]
            new_valid_to = item["valid_to"]

            is_extended = (
                old_valid_to is not None
                and new_valid_to is not None
                and new_valid_to > old_valid_to
            )

            if is_extended:
                change_summary = "Advisory extended"
                change_type = "extended"
                message = (
                    f"Advisory for route(s) "
                    f"{item['route_id'] or 'unknown'} extended to "
                    f"{new_valid_to}."
                )
                extended_count += 1
            else:
                change_summary = "Advisory content revised"
                change_type = "revised"
                message = (
                    f"Revised {item['advisory_type']} advisory for route(s) "
                    f"{item['route_id'] or 'unknown'}."
                )
                revised_count += 1

            conn.execute(
                """
                UPDATE advisories
                SET summary = ?,
                    route_id = ?,
                    area = ?,
                    advisory_type = ?,
                    valid_from = ?,
                    valid_to = ?,
                    status = ?,
                    last_confirmed_at = ?,
                    content_hash = ?,
                    revision_id = revision_id + 1,
                    change_summary = ?,
                    alert_status = 'pending',
                    alerted_at = NULL
                WHERE notice_id = ?
                """,
                (
                    item["summary"], item["route_id"], item["area"],
                    item["advisory_type"], item["valid_from"],
                    item["valid_to"], status, now, content_hash,
                    change_summary, item["notice_id"]
                )
            )

            alert_created = record_alert(
                conn,
                item["notice_id"],
                change_type,
                message,
                now
            )

            if alert_created:
                alert_count += 1
                conn.execute(
                    """
                    UPDATE advisories
                    SET alert_status = 'sent', alerted_at = ?
                    WHERE notice_id = ?
                    """,
                    (now, item["notice_id"])
                )

        else:
            conn.execute(
                """
                UPDATE advisories
                SET last_confirmed_at = ?, status = ?
                WHERE notice_id = ?
                """,
                (now, status, item["notice_id"])
            )

    # Withdrawn: notices in DB but missing from current feed
    if seen_notice_ids:
        placeholders = ",".join("?" for _ in seen_notice_ids)

        missing = conn.execute(
            f"""
            SELECT notice_id, route_id, advisory_type
            FROM advisories
            WHERE notice_id NOT IN ({placeholders})
              AND status IN ('active', 'scheduled')
            """,
            seen_notice_ids
        ).fetchall()

        for notice_id, route_id, advisory_type in missing:
            conn.execute(
                """
                UPDATE advisories
                SET status = 'withdrawn',
                    last_confirmed_at = ?,
                    change_summary = 'Advisory withdrawn from source feed'
                WHERE notice_id = ?
                """,
                (now, notice_id)
            )
            withdrawn_count += 1

            alert_created = record_alert(
                conn,
                notice_id,
                "withdrawn",
                (
                    f"{advisory_type or 'Transit'} advisory for route(s) "
                    f"{route_id or 'unknown'} withdrawn."
                ),
                now
            )

            if alert_created:
                alert_count += 1

    conn.commit()
    conn.close()

    log(
        f"Refresh complete: {new_count} new, {revised_count} revised, "
        f"{extended_count} extended, {withdrawn_count} withdrawn, "
        f"{alert_count} new alert(s)"
    )


def refresh():
    try:
        raw_feed = fetch_feed()
        root = ElementTree.fromstring(raw_feed)
        items = []

        for entry in root.findall(".//item"):
            title = clean_text(entry.findtext("title"))
            description = clean_text(entry.findtext("description"))
            link = clean_text(entry.findtext("link"))
            published = clean_text(entry.findtext("pubDate"))

            if not title or not link:
                log("Skipped item: missing title or link")
                continue

            route_id, area, advisory_type, valid_from, valid_to = \
                extract_fields(title, description)

            notice_id = hashlib.sha256(
                f"{link}|{title}".encode("utf-8")
            ).hexdigest()

            items.append(
                {
                    "notice_id": notice_id,
                    "agency": "NJ TRANSIT",
                    "route_id": route_id,
                    "area": area,
                    "source_url": link,
                    "advisory_type": advisory_type,
                    "summary": f"{title}. {description}".strip(". "),
                    "published_at": parse_date(published),
                    "valid_from": valid_from,
                    "valid_to": valid_to
                }
            )

        if not items:
            log("No valid notices parsed from source")
            return

        save_notices(items)

    except Exception as error:
        log(
            "Refresh failed; existing database records were not "
            f"marked live: {error}"
        )


if __name__ == "__main__":
    init_db()
    refresh()