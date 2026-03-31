from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse


class RateLimitedClient:
    """HTTP client with per-domain rate limiting and retry on 429."""

    USER_AGENT = "MTGDeckRec/0.1.0"
    DEFAULT_DELAY = 0.15  # seconds between requests per domain

    def __init__(self, delay: float = DEFAULT_DELAY):
        self._delay = delay
        self._last_request: dict[str, float] = {}

    def _wait_for_rate_limit(self, domain: str) -> None:
        last = self._last_request.get(domain, 0.0)
        elapsed = time.monotonic() - last
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)

    def _record_request(self, domain: str) -> None:
        self._last_request[domain] = time.monotonic()

    def get_json(self, url: str, max_retries: int = 3) -> dict:
        domain = urlparse(url).netloc
        self._wait_for_rate_limit(domain)

        request = urllib.request.Request(
            url,
            headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"},
        )

        for attempt in range(max_retries):
            try:
                self._record_request(domain)
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < max_retries - 1:
                    retry_after = float(e.headers.get("Retry-After", 2))
                    time.sleep(retry_after)
                    continue
                raise APIError(f"HTTP {e.code} from {domain}: {e.reason}") from e
            except urllib.error.URLError as e:
                raise APIError(f"Network error for {domain}: {e.reason}") from e

        raise APIError(f"Max retries exceeded for {url}")


class APIError(Exception):
    pass


# Shared singleton — import and use directly
client = RateLimitedClient()
