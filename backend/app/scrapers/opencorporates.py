import logging
from typing import List
from urllib.parse import quote_plus

import httpx

from ..config import settings
from .base import BaseScraper

logger = logging.getLogger("spresy.opencorporates")

# Map country to OpenCorporates jurisdiction code
JURISDICTION = {
    "india": "in",
    "united kingdom": "gb",
    "uk": "gb",
    "us": "us",
    "usa": "us",
    "united states": "us",
}


class OpenCorporatesScraper(BaseScraper):
    """
    Tier 1 official API. OpenCorporates company registry search.
    Uses the 'in' jurisdiction for India-first lookups.
    Free tier works without a key (rate-limited).
    """

    name = "opencorporates"
    display_name = "OpenCorporates (API)"
    yields_leads = True
    tier = 1

    def _jurisdiction(self) -> str:
        if not self.location:
            return "in"  # India-first default
        loc = self.location.lower()
        for key, code in JURISDICTION.items():
            if key in loc:
                return code
        # Likely Indian city if not matched
        return "in"

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        jurisdiction = self._jurisdiction()
        results: List[dict] = []
        params = {"q": query, "jurisdiction_code": jurisdiction, "per_page": min(limit, 25)}
        if settings.OPENCORPORATES_API_KEY:
            params["api_token"] = settings.OPENCORPORATES_API_KEY
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get("https://api.opencorporates.com/v0.4/companies/search", params=params)
                data = resp.json()
                for item in data.get("results", [])[:limit]:
                    company = item.get("company", {})
                    address = company.get("registered_address_in_full") or company.get("registered_address")
                    results.append({
                        "name": company.get("name", ""),
                        "website": company.get("homepage_url"),
                        "address": address,
                        "city": company.get("registered_address_in_full", "").split(",")[0] if isinstance(company.get("registered_address_in_full"), str) else None,
                        "description": f"Company #{company.get('company_number')} · {company.get('company_type', '')}".strip(),
                        "category": company.get("industry_codes", [{}])[0].get("industry_description") if company.get("industry_codes") else None,
                        "verified": True,
                        "source": "opencorporates",
                    })
        except Exception as e:
            logger.warning("OpenCorporates search failed for %s: %s", query, e)
        return results
