import sqlite3
from pathlib import Path

DB = Path("transit.db")
conn = sqlite3.connect(DB)
rows = conn.execute(
    "SELECT route, advisory_text, posted_at, source_url FROM advisories ORDER BY id DESC"
).fetchall()
conn.close()

html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Transit Advisories</title>
<style>
body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }
h1 { color: #1a5490; }
.advisory { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.route { font-weight: bold; color: #1a5490; font-size: 18px; }
.time { color: #666; font-size: 13px; margin-top: 6px; }
a { color: #1a5490; }
</style>
</head>
<body>
<h1>Transit Advisories</h1>
<p>Total: """ + str(len(rows)) + """ advisories</p>
"""
for route, text, posted, url in rows:
    html += f"""
<div class="advisory">
  <div class="route">Route {route}</div>
  <div>{text}</div>
  <div class="time">Posted: {posted} &nbsp;|&nbsp; <a href="{url}" target="_blank">Source</a></div>
</div>
"""
html += "</body></html>"

Path("advisories.html").write_text(html, encoding="utf-8")
print("Created advisories.html with", len(rows), "advisories")