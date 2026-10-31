# TransitNotice — Final Project Report

## Cover Page

**Project Title:** TransitNotice — Public Transport Service Update Tracker

**Student Name:** Leena Sri .S

**Internship Program:** Web Scraping (WEB-07) — Cybernaut Edtech

**Mentor:** Santhiya

**Academic Year:** 2026

---

## Abstract & Context

Passengers need clear updates about route diversions and planned service interruptions. TransitNotice monitors official public transit advisories, extracts affected routes and validity windows, and displays searchable notices with freshness labels.

**User Personas:**
1. **Daily Commuter (Leena)** — Needs quick, route-specific alerts about diversions or delays before starting travel.
2. **Transit Operator / Support Staff** — Needs to track advisory history, detect withdrawn or revised notices, and maintain an audit trail.

**Usefulness of scheduled monitoring:** Provides timely updates without manual checking.
**Limitations:** Source downtime, parsing errors, delayed publication on the authority site.

---

## Source Selection

- Official public transit advisory page (NJ Transit / MTC), no login required
- robots.txt and site terms reviewed; no CAPTCHA evasion or private data collection
- Crawl policy: manual/scheduled refresh, request timeout, retry with backoff, failure logs
- Full details in `SOURCE_APPROVAL.md`

---

## Implementation

- **Scraper (`scraper.py`)** — fetches advisories, normalizes fields, detects new/revised/extended/withdrawn changes
- **Database (`transit.db`)** — SQLite with `advisories`, `alert_log`, `subscribers` tables
- **Idempotent upserts** using `content_hash`; revision tracking via `revision_id`
- **Flask dashboard (`dashboard.py`)** — route, area, station, service date, status filters + full-text search
- **Freshness badge** — FRESH (≤24h) / STALE based on `last_confirmed_at`
- **Alert mechanism** — one alert per new/revised advisory, deduplication via `dedupe_key`, delivery logs

---

## SRS & ER Diagram

**Use Cases:**
- View active advisories
- Filter by route / area / station / service date / status
- Search notice text
- Refresh advisories
- View alert history
- Store subscriber filter preferences

**ER Diagram:**

```text
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│   advisories     │       │    alert_log     │       │   subscribers    │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ notice_id PK     │──1:N──│ alert_id PK      │       │ subscriber_id PK │
│ agency           │       │ notice_id FK     │       │ name             │
│ route_id         │       │ change_type      │       │ email            │
│ area             │       │ dedupe_key       │       │ route_filter     │
│ source_url       │       │ message          │       │ area_filter      │
│ advisory_type    │       │ delivery_status  │       │ created_at       │
│ summary          │       │ created_at       │       └──────────────────┘
│ published_at     │       │ delivered_at     │
│ valid_from/to    │       └──────────────────┘
│ status           │
│ observed_at      │
│ last_confirmed_at│
│ content_hash     │
│ revision_id      │
│ change_summary   │
└──────────────────┘