import asyncio
import logging
from typing import Optional

from ..config import settings

logger = logging.getLogger("spresy.playwright")

_browser = None
_lock = asyncio.Lock()


async def _get_browser():
    """Lazily launch a headless Chromium browser (one per process)."""
    global _browser
    async with _lock:
        if _browser is None:
            try:
                from playwright.async_api import async_playwright
                pw = await async_playwright().start()
                _browser = await pw.chromium.launch(headless=True)
            except Exception as e:
                logger.warning("Playwright not available (%s). Install with: pip install playwright && playwright install chromium", e)
                return None
    return _browser


async def playwright_fetch(url: str, wait_selector: Optional[str] = None, wait_ms: int = 3500) -> Optional[str]:
    """
    Fetch a JS-rendered page using headless Chromium.
    Returns rendered HTML or None if Playwright is unavailable.
    """
    if not settings.USE_PLAYWRIGHT:
        return None
    browser = await _get_browser()
    if not browser:
        return None
    try:
        page = await browser.new_page(
            user_agent=settings.USER_AGENT,
            locale="en-IN",
            viewport={"width": 1366, "height": 768},
        )
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        if wait_selector:
            try:
                await page.wait_for_selector(wait_selector, timeout=15000)
            except Exception:
                pass
        else:
            await page.wait_for_timeout(wait_ms)
        html = await page.content()
        await page.close()
        return html
    except Exception as e:
        logger.warning("Playwright fetch failed for %s: %s", url, e)
        try:
            await page.close()
        except Exception:
            pass
        return None
