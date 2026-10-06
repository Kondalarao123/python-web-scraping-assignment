"""Central configuration and constants."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

BOOKS_SOURCE = "Books to Scrape"
QUOTES_SOURCE = "Quotes to Scrape"
BOOKS_START_URL = "https://books.toscrape.com/"
QUOTES_START_URL = "https://quotes.toscrape.com/"
USER_AGENT = "Mozilla/5.0 (compatible; ScrapingAssignmentBot/1.0; educational use)"

# Final CSV column order.
OUTPUT_COLUMNS = [
    "source", "source_url", "name_or_title", "category", "price", "currency",
    "rating", "author", "tags", "description", "availability", "scraped_at",
]


@dataclass
class Config:
    output_dir: str = "output"
    log_dir: str = "logs"
    sources: Tuple[str, ...] = ("books", "quotes")
    max_pages: Optional[int] = None      # None = follow pagination to the end
    fetch_book_details: bool = True      # needed for category + description
    workers: int = 4                     # threads used for book detail pages
    request_delay: float = 0.2           # seconds between requests (global)
    timeout: float = 15.0
    max_retries: int = 3                 # retries after the first attempt
    backoff_factor: float = 1.0          # sleep = factor * 2**(attempt-1)
