import asyncio
import logging
from typing import Optional

import httpx

from ..config import settings

logger = logging.getLogger("spresy.http")


class HttpClient:
    """Shared HTTP client with rate limiting & robots.txt awareness."""

    def __init__(self):
        self._sem = asyncio.Semaphore(settings.MAX_CONCURRENCY)
        self._client: Optional[httpx.AsyncClient] = None
        self.last_request_time: dict = {}

    async def __aenter__(self):
        headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(settings.REQUEST_TIMEOUT),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=settings.MAX_CONCURRENCY + 2, max_keepalive_connections=10),
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get(self, url: str, **kwargs) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("HttpClient used outside async context")
        async with self._sem:
            # Simple global rate limiter: space requests by default delay
            now = asyncio.get_event_loop().time()
            await polite_spacing(now, settings.DEFAULT_DELAY_SECONDS)
            resp = await self._client.get(url, **kwargs)
            return resp


async def polite_spacing(now: float, min_interval: float):
    """Naive global spacing between requests."""
    # Placeholder to keep signature stable; real per-host spacing handled in robots.py
    pass


async def fetch_text(client: HttpClient, url: str, max_bytes: int = 3 * 1024 * 1024) -> Optional[str]:
    """Fetch a URL and return its text content (limited size). Returns None on failure."""
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return None
        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type and "xml" not in content_type and "text" not in content_type:
            # Could still be a JSON-LD rich result
            if "json" not in content_type:
                return None
        data = resp.content[:max_bytes]
        # Try common encodings
        for enc in ("utf-8", "latin-1"):
            try:
                return data.decode(enc, errors="replace")
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug("fetch_text failed for %s: %s", url, e)
        return None
