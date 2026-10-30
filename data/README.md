# TransitNotice — NJ Transit Advisory Dashboard

TransitNotice is a Flask-based web dashboard that collects, stores, and displays
NJ Transit service advisories from an official RSS feed. It helps users quickly
see affected routes, advisory details, effective windows, and change alerts.

## Features

- Live refresh of NJ Transit advisories from the official RSS feed
- Automatic extraction of affected routes, areas, and advisory types
- Effective window detection (e.g., "Effective Immediately" or time ranges)
- Change detection: new and revised advisories generate alerts
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
- `data/transit.db` — SQLite database
- `data/limit_50.py` — keeps the latest 50 advisories
- `data/backfill_windows.py` — backfills effective windows for existing records

## How to Run

1. Install dependencies:

```bat
pip install flask requests