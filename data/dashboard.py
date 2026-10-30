from flask import Flask, request, render_template_string, redirect, url_for
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB = Path("transit.db")
def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS advisories (
        notice_id TEXT PRIMARY KEY,
        agency TEXT NOT NULL,
        route_id TEXT,
        effective_start TEXT,
        effective_end TEXT,
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
    """)
    conn.commit()
    conn.close()

init_db()
TIMEZONE = "America/New_York (NJ local time)"

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TransitNotice Dashboard</title>
<style>
:root {
  --accent: #1d4ed8;
  --bg: #f1f5f9;
  --surface: #ffffff;
  --text: #172033;
  --muted: #526176;
  --border: #d5dce5;
}
:root[data-theme="dark"] {
  --bg: #0f172a;
  --surface: #1e293b;
  --text: #f1f5f9;
  --muted: #cbd5e1;
  --border: #475569;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
}
a { color: var(--accent); }
button, input, select { font: inherit; }
button, select, a { touch-action: manipulation; }
button { cursor: pointer; }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
.skip {
  position: absolute;
  left: 12px;
  top: -80px;
  padding: 12px;
  background: var(--surface);
  z-index: 20;
}
.skip:focus { top: 12px; }
.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  width: 240px;
  padding: 28px 20px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  overflow-y: auto;
}
.brand { font-size: 25px; font-weight: bold; color: var(--accent); }
.subtitle { color: var(--muted); font-size: 13px; line-height: 1.6; }
nav { display: grid; gap: 10px; margin-top: 28px; }
nav a {
  padding: 13px;
  color: var(--text);
  text-decoration: none;
  border: 1px solid var(--border);
  border-radius: 9px;
}
nav a:hover { border-color: var(--accent); }
.settings { margin-top: 32px; }
.settings label { display: block; margin: 16px 0 8px; }
.settings select, .settings button { width: 100%; }
main { margin-left: 240px; padding: 30px; min-width: 0; }
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
h1 { margin: 0; font-size: 28px; }
h2 { font-size: 20px; margin: 0 0 16px; }
.muted { color: var(--muted); line-height: 1.6; }
.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin: 24px 0;
}
.card, .panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}
.num {
  font-size: 30px;
  font-weight: bold;
  overflow-wrap: anywhere;
}
.label { color: var(--muted); margin-top: 8px; }
.latest { font-size: 18px; line-height: 1.5; }
.panel { margin-bottom: 22px; scroll-margin-top: 16px; }
.controls {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.field { min-width: 0; }
.field label { display: block; margin-bottom: 8px; font-size: 14px; }
input, select, button, .button {
  border-radius: 8px;
  padding: 11px 13px;
  border: 1px solid var(--border);
}
input, select {
  width: 100%;
  background: var(--surface);
  color: var(--text);
}
button, .button {
  display: inline-block;
  background: var(--accent);
  color: white;
  text-decoration: none;
  text-align: center;
}
.actions { display: flex; align-items: end; gap: 10px; flex-wrap: wrap; }
.secondary { background: var(--surface); color: var(--text); }
.table-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
}
table {
  width: 100%;
  min-width: fixed;
  border-collapse: collapse;
}
caption { text-align: left; padding: 12px; color: var(--muted); }
th {
  background: var(--accent);
  color: white;
  text-align: left;
  padding: 14px;
}
td {
  padding: 14px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
  line-height: 1.5;
}
.advisory { min-width: 280px; max-width: 500px; overflow-wrap: anywhere; }
.badge {
  display: inline-block;
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 4px 8px;
}
.empty { text-align: center; padding: 30px; }
@media (max-width: 1000px) {
  .controls { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .sidebar {
    position: static;
    width: 100%;
    border-right: 0;
    border-bottom: 1px solid var(--border);
    padding: 20px;
  }
  nav { display: flex; flex-wrap: wrap; margin-top: 16px; }
  .settings { margin-top: 18px; }
  main { margin-left: 0; padding: 16px; }
  .cards, .controls { grid-template-columns: 1fr; }
  h1 { font-size: 24px; }
  .panel { padding: 16px; }
}
th, td {
  font-size: 12px;
  padding: 8px 10px;
  overflow-wrap: anywhere;
}
th:nth-child(1), td:nth-child(1) { width: 9%; }
th:nth-child(2), td:nth-child(2) { width: 11%; }
th:nth-child(3), td:nth-child(3) { width: 32%; }
th:nth-child(4), td:nth-child(4) { width: 11%; }
th:nth-child(5), td:nth-child(5) { width: 10%; }
th:nth-child(6), td:nth-child(6) { width: 12%; }
th:nth-child(7), td:nth-child(7) { width: 9%; }
th:nth-child(8), td:nth-child(8) { width: 6%; }
.advisory { min-width: 0; max-width: none; }
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<aside class="sidebar" aria-label="Sidebar">
  <div class="brand">TransitNotice</div>
  <p class="subtitle">Public Transport<br>Service Update Tracker</p>

  <nav aria-label="Dashboard navigation">
    <a href="#overview">Overview</a>
    <a href="#filters">Search & Filters</a>
    <a href="#notices">Advisories</a>
    <a href="#alerts">Alerts</a>
    <a href="#display-settings">Theme Settings</a>
  </nav>

  <section class="settings" id="display-settings">
    <h2>Appearance</h2>
    <label for="accent">Theme colour</label>
    <select id="accent">
      <option value="blue">Blue</option>
      <option value="purple">Purple</option>
      <option value="green">Green</option>
      <option value="orange">Orange</option>
    </select>
    <label for="mode">Display mode</label>
    <button type="button" id="mode" aria-pressed="false">
      Dark mode: Off
    </button>
  </section>
</aside>

<main id="main">
  <header class="topbar" id="overview">
    <div>
      <h1>Transit Advisories Dashboard</h1>
      <form method="post" action="/refresh" style="margin:12px 0;">
  <button type="submit">Refresh now</button>
</form>
      <p class="muted">Search published notices and check source details.</p>
    </div>
    <a class="button secondary" href="">Reload dashboard</a>
  </header>

  <section class="cards" aria-label="Database overview">
    <div class="card">
      <div class="num">{{ total }}</div>
      <div class="label">Total stored advisories</div>
    </div>
    <div class="card">
      <div class="num">{{ unique_routes }}</div>
      <div class="label">Unique stored routes</div>
      <div class="card">
      <div class="num">{{ alert_count }}</div>
      <div class="label">Alerts generated</div>
      </div>
    </div>
    <div class="card">
      <div class="num latest">{{ latest or '-' }}</div>
      <div class="label">Posted date of latest stored record</div>
    </div>
  </section>

  <section class="panel" id="filters">
    <h2>Search & Filters</h2>
    <form class="controls" method="get" action="/">
      <div class="field">
        <label for="route">Route</label>
        <input id="route" name="route" placeholder="e.g. 412"
               value="{{ route }}">
      </div>
      <div class="field">
        <label for="area">Area keyword</label>
        <input id="area" name="area" placeholder="e.g. Newark"
               value="{{ area }}">
      </div>
      <div class="field">
        <label for="q">Search notice text</label>
        <input id="q" name="q" placeholder="e.g. diversion"
               value="{{ q }}">
      </div>
      <div class="field">
        <label for="service_date">Service date</label>
        <input id="service_date" type="date" name="service_date"
               value="{{ service_date }}">
      </div>
      <div class="field">
        <label for="status">Stored status</label>
        <select id="status" name="status">
          <option value="">All statuses</option>
          {% for item in ['active', 'expired', 'withdrawn', 'cancelled'] %}
          <option value="{{ item }}"
            {% if status == item %}selected{% endif %}>
            {{ item|capitalize }}
          </option>
          {% endfor %}
        </select>
      </div>
      <div class="actions">
        <button type="submit">Apply filters</button>
        <a class="button secondary" href="/">Reset</a>
      </div>
    </form>
    <p class="muted">
      Area currently searches notice text. Service date checks both
      the start and end of the stored validity window.
    </p>
  </section>

  <section class="panel" id="notices">
    <h2>Advisories — {{ rows|length }} results</h2>
    <p class="muted">
      Stored notices are not a live-service guarantee.
      Reloading this page does not fetch new authority notices.
      Check verification times and official source links.
    </p>

    <div class="table-wrap" tabindex="0"
         role="region" aria-label="Scrollable advisory table">
      <table>
        <caption>On small screens, scroll sideways to view all columns.</caption>
        <thead>
          <tr>
            <th scope="col">Routes</th>
            <th scope="col">Area</th>
            <th scope="col">Advisory</th>
            <th scope="col">Valid until</th>
            <th scope="col">Stored status</th>
            <th scope="col">Last confirmed</th>
            <th scope="col">Official source</th>
            <th scope="col">Effective window</th>
          </tr>
        </thead>
        <tbody>
        {% for r in rows %}
          <tr>
            <td><span class="badge">{{ r[0] or '-' }}</span></td>
            <td>{{ r[7] or 'Not identified' }}</td>
            <td class="advisory">{{ r[1] or '-' }}</td>
            <td>{{ r[5] or 'Not provided' }}</td>
            <td>{{ r[4] or 'Unknown' }}</td>
            <td>{{ r[6] or 'Not recorded' }}</td>
            <td>
              {% if r[3] and
                    (r[3].startswith('https://') or
                     r[3].startswith('http://')) %}
              <a href="{{ r[3] }}" target="_blank"
                 rel="noopener noreferrer">Open source</a>
              {% else %}
              Unavailable
              {% endif %}
            </td>
           <td>
  {% if r[-2] and r[-1] %}
    {{ r[-2] }} – {{ r[-1] }}
  {% elif r[-2] %}
    {{ r[-2] }}
  {% elif r[-1] %}
    Until {{ r[-1] }}
  {% else %}
    —
  {% endif %}
</td>
          </tr>
        {% else %}
          <tr>
            <td colspan="8" class="empty">
              No advisories match these filters.
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    <section class="panel" id="alerts">
  <h2>Alerts — {{ alerts|length }}</h2>
  <p class="muted">One alert is recorded for each new or revised advisory.</p>
  <div class="table-wrap" tabindex="0" role="region" aria-label="Alert log">
    <table>
      <thead><tr>
        <th>Time</th><th>Type</th><th>Alert</th><th>Delivery</th><th>Notice</th>
      </tr></thead>
      <tbody>
      {% for a in alerts %}
        <tr>
          <td>{{ a[5] }}</td>
          <td>{{ a[1] }}</td>
          <td>{{ a[3] }}</td>
          <td>{{ a[4] }}</td>
          <td><a href="/?q={{ a[2] }}">View advisory</a></td>
        </tr>
      {% else %}
        <tr><td colspan="5" class="empty">No alerts yet.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</section>
    <p class="muted">Configured timezone label: {{ timezone }}</p>
  </section>
</main>

<script>
const root = document.documentElement;
const colourSelect = document.getElementById("accent");
const modeButton = document.getElementById("mode");

const palettes = {
  blue:   { light: "#1d4ed8", dark: "#93c5fd" },
  purple: { light: "#6d28d9", dark: "#c4b5fd" },
  green:  { light: "#166534", dark: "#86efac" },
  orange: { light: "#9a3412", dark: "#fdba74" }
};

let colour = "blue";
let dark = false;

try {
  const savedColour = localStorage.getItem("transit-colour");
  if (Object.prototype.hasOwnProperty.call(palettes, savedColour)) {
    colour = savedColour;
  }
  dark = localStorage.getItem("transit-dark") === "true";
} catch (error) {}

function applyAppearance() {
  root.dataset.theme = dark ? "dark" : "light";

  // Keep filled buttons and headings readable with white text.
  root.style.setProperty("--accent", palettes[colour].light);

  colourSelect.value = colour;
  modeButton.textContent = dark ? "Dark mode: On" : "Dark mode: Off";
  modeButton.setAttribute("aria-pressed", String(dark));

  try {
    localStorage.setItem("transit-colour", colour);
    localStorage.setItem("transit-dark", String(dark));
  } catch (error) {}
}

colourSelect.addEventListener("change", function () {
  colour = this.value;
  applyAppearance();
});
modeButton.addEventListener("click", function () {
  dark = !dark;
  applyAppearance();
});
applyAppearance();
</script>
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
        SELECT route_id, advisory_type, summary, source_url,
               status, valid_to, last_confirmed_at, area, effective_start, effective_end
        FROM advisories
        WHERE 1=1
    """
    params = []

    if route:
        query += " AND route_id LIKE ?"
        params.append(f"%{route}%")
    if area:
        query += " AND area LIKE ?"
        params.append(f"%{area}%")
    if q:
        query += " AND summary LIKE ?"
        params.append(f"%{q}%")
    if service_date:
        query += " AND (valid_from IS NULL OR valid_from <= ?)"
        query += " AND (valid_to IS NULL OR valid_to >= ?)"
        params.extend([service_date, service_date])
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY COALESCE(published_at, observed_at) DESC"

    rows = conn.execute(query, params).fetchall()

    total = conn.execute("SELECT COUNT(*) FROM advisories").fetchone()[0]
    unique_routes = conn.execute(
        "SELECT COUNT(DISTINCT route_id) FROM advisories "
        "WHERE route_id IS NOT NULL"
    ).fetchone()[0]
    latest = conn.execute(
        "SELECT COALESCE(published_at, observed_at)FROM advisories "
        "ORDER BY COALESCE(published_at, observed_at) DESC LIMIT 1"
    ).fetchone()
    latest = latest[0] if latest else "-"
    alerts = conn.execute(
        """
        SELECT notice_id, change_type, dedupe_key, message,
               delivery_status, created_at
        FROM alert_log
        ORDER BY created_at DESC
        LIMIT 50
        """
    ).fetchall()
    alerts = [tuple(a) for a in alerts]
    alert_count = conn.execute(
        "SELECT COUNT(*) FROM alert_log"
    ).fetchone()[0]
    conn.close()

    return render_template_string(
        TEMPLATE, rows=rows, total=total, unique_routes=unique_routes,
        latest=latest, route=route, area=area, q=q,
        service_date=service_date, status=status, timezone=TIMEZONE,alerts=alerts, alert_count=alert_count
    )
@app.route("/refresh", methods=["POST"])
def refresh_now():
    from scraper import refresh
    refresh()
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)