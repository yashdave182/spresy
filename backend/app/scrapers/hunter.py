import logging
from typing import List, Optional

import httpx

from ..config import settings
from .base import BaseScraper

logger = logging.getLogger("spresy.hunter")


class HunterScraper(BaseScraper):
    """
    Tier 1 email-finder API (Hunter.io). Given a domain or a search query,
    returns verified business emails. Paid but legal & high quality.
    Requires HUNTER_API_KEY.
    """

    name = "hunter"
    display_name = "Hunter.io (API)"
    yields_leads = True
    tier = 1
    # Used as an enrichment source: given a website, find emails.
    is_enricher = True

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        if not settings.HUNTER_API_KEY:
            logger.info("HUNTER_API_KEY not set; skipping.")
            return []
        results: List[dict] = []
        # Hunter domain search expects a domain; query may be a URL or a company name.
        domain = self._domain_from(query)
        if not domain:
            return results
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.hunter.io/v2/domain-search",
                    params={"domain": domain, "api_key": settings.HUNTER_API_KEY, "limit": min(limit, 25)},
                )
                data = resp.json().get("data", {})
                for email in data.get("emails", [])[:limit]:
                    results.append({
                        "name": data.get("organization") or domain,
                        "website": f"https://{domain}",
                        "email": email.get("value"),
                        "verified": bool(email.get("verified")),
                        "source": "hunter",
                    })
        except Exception as e:
            logger.warning("Hunter search failed for %s: %s", query, e)
        return results

    async def find_emails_for_domain(self, domain: str) -> Optional[str]:
        """Enrichment helper: get the first usable email for a domain."""
        if not settings.HUNTER_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.hunter.io/v2/domain-search",
                    params={"domain": domain, "api_key": settings.HUNTER_API_KEY, "limit": 5},
                )
                emails = resp.json().get("data", {}).get("emails", [])
                for email in emails:
                    value = email.get("value", "")
                    if value and "hunter.io" not in value:
                        return value
        except Exception:
            pass
        return None

    @staticmethod
    def _domain_from(text: str) -> Optional[str]:
        import re
        from urllib.parse import urlparse

        text = text.strip().lower()
        if "://" in text:
            return urlparse(text).netloc.replace("www.", "")
        m = re.search(r"([a-z0-9\-]+\.)+(com|in|co\.in|net|org|io)(\/[^\s]*)?", text)
        if m:
            return m.group(0).split("/")[0]
        return None
