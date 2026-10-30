from flask import Flask, request, jsonify, render_template
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "transitnotice.db")

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/routes")
def api_routes():
    q = request.args.get("q", "").strip()
    conn = get_db()

    try:
        rows = conn.execute(
            """
            SELECT
                col1 AS route_id,
                col3 AS route_short_name,
                col2 AS route_long_name
            FROM routes
            WHERE col3 LIKE ? OR col2 LIKE ?
            LIMIT 20
            """,
            (f"%{q}%", f"%{q}%")
        ).fetchall()

        return jsonify([dict(row) for row in rows])
    finally:
        conn.close()


@app.route("/api/notices", methods=["GET"])
def get_notices():
    conn = get_db()

    try:
        rows = conn.execute(
            """
            SELECT
                id,
                route_id,
                notice_type AS title,
                message AS description,
                created_at
            FROM notices
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

        return jsonify([dict(row) for row in rows])
    finally:
        conn.close()


@app.route("/api/notices", methods=["POST"])
def add_notice():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    title = data.get("title", "")
    description = data.get("description", "")
    route_id = data.get("route_id")

    if not isinstance(title, str) or not isinstance(description, str):
        return jsonify({
            "error": "Title and description must be text"
        }), 400

    title = title.strip()
    description = description.strip()

    if not title or not description:
        return jsonify({
            "error": "Title and description required"
        }), 400

    if route_id is not None:
        if not isinstance(route_id, str):
            return jsonify({"error": "Route ID must be text"}), 400
        route_id = route_id.strip() or None

    conn = get_db()

    try:
        cur = conn.execute(
            """
            INSERT INTO notices (notice_type, message, route_id)
            VALUES (?, ?, ?)
            """,
            (title, description, route_id)
        )
        conn.commit()

        return jsonify({
            "success": True,
            "id": cur.lastrowid
        }), 201
    finally:
        conn.close()


@app.route("/api/notices/<int:notice_id>", methods=["DELETE"])
def delete_notice(notice_id):
    conn = get_db()

    try:
        cur = conn.execute(
            "DELETE FROM notices WHERE id = ?",
            (notice_id,)
        )
        conn.commit()

        if cur.rowcount == 0:
            return jsonify({"error": "Notice not found"}), 404

        return jsonify({"success": True})
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=True, port=5000)