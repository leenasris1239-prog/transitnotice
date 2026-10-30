from flask import Flask, request, render_template_string
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB = Path("transit.db")
TIMEZONE = "America/New_York (NJ local time)"

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Transit Dashboard</title>
<style>
body { font-family: Arial, sans-serif; background: #f4f6f8; margin: 0; padding: 30px; }
h1 { color: #1a5490; }
.cards { display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }
.card { background: white; border-radius: 10px; padding: 20px 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.num { font-size: 32px; font-weight: bold; color: #1a5490; }
.label { color: #666; }
.controls { margin: 20px 0; }
input, select, button { padding: 10px; border-radius: 6px; border: 1px solid #ccc; }
button { background: #1a5490; color: white; border: none; cursor: pointer; }
table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
th { background: #1a5490; color: white; padding: 12px; text-align: left; }
td { padding: 12px; border-bottom: 1px solid #eee; }
.badge { background: #e3f0ff; color: #1a5490; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
a { color: #1a5490; }
.tz { color: #666; font-size: 14px; margin-top: 10px; }
</style>
</head>
<body>
<h1>Transit Advisories Dashboard</h1>
<div class="cards">
<div class="card"><div class="num">{{ total }}</div><div class="label">Total Advisories</div></div>
<div class="card"><div class="num">{{ unique_routes }}</div><div class="label">Unique Routes</div></div>
<div class="card"><div class="num">{{ latest }}</div><div class="label">Latest Posted</div></div>
</div>
<form class="controls" method="get" action="/">
  <input type="text" name="route" placeholder="Route (e.g. 412)" value="{{ route }}">
  <input type="text" name="area" placeholder="Area (e.g. Newark)" value="{{ area }}">
  <input type="text" name="q" placeholder="Search text" value="{{ q }}">
  <input type="date" name="service_date" value="{{ service_date }}">
  <select name="status">
    <option value="">All Status</option>
    <option value="active" {% if status == 'active' %}selected{% endif %}>Active</option>
    <option value="expired" {% if status == 'expired' %}selected{% endif %}>Expired</option>
  </select>
  <button type="submit">Apply</button>
  <a href="/">Reset</a>
</form>
<table>
<tr><th>Route</th><th>Type</th><th>Advisory</th><th>ValidTill</th><th>Status</th><th>LastChecked</th><th>Source</th></tr>
{% for r in rows %}
<tr>
<td><span class="badge">{{ r[0] }}</span></td>
<td>{{ r[7] }}</td>
<td>{{ r[1] }}</td>
<td>{{ r[5] or '_' }}</td>
<td>{{ r[4] }}</td>
<td>{{ r[6] }}</td>
<td><a href="{{ r[3] }}" target="_blank">Link</a></td>
</tr>
{% endfor %}
</table>
<div class="tz">Timezone: {{ timezone }}</div>
</body>
</html>
"""

@app.route("/")
def dashboard():
    route = request.args.get("route", "").strip()
    area = request.args.get("area", "").strip()
    q = request.args.get("q", "").strip()
    service_date = request.args.get("service_date", "").strip()
    status = request.args.get("status", "").strip()

    conn = sqlite3.connect(DB)
    query = """
        SELECT GROUP_CONCAT(route), advisory_text, posted_at, source_url,
               status, valid_to, last_confirmed_at, advisory_type
        FROM advisories
        WHERE 1=1
    """
    params = []
    if route:
        query += " AND route LIKE ?"
        params.append(f"%{route}%")
    if area:
        query += " AND advisory_text LIKE ?"
        params.append(f"%{area}%")
    if q:
        query += " AND advisory_text LIKE ?"
        params.append(f"%{q}%")
    if service_date:
        query += " AND (valid_to IS NULL OR valid_to >= ?)"
        params.append(service_date)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " GROUP BY content_hash ORDER BY MAX(id) DESC"

    rows = conn.execute(query, params).fetchall()

    total = conn.execute("SELECT COUNT(DISTINCT content_hash) FROM advisories").fetchone()[0]
    unique_routes = conn.execute("SELECT COUNT(DISTINCT route) FROM advisories").fetchone()[0]
    latest = conn.execute("SELECT posted_at FROM advisories ORDER BY id DESC LIMIT 1").fetchone()
    latest = latest[0] if latest else "-"
    conn.close()

    return render_template_string(TEMPLATE, rows=rows, total=total,
        unique_routes=unique_routes, latest=latest, route=route, area=area,
        q=q, service_date=service_date, status=status, timezone=TIMEZONE)

if __name__ == "__main__":
    app.run(debug=True, port=5000)