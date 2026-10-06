"""CLI entry point:  python main.py [--max-pages N] [--skip-details] ..."""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime

from config import Config
from http_client import Fetcher
from pipeline import run_pipeline


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Multi-source scraping & consolidation pipeline")
    p.add_argument("--sources", nargs="+", choices=["books", "quotes"], default=["books", "quotes"])
    p.add_argument("--max-pages", type=int, default=None, help="limit pages per source (default: all)")
    p.add_argument("--skip-details", action="store_true",
                   help="do not open book detail pages (faster; category/description stay empty)")
    p.add_argument("--workers", type=int, default=4, help="threads for book detail pages")
    p.add_argument("--delay", type=float, default=0.2, help="seconds between requests")
    p.add_argument("--output-dir", default="output")
    p.add_argument("--log-dir", default="logs")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args(argv)


def setup_logging(log_dir: str, level: str) -> str:
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"scrape_{datetime.now():%Y%m%d_%H%M%S}.log")
    fmt = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    logging.basicConfig(level=getattr(logging, level), format=fmt,
                        handlers=[logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()])
    return path


def main(argv=None) -> int:
    args = parse_args(argv)
    log_path = setup_logging(args.log_dir, args.log_level)
    config = Config(output_dir=args.output_dir, log_dir=args.log_dir, sources=tuple(args.sources),
                    max_pages=args.max_pages, fetch_book_details=not args.skip_details,
                    workers=args.workers, request_delay=args.delay)
    fetcher = Fetcher(timeout=config.timeout, max_retries=config.max_retries,
                      backoff_factor=config.backoff_factor, delay=config.request_delay)
    summary = run_pipeline(config, fetcher)
    t = summary["totals"]
    print(f"\nDone in {summary['execution_time_seconds']}s | collected={t['collected']} "
          f"rejected={t['rejected']} duplicates={t['duplicates_removed']} final={t['final']}")
    print(f"Output: {config.output_dir}/final_dataset.csv, summary_report.json | Log: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
