from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib
import json
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "advisories.db"
DEMO_FILE = BASE_DIR / "demo_advisories.json"


def time_text(value):
    return value.isoformat(timespec="seconds")


def main():
    now = datetime.now(timezone.utc)
    checked_at = time_text(now)

    # Create the demo source file only on the first run.
    if not DEMO_FILE.exists():
        examples = [
            {
                "external_id": "DEMO-001",
                "agency": "Demo Transport Authority",
                "routes": ["0", "38"],
                "stations": ["Demo Central"],
                "area": "Demo Central Area",
                "advisory_type": "diversion",
                "summary": "DEMO: Temporary diversion affecting two routes.",
                "published_at": time_text(now - timedelta(hours=2)),
                "valid_from": time_text(now - timedelta(hours=1)),
                "valid_to": time_text(now + timedelta(days=1)),
                "lifecycle_status": "published"
            },
            {
                "external_id": "DEMO-002",
                "agency": "Demo Transport Authority",
                "routes": ["533"],
                "stations": ["Demo East"],
                "area": "Demo East Area",
                "advisory_type": "interruption",
                "summary": "DEMO: This interruption has already expired.",
                "published_at": time_text(now - timedelta(days=3)),
                "valid_from": time_text(now - timedelta(days=2)),
                "valid_to": time_text(now - timedelta(days=1)),
                "lifecycle_status": "published"
            },
            {
                "external_id": "DEMO-003",
                "agency": "Demo Transport Authority",
                "routes": ["0"],
                "stations": [],
                "area": "Demo Central Area",
                "advisory_type": "service_change",
                "summary": "DEMO: Service change without an announced end date.",
                "published_at": time_text(now - timedelta(hours=2)),
                "valid_from": time_text(now - timedelta(hours=1)),
                "valid_to": None,
                "lifecycle_status": "published"
            }
        ]

        DEMO_FILE.write_text(
            json.dumps(examples, indent=2),
            encoding="utf-8"
        )

    notices = json.loads(DEMO_FILE.read_text(encoding="utf-8"))

    if not isinstance(notices, list):
        raise ValueError("Demo source must contain a list")

    required_fields = {
        "external_id", "agency", "routes", "stations", "area",
        "advisory_type", "summary", "published_at",
        "valid_from", "valid_to", "lifecycle_status"
    }

    seen_ids = set()

    # Validate all records before writing to the database.
    for notice in notices:
        if not isinstance(notice, dict):
            raise ValueError("Each advisory must be an object")

        if not required_fields.issubset(notice):
            raise ValueError("An advisory has missing fields")

        for field in (
            "external_id", "agency", "advisory_type", "summary"
        ):
            if not isinstance(notice[field], str) or not notice[field].strip():
                raise ValueError(field + " must contain text")

        if notice["external_id"] in seen_ids:
            raise ValueError("Duplicate external_id in demo source")

        seen_ids.add(notice["external_id"])

        if notice["area"] is not None and not isinstance(
            notice["area"], str
        ):
            raise ValueError("Area must be text or null")

        for field in ("routes", "stations"):
            values = notice[field]
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value.strip()
                for value in values
            ):
                raise ValueError(field + " must be a list of text")

        parsed_dates = {}

        for field in ("published_at", "valid_from", "valid_to"):
            value = notice[field]

            if value is None:
                parsed_dates[field] = None
                continue

            if not isinstance(value, str):
                raise ValueError(field + " must be text or null")

            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

            if parsed.tzinfo is None:
                raise ValueError(field + " must include a timezone")

            parsed_dates[field] = parsed

        start = parsed_dates["valid_from"]
        end = parsed_dates["valid_to"]

        if start and end and end <= start:
            raise ValueError("valid_to must be later than valid_from")

        if notice["lifecycle_status"] not in (
            "published", "withdrawn", "cancelled"
        ):
            raise ValueError("Invalid lifecycle_status")

    conn = sqlite3.connect(
        f"{DB_PATH.as_uri()}?mode=rw",
        uri=True
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    new_count = 0
    revised_count = 0
    unchanged_count = 0

    try:
        with conn:
            conn.execute(
                """
                INSERT INTO sources (
                    name, agency, source_url, mode,
                    approval_status, permission_notes
                )
                VALUES (?, ?, ?, 'demo', 'approved', ?)
                ON CONFLICT(source_url) DO NOTHING
                """,
                (
                    "Local demo fixture",
                    "Demo Transport Authority",
                    DEMO_FILE.as_uri(),
                    "Student-created test data, not official live notices."
                )
            )

            source_id = conn.execute(
                "SELECT id FROM sources WHERE source_url = ?",
                (DEMO_FILE.as_uri(),)
            ).fetchone()["id"]

            for notice in notices:
                normalized = dict(notice)
                normalized["routes"] = sorted(set(notice["routes"]))
                normalized["stations"] = sorted(set(notice["stations"]))

                snapshot = json.dumps(
                    normalized,
                    sort_keys=True,
                    ensure_ascii=False
                )

                digest = hashlib.sha256(
                    snapshot.encode("utf-8")
                ).hexdigest()

                old = conn.execute(
                    """
                    SELECT * FROM advisories
                    WHERE source_id = ? AND external_id = ?
                    """,
                    (source_id, notice["external_id"])
                ).fetchone()

                if old and old["content_hash"] == digest:
                    conn.execute(
                        """
                        UPDATE advisories
                        SET last_confirmed_at = ?
                        WHERE id = ?
                        """,
                        (checked_at, old["id"])
                    )
                    unchanged_count += 1
                    continue

                revision = old["revision_id"] + 1 if old else 1

                if old:
                    previous = conn.execute(
                        """
                        SELECT snapshot_json
                        FROM revisions
                        WHERE advisory_id = ? AND revision_id = ?
                        """,
                        (old["id"], old["revision_id"])
                    ).fetchone()

                    previous_data = (
                        json.loads(previous["snapshot_json"])
                        if previous else {}
                    )

                    changed_fields = [
                        key for key in normalized
                        if normalized[key] != previous_data.get(key)
                    ]

                    change_summary = (
                        "Changed: " + ", ".join(changed_fields)
                    )
                    revised_count += 1
                else:
                    change_summary = "First observed demo advisory"
                    new_count += 1

                conn.execute(
                    """
                    INSERT INTO advisories (
                        source_id, external_id, agency, area,
                        advisory_type, summary, source_url,
                        published_at, valid_from, valid_to,
                        lifecycle_status, observed_at,
                        last_confirmed_at, content_hash,
                        revision_id, change_summary
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    ON CONFLICT(source_id, external_id) DO UPDATE SET
                        agency = excluded.agency,
                        area = excluded.area,
                        advisory_type = excluded.advisory_type,
                        summary = excluded.summary,
                        source_url = excluded.source_url,
                        published_at = excluded.published_at,
                        valid_from = excluded.valid_from,
                        valid_to = excluded.valid_to,
                        lifecycle_status = excluded.lifecycle_status,
                        last_confirmed_at = excluded.last_confirmed_at,
                        content_hash = excluded.content_hash,
                        revision_id = excluded.revision_id,
                        change_summary = excluded.change_summary
                    """,
                    (
                        source_id,
                        notice["external_id"],
                        notice["agency"],
                        notice["area"],
                        notice["advisory_type"],
                        notice["summary"],
                        DEMO_FILE.as_uri(),
                        notice["published_at"],
                        notice["valid_from"],
                        notice["valid_to"],
                        notice["lifecycle_status"],
                        checked_at,
                        checked_at,
                        digest,
                        revision,
                        change_summary
                    )
                )

                advisory_id = conn.execute(
                    """
                    SELECT id FROM advisories
                    WHERE source_id = ? AND external_id = ?
                    """,
                    (source_id, notice["external_id"])
                ).fetchone()["id"]

                conn.execute(
                    "DELETE FROM advisory_routes WHERE advisory_id = ?",
                    (advisory_id,)
                )

                conn.executemany(
                    """
                    INSERT INTO advisory_routes (advisory_id, route_id)
                    VALUES (?, ?)
                    """,
                    [
                        (advisory_id, route)
                        for route in normalized["routes"]
                    ]
                )

                conn.execute(
                    "DELETE FROM advisory_stations WHERE advisory_id = ?",
                    (advisory_id,)
                )

                conn.executemany(
                    """
                    INSERT INTO advisory_stations (
                        advisory_id, station_name
                    )
                    VALUES (?, ?)
                    """,
                    [
                        (advisory_id, station)
                        for station in normalized["stations"]
                    ]
                )

                conn.execute(
                    """
                    INSERT INTO revisions (
                        advisory_id, revision_id, content_hash,
                        snapshot_json, change_summary, observed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        advisory_id,
                        revision,
                        digest,
                        snapshot,
                        change_summary,
                        checked_at
                    )
                )

            conn.execute(
                """
                UPDATE sources
                SET last_checked_at = ?,
                    last_success_at = ?,
                    last_error = NULL
                WHERE id = ?
                """,
                (checked_at, checked_at, source_id)
            )

            conn.execute(
                """
                INSERT INTO refresh_log (
                    source_id, started_at, finished_at,
                    result, attempt_count, notices_seen
                )
                VALUES (?, ?, ?, 'success', 1, ?)
                """,
                (
                    source_id,
                    checked_at,
                    checked_at,
                    len(notices)
                )
            )

        print("DEMO REFRESH COMPLETE")
        print("New:", new_count)
        print("Revised:", revised_count)
        print("Unchanged:", unchanged_count)
        print("Demo data only - not official live information.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()