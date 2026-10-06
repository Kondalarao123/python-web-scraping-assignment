# Multi-Source Web Scraping & Data Consolidation

A Python pipeline that scrapes **Books to Scrape** and **Quotes to Scrape**, maps both to one
common schema, cleans and validates the records, removes duplicates and writes a single
consolidated dataset plus a summary report.

```
Books ─┐
       ├─> Scrape ─> Clean ─> Validate ─> Deduplicate ─> Consolidate ─> output/
Quotes ┘
```

## Python version
Python 3.9 or newer (developed on 3.12).

## Setup
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Dependencies: `requests`, `beautifulsoup4`, `pytest` (tests only).

## How to run
```bash
python main.py                      # full run (all pages, book detail pages included)
python main.py --max-pages 3        # quick trial run
python main.py --skip-details       # much faster; book category/description stay empty
python main.py --sources quotes     # one source only
python main.py --delay 0.5 --workers 2   # be gentler on the server
python -m pytest -q                 # run the tests (fully offline)
```
Other options: `--output-dir`, `--log-dir`, `--log-level`. A full run opens ~1,000 book detail
pages, so expect a few minutes with the default 0.2 s delay.

## Output
| File | Content |
|---|---|
| `output/final_dataset.csv` | consolidated, cleaned, de-duplicated records |
| `output/summary_report.json` | counts per source, rejection reasons, duplicates, timing, HTTP stats |
| `output/rejected_records.csv` | records that failed validation + the reasons |
| `output/duplicates_removed.csv` | removed duplicates + why and which record they duplicate |
| `logs/scrape_<timestamp>.log` | full execution log |

## Project structure
```
main.py            CLI + logging setup          pipeline.py     orchestration + file output
config.py          constants / settings         http_client.py  retries, backoff, rate limit
scrapers/          books_scraper.py, quotes_scraper.py (all selectors live here)
processing/        cleaning.py, validation.py, deduplication.py
tests/             26 offline tests using HTML fixtures
```
Scraping logic and transformation logic are separate: scrapers return *raw* values (e.g. `"£51.77"`,
`"Three"`), and `processing/` turns them into clean values.

## How pagination works
Both scrapers start at the home page and follow the `li.next a` link on each page until it no
longer exists. No page numbers are hard-coded, so if the sites add pages the scraper follows them.
A `visited` set prevents infinite loops. If a listing page fails after all retries, pagination for
that source stops (the next link can't be discovered) but data already collected is kept and the
other source still runs. `--max-pages` limits pages for trial runs.

## Data model
`source, source_url, name_or_title, category, price, currency, rating, author, tags, description, availability, scraped_at`

| Field | Books to Scrape | Quotes to Scrape |
|---|---|---|
| name_or_title | book title (from the link's `title` attribute, so it isn't truncated) | quote text |
| source_url | the book's own product URL | the listing page the quote appeared on (quotes have no page of their own) |
| category | breadcrumb on the detail page | empty |
| price / currency | numeric price / `GBP` | empty |
| rating | integer 1–5 | empty |
| author | empty (site doesn't publish it) | quote author |
| tags | empty | `|`-separated, lower-case |
| description | detail-page description | empty |
| availability | e.g. "In stock" | empty |

Fields that don't apply stay empty. Nothing is invented. `currency` and `availability` are two
columns I added beyond the suggested list because the price is meaningless without its currency
and availability is listed in the task description.

## Cleaning approach (`processing/cleaning.py`)
- Collapse whitespace (including non-breaking spaces), trim; empty strings and placeholders
  (`N/A`, `-`, `null`…) become empty/None.
- Unicode NFKC normalisation; the decorative quote marks wrapping each quote are removed.
- Price: first number in the string, so `£51.77` and the mojibake `Â£51.77` both give `51.77`.
  Responses are decoded as UTF-8 explicitly to avoid the mojibake in the first place.
- Rating: star-class word (`Three`) → integer `3`.
- URLs: made absolute, scheme/host lower-cased, fragments removed, non-http(s) rejected.
- Tags: lower-cased, trimmed, de-duplicated.

## Validation approach (`processing/validation.py`)
Checked before anything reaches the final dataset; failures are logged, counted per reason and
written to `rejected_records.csv`:
- known source; required fields per source (books: title, URL, price, rating; quotes: text, URL, author)
- price numeric and non-negative when present; rating numeric and within 1–5
- URL present and valid-looking (http/https with a host)

## Deduplication approach (`processing/deduplication.py`)
Duplicate key = **source + normalised title/text + normalised author**. Normalisation: remove
accents, case-fold, replace punctuation with spaces, collapse whitespace – so `"Example Book Title"`,
`" Example Book Title "` and `"EXAMPLE BOOK TITLE"` are the same. For Books, a second rule treats
identical product URLs as duplicates (not applied to quotes, because all quotes on a page share
the page URL). The first occurrence is kept.

**Why remove instead of flag:** the final dataset should be directly usable. To avoid losing
information, every removed record is written to `duplicates_removed.csv` with the reason and the
title it duplicates, and counts appear in the summary.
Note: on the live sites I expect few or no duplicates, since each item appears once; the logic is
covered by unit tests with deliberately messy variants.

## Error-handling approach
- `http_client.Fetcher`: timeout on every request; retry on timeouts, connection errors and
  HTTP 429/5xx with exponential backoff (1 s, 2 s, 4 s); no retry on 404/403; global rate limit.
- A missing HTML element becomes `None`, not a crash; a card that raises is logged and skipped.
- A failed book detail page only leaves category/description empty for that book.
- One source failing completely does not stop the other.
- Cleaning/validation never raise for bad data – bad records are rejected with a reason.

## Assumptions
- `source_url` for a quote is its listing page (no per-quote URL exists).
- A book without a price or rating is considered invalid (both are always shown on the site).
- Title + author is a good identity for a quote/book within one source.

## Known limitations
- Book category/description need one extra request per book (~1,000), so a full run is slower;
  `--skip-details` trades those fields for speed.
- No incremental/resume support; each run starts from scratch.
- Cross-source duplicate detection is not needed here (books and quotes are different entities)
  and not implemented.
- Parsers rely on the current HTML structure of the two practice sites.

## Bonus features included
Retry with exponential backoff, configurable settings + CLI arguments, unit tests (26),
rate limiting, threaded detail-page fetching.

## AI usage summary
See `AI_USAGE.md`.
