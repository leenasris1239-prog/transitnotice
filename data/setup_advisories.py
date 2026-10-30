from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "advisories.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    agency TEXT NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    mode TEXT NOT NULL DEFAULT 'demo'
        CHECK (mode IN ('demo', 'public')),
    approval_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (approval_status IN ('pending', 'approved', 'blocked')),
    permission_notes TEXT,
    last_checked_at TEXT,
    last_success_at TEXT,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS advisories (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    external_id TEXT NOT NULL,
    agency TEXT NOT NULL,
    area TEXT,
    advisory_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_url TEXT NOT NULL,
    published_at TEXT,
    valid_from TEXT,
    valid_to TEXT,
    lifecycle_status TEXT NOT NULL DEFAULT 'published'
        CHECK (
            lifecycle_status IN ('published', 'withdrawn', 'cancelled')
        ),
    observed_at TEXT NOT NULL,
    last_confirmed_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    revision_id INTEGER NOT NULL DEFAULT 1,
    change_summary TEXT,
    UNIQUE (source_id, external_id)
);

CREATE TABLE IF NOT EXISTS advisory_routes (
    advisory_id INTEGER NOT NULL
        REFERENCES advisories(id) ON DELETE CASCADE,
    route_id TEXT NOT NULL,
    PRIMARY KEY (advisory_id, route_id)
);

CREATE TABLE IF NOT EXISTS advisory_stations (
    advisory_id INTEGER NOT NULL
        REFERENCES advisories(id) ON DELETE CASCADE,
    station_name TEXT NOT NULL,
    PRIMARY KEY (advisory_id, station_name)
);

CREATE TABLE IF NOT EXISTS revisions (
    id INTEGER PRIMARY KEY,
    advisory_id INTEGER NOT NULL
        REFERENCES advisories(id) ON DELETE CASCADE,
    revision_id INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    change_summary TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    UNIQUE (advisory_id, revision_id)
);

CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    filter_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_log (
    id INTEGER PRIMARY KEY,
    subscriber_id INTEGER NOT NULL REFERENCES subscribers(id),
    advisory_id INTEGER NOT NULL REFERENCES advisories(id),
    revision_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    alert_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (
            alert_status IN (
                'pending', 'demo_logged', 'sent', 'failed'
            )
        ),
    created_at TEXT NOT NULL,
    alerted_at TEXT,
    error_message TEXT,
    UNIQUE (subscriber_id, advisory_id, revision_id, event_type)
);

CREATE TABLE IF NOT EXISTS refresh_log (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    result TEXT NOT NULL
        CHECK (result IN ('running', 'success', 'failed', 'blocked')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    notices_seen INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_advisory_routes_route
ON advisory_routes(route_id);

CREATE INDEX IF NOT EXISTS idx_advisories_dates
ON advisories(valid_from, valid_to);

CREATE INDEX IF NOT EXISTS idx_advisories_area
ON advisories(area);
"""


def main():
    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        conn.commit()

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]

        print("DATABASE SETUP COMPLETE")
        print("Database:", DB_PATH.name)
        print("Integrity check:", integrity)
        print("Tables:")
        for row in tables:
            print(" -", row[0])

        print("Existing transitnotice.db was not modified.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()