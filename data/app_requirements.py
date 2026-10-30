from pathlib import Path
from datetime import datetime, timezone
import json
import sqlite3

from flask import request, jsonify
from app import app

BASE_DIR = Path(__file__).resolve().parent
ADVISORY_DB = BASE_DIR / "advisories.db"


def advisory_db():
    conn = sqlite3.connect(
        f"{ADVISORY_DB.as_uri()}?mode=rw",
        uri=True
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def parse_time(value):
    if not value:
        return None

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        raise ValueError("Date-time must include a timezone")

    return parsed.astimezone(timezone.utc)


def calculate_status(notice, now):
    lifecycle = notice["lifecycle_status"]

    if lifecycle in ("withdrawn", "cancelled"):
        return lifecycle

    try:
        start = parse_time(notice["valid_from"])
        end = parse_time(notice["valid_to"])
    except (ValueError, TypeError):
        return "needs_review"

    if start and end and end <= start:
        return "needs_review"

    if end and now >= end:
        return "expired"

    if start and now < start:
        return "upcoming"

    if not start:
        return "unknown_window"

    if not end:
        return "open_ended"

    return "active"


@app.route("/api/advisories")
def list_advisories():
    route = request.args.get("route", "").strip()
    area = request.args.get("area", "").strip()
    station = request.args.get("station", "").strip()
    query = request.args.get("q", "").strip().lower()
    wanted_status = request.args.get("status", "").strip()

    conn = advisory_db()

    try:
        rows = conn.execute(
            """
            SELECT
                a.*,
                s.name AS source_name,
                s.mode AS source_mode,
                s.last_checked_at AS source_last_checked_at,
                s.last_success_at AS source_last_success_at,
                s.last_error AS source_last_error
            FROM advisories AS a
            JOIN sources AS s ON s.id = a.source_id
            ORDER BY a.observed_at DESC, a.id DESC
            """
        ).fetchall()

        route_map = {}
        for row in conn.execute(
            "SELECT advisory_id, route_id FROM advisory_routes"
        ):
            route_map.setdefault(row["advisory_id"], []).append(
                row["route_id"]
            )

        station_map = {}
        for row in conn.execute(
            "SELECT advisory_id, station_name FROM advisory_stations"
        ):
            station_map.setdefault(row["advisory_id"], []).append(
                row["station_name"]
            )

        now = datetime.now(timezone.utc)
        output = []

        for row in rows:
            notice = dict(row)
            notice["routes"] = route_map.get(notice["id"], [])
            notice["stations"] = station_map.get(notice["id"], [])
            notice["status"] = calculate_status(notice, now)

            # Freshness is separate from the announced service window.
            if notice["source_mode"] == "demo":
                notice["freshness"] = "demo"
            elif notice["source_last_error"]:
                notice["freshness"] = "refresh_failed"
            else:
                try:
                    confirmed = parse_time(notice["last_confirmed_at"])
                    if confirmed is None:
                        notice["freshness"] = "unverified"
                    else:
                        age = (now - confirmed).total_seconds()
                        if age < 0:
                            notice["freshness"] = "needs_review"
                        elif age > 3600:
                            notice["freshness"] = "stale"
                        else:
                            notice["freshness"] = "recently_verified"
                except (ValueError, TypeError):
                    notice["freshness"] = "unverified"

            if route and route not in notice["routes"]:
                continue

            if area and area.lower() not in (notice["area"] or "").lower():
                continue

            if station and not any(
                station.lower() in name.lower()
                for name in notice["stations"]
            ):
                continue

            if wanted_status and notice["status"] != wanted_status:
                continue

            searchable = " ".join([
                notice["summary"] or "",
                notice["agency"] or "",
                notice["advisory_type"] or "",
                notice["area"] or "",
                *notice["routes"],
                *notice["stations"]
            ]).lower()

            if query and query not in searchable:
                continue

            output.append(notice)

        return jsonify(output)
    finally:
        conn.close()


@app.route("/api/sources")
def list_sources():
    conn = advisory_db()
    try:
        rows = conn.execute(
            "SELECT * FROM sources ORDER BY id"
        ).fetchall()
        return jsonify([dict(row) for row in rows])
    finally:
        conn.close()


@app.route("/api/advisories/<int:notice_id>/history")
def advisory_history(notice_id):
    conn = advisory_db()

    try:
        exists = conn.execute(
            "SELECT id FROM advisories WHERE id = ?",
            (notice_id,)
        ).fetchone()

        if exists is None:
            return jsonify({"error": "Advisory not found"}), 404

        rows = conn.execute(
            """
            SELECT revision_id, change_summary,
                   observed_at, snapshot_json
            FROM revisions
            WHERE advisory_id = ?
            ORDER BY revision_id DESC
            """,
            (notice_id,)
        ).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            item["snapshot"] = json.loads(item.pop("snapshot_json"))
            result.append(item)

        return jsonify(result)
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)