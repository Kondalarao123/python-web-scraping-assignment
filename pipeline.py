"""Orchestration: scrape -> clean -> validate -> deduplicate -> consolidate -> write."""
from __future__ import annotations

import csv
import json
import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

from config import BOOKS_SOURCE, OUTPUT_COLUMNS, QUOTES_SOURCE, Config
from processing.cleaning import clean_record
from processing.deduplication import deduplicate
from processing.validation import validate_record
from scrapers.books_scraper import scrape_books
from scrapers.quotes_scraper import scrape_quotes

log = logging.getLogger(__name__)


def _csv_row(rec: Dict[str, Any], columns: List[str]) -> Dict[str, Any]:
    row = {c: rec.get(c) for c in columns}
    if "tags" in row:
        row["tags"] = "|".join(rec.get("tags") or [])
    return {k: ("" if v is None else v) for k, v in row.items()}


def _write_csv(path: str, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for rec in rows:
            writer.writerow(_csv_row(rec, columns))


def run_pipeline(config: Config, fetcher) -> Dict[str, Any]:
    started = time.time()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    os.makedirs(config.output_dir, exist_ok=True)

    # 1. Scrape (a failing source never stops the other one)
    raw: List[Dict[str, Any]] = []
    scrape_stats: Dict[str, Dict[str, int]] = {}
    jobs = {
        "books": (BOOKS_SOURCE, lambda: scrape_books(
            fetcher, config.max_pages, config.fetch_book_details, config.workers)),
        "quotes": (QUOTES_SOURCE, lambda: scrape_quotes(fetcher, config.max_pages)),
    }
    for key in config.sources:
        label, job = jobs[key]
        try:
            result = job()
            raw.extend(result.records)
            scrape_stats[label] = result.stats
        except Exception:
            log.exception("Source %s failed completely; continuing with others", label)
            scrape_stats[label] = {"source_failed": 1}

    # 2. Clean
    cleaned, rejected = [], []
    collected = Counter(r.get("source") for r in raw)
    for r in raw:
        try:
            cleaned.append(clean_record(r))
        except Exception as exc:
            log.exception("Cleaning failed for %s", r.get("source_url"))
            rejected.append({**r, "rejection_reasons": f"cleaning_error:{exc.__class__.__name__}"})
    after_cleaning = Counter(r.get("source") for r in cleaned)

    # 3. Validate
    valid, reason_counts = [], Counter()
    for rec in cleaned:
        errors = validate_record(rec)
        if errors:
            reason_counts.update(errors)
            log.warning("Rejected %r (%s): %s", rec.get("name_or_title"), rec.get("source"), errors)
            rejected.append({**rec, "rejection_reasons": ";".join(errors)})
        else:
            valid.append(rec)

    # 4. Deduplicate (remove, but keep a record of what was removed and why)
    unique, duplicates = deduplicate(valid)
    dup_reasons = Counter(d["duplicate_reason"] for d in duplicates)
    for d in duplicates:
        log.info("Duplicate removed: %r duplicates %r (%s)", d.get("name_or_title"),
                 d.get("duplicate_of_title"), d["duplicate_reason"])

    # 5. Consolidate + write
    final_path = os.path.join(config.output_dir, "final_dataset.csv")
    _write_csv(final_path, unique, OUTPUT_COLUMNS)
    _write_csv(os.path.join(config.output_dir, "rejected_records.csv"), rejected,
               OUTPUT_COLUMNS + ["rejection_reasons"])
    _write_csv(os.path.join(config.output_dir, "duplicates_removed.csv"), duplicates,
               OUTPUT_COLUMNS + ["duplicate_reason", "duplicate_of_title"])

    rejected_by_source = Counter(r.get("source") for r in rejected)
    dup_by_source = Counter(d.get("source") for d in duplicates)
    final_by_source = Counter(r.get("source") for r in unique)
    labels = [BOOKS_SOURCE, QUOTES_SOURCE]
    summary = {
        "run_started_at": started_at,
        "execution_time_seconds": round(time.time() - started, 2),
        "sources": {
            lab: {
                "collected": collected.get(lab, 0),
                "after_cleaning": after_cleaning.get(lab, 0),
                "rejected": rejected_by_source.get(lab, 0),
                "duplicates_removed": dup_by_source.get(lab, 0),
                "final": final_by_source.get(lab, 0),
                "scrape_stats": scrape_stats.get(lab, {}),
            } for lab in labels if lab in scrape_stats
        },
        "totals": {
            "collected": len(raw),
            "after_cleaning": len(cleaned),
            "rejected": len(rejected),
            "duplicates_removed": len(duplicates),
            "final": len(unique),
        },
        "rejection_reasons": dict(reason_counts),
        "duplicate_reasons": dict(dup_reasons),
        "http": dict(getattr(fetcher, "stats", {})),
    }
    with open(os.path.join(config.output_dir, "summary_report.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    log.info("Pipeline finished: %s", summary["totals"])
    return summary
