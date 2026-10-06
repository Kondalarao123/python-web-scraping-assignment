"""HTTP layer: rate limiting, timeouts, retries with exponential backoff."""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import requests

from config import USER_AGENT

log = logging.getLogger(__name__)
RETRY_STATUS = {429, 500, 502, 503, 504}


class Fetcher:
    """Thread-safe page fetcher. `get()` returns HTML text or None on failure."""

    def __init__(self, timeout: float = 15.0, max_retries: int = 3,
                 backoff_factor: float = 1.0, delay: float = 0.2):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._rate_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._last_request = 0.0
        self.stats = {"requests": 0, "retries": 0, "failed_urls": 0}

    def _bump(self, key: str) -> None:
        with self._stats_lock:
            self.stats[key] += 1

    def _throttle(self) -> None:
        with self._rate_lock:
            wait = self._last_request + self.delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()

    def get(self, url: str) -> Optional[str]:
        attempts = self.max_retries + 1
        for attempt in range(1, attempts + 1):
            self._throttle()
            self._bump("requests")
            reason = None
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    resp.encoding = "utf-8"  # avoids 'Â£' mojibake on prices
                    return resp.text
                if resp.status_code in RETRY_STATUS:
                    reason = f"HTTP {resp.status_code}"
                else:  # 404, 403, ... retrying will not help
                    log.warning("GET %s -> HTTP %s (not retrying)", url, resp.status_code)
                    self._bump("failed_urls")
                    return None
            except requests.Timeout:
                reason = "timeout"
            except requests.ConnectionError as exc:
                reason = f"connection error ({exc.__class__.__name__})"
            except requests.RequestException as exc:
                reason = f"request error ({exc.__class__.__name__})"

            if attempt < attempts:
                sleep_for = self.backoff_factor * (2 ** (attempt - 1))
                log.warning("GET %s failed: %s. Retry %d/%d in %.1fs",
                            url, reason, attempt, self.max_retries, sleep_for)
                self._bump("retries")
                time.sleep(sleep_for)
            else:
                log.error("GET %s failed after %d attempts: %s", url, attempts, reason)
        self._bump("failed_urls")
        return None
