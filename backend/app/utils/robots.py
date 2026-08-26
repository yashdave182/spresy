import asyncio
import random
import urllib.robotparser
from functools import lru_cache
from typing import Optional, Tuple
from urllib.parse import urlparse

from ..config import settings

# Per-host robots.txt parser cache
_robots_cache: dict = {}
_lock = asyncio.Lock()


@lru_cache(maxsize=256)
def _get_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def robots_url_for(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


async def _fetch_robots(client, url: str) -> Optional[str]:
    try:
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code == 200 and "text" in resp.headers.get("content-type", "text/plain"):
            return resp.text
    except Exception:
        return None
    return None


async def can_fetch(client, url: str, user_agent: str = None) -> Tuple[bool, float]:
    """Returns (allowed, polite_delay_seconds). Loads & caches robots.txt per domain."""
    ua = user_agent or settings.USER_AGENT
    domain = _get_domain(url)
    if not domain:
        return True, 0.0

    async with _lock:
        if domain in _robots_cache:
            entry = _robots_cache[domain]
        else:
            robots_txt = await _fetch_robots(client, robots_url_for(url))
            rp = urllib.robotparser.RobotFileParser()
            if robots_txt:
                rp.parse(robots_txt.splitlines())
            delay = rp.crawl_delay(ua) or rp.crawl_delay("*")
            delay = delay or settings.DEFAULT_DELAY_SECONDS
            entry = (rp, delay)
            _robots_cache[domain] = entry

    rp, delay = entry
    if not rp.disallow_all and not rp.allow_all:
        # robots.txt missing/empty -> allowed
        return True, delay or 0.0
    allowed = rp.can_fetch(ua, url)
    return allowed, delay or 0.0


async def polite_sleep(delay: float):
    """Add jitter to avoid hammering servers."""
    await asyncio.sleep(delay * random.uniform(0.8, 1.4))
