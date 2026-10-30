# Source Approval Document — NJ TRANSIT Bus Advisories

## 1. Data Source
- Source: NJ TRANSIT Bus Advisories RSS feed
- URL: https://www.njtransit.com/bus-advisories (RSS XML)
- Type: Public RSS feed (XML)
- Access: Free, no login, no API key required

## 2. Permissions & Compliance
- robots.txt reviewed: RSS feed is publicly provided for consumption
- Site terms: public transit advisories, intended for public information
- No login bypass, no CAPTCHA evasion, no private data collected
- Only publicly published advisory text is used
- Attribution: "Source: NJ TRANSIT" shown in dashboard

## 3. Fields Extracted
- Route code (from title)
- Advisory text / summary
- Posted date (pubDate)
- Valid window (start/end date parsed from text)
- Advisory type (detour / cancellation / delay / other)
- Source URL
- Content hash (for change detection)
- Revision ID

## 4. Crawl Policy / Schedule
- Refresh: manual trigger (demo) / scheduled daily refresh (production)
- Rate limit: 1 request per refresh cycle (polite crawling)
- Timeout: 10 seconds per request
- Retry: up to 2 retries with backoff on failure
- Failure logged, old data retained (not marked live)

## 5. Risks
- Site structure change may break parser → parser tests + failure logs
- Feed unavailable → graceful degradation, stale data labeled clearly
- Date format variation → regex-based parsing with fallback
- Duplicate notices → content hash dedup

## 6. Alternatives Considered
- NJ TRANSIT official API (if available) — preferred for structured data
- Mobile app notifications — not accessible programmatically
- Third-party aggregator — avoided (unofficial, may be stale)

## 7. Data Minimization
- Only advisory-related fields stored
- No personal data collected
- Display limited to 50 latest unique notices
- Old/expired advisories archived with status flag