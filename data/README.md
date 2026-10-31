# TransitNotice — NJ Transit Advisory Dashboard

TransitNotice is a Flask-based web dashboard that collects, stores, and displays
NJ Transit service advisories from an official RSS feed. It helps users quickly
see affected routes, advisory details, effective windows, and change alerts.

## Features

- Live refresh of NJ Transit advisories from the official RSS feed
- Automatic extraction of affected routes, areas, and advisory types
- Effective window detection (e.g., "Effective Immediately" or time ranges)
- Change detection: new, revised, extended, and withdrawn advisories with alerts
- Alert log with delivery status (safe demo mode)
- Route, area, keyword, date, and status-based filtering
- Dashboard cards: total advisories, unique routes, latest update, alerts
- Database limited to the latest 50 advisories for clean demo data
- Responsive, accessible dashboard with dark mode support

## Tech Stack

- Python 3
- Flask
- SQLite
- RSS / XML parsing
- HTML, CSS (responsive, dark mode)

## Project Structure

- `scraper.py` — fetches and parses the RSS feed, extracts fields, saves notices, creates alerts
- `dashboard.py` — Flask web dashboard with filters, alerts, and refresh button
- `db.py` — database schema and helper functions
- `data/test_refresh.py` — robustness tests for malformed XML, missing fields, duplicates, and unavailable sources
- `data/transit.db` — SQLite database
- `data/limit_50.py` — keeps the latest 50 advisories
- `data/backfill_windows.py` — backfills effective windows for existing records

## Timezone Handling

All timestamps are stored in UTC using ISO 8601 format
(`YYYY-MM-DDTHH:MM:SS+00:00`). Advisory validity dates are normalized to
ISO date format (`YYYY-MM-DD`). This keeps refresh behavior reproducible
across machines and time zones.

## Data Source & Crawling Policy

- Source: NJ Transit official Bus Advisories RSS feed
  (`https://www.njtransit.com/rss/BusAdvisories_feed.xml`)
- Only publicly available advisory data is collected; no login, CAPTCHA
  bypass, or private data is accessed.
- Requests use a descriptive User-Agent, a 15-second timeout, a maximum of
  3 attempts, and exponential backoff between retries.
- Refresh failures are logged and existing database records are never
  overwritten or marked live when the source cannot be refreshed.

## Running Tests

Run the robustness test suite (malformed XML, missing fields, duplicates,
unavailable source):

```bat
cd data
py test_refresh.py

## How to Run

1. Install dependencies:

```bat
pip install flask requests

```markdown
## Deployment & Operational Notes

- Run `py scraper.py` manually or on a schedule (e.g., Windows Task Scheduler)
  to keep advisories fresh.
- The dashboard shows `last_confirmed_at` as the freshness indicator; notices
  are never presented as live without a recent verification time.
- Database files, exported logs, and downloaded GTFS archives are excluded
  from version control via `.gitignore`.
- Secrets (if any are added later) must be kept in environment variables,
  never in source code.