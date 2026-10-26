"""Polite HTTP client for nsearchives.nseindia.com with an on-disk cache."""

import time
from pathlib import Path

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)


class NseClient:
    def __init__(self, cache_dir: Path, min_interval: float = 0.4, retries: int = 3, timeout: float = 30.0):
        self.cache_dir = cache_dir
        self.min_interval = min_interval
        self.retries = retries
        self._last_request = 0.0
        self._http = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            timeout=timeout,
            follow_redirects=True,
        )

    def fetch(self, url: str, cache_key: str, use_cache: bool = True,
              headers: dict[str, str] | None = None) -> bytes | None:
        """Return the file body, or None when NSE has no file at that URL (404)."""
        path = self.cache_dir / cache_key
        if use_cache and path.exists():
            return path.read_bytes()

        for attempt in range(self.retries):
            self._throttle()
            try:
                resp = self._http.get(url, headers=headers)
            except httpx.TransportError:
                if attempt == self.retries - 1:
                    raise
                time.sleep(2**attempt)
                continue
            if resp.status_code == 404:
                return None
            if resp.status_code >= 500 or resp.status_code in (403, 429):
                if attempt == self.retries - 1:
                    resp.raise_for_status()
                time.sleep(2 ** (attempt + 1))
                continue
            resp.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(resp.content)
            return resp.content
        return None

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def close(self) -> None:
        self._http.close()
