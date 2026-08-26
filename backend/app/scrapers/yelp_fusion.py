import logging
from typing import List
from urllib.parse import quote_plus

import httpx

from ..config import settings
from .base import BaseScraper

logger = logging.getLogger("spresy.yelpfusion")


class YelpFusionScraper(BaseScraper):
    """
    Tier 1 official API. Yelp Fusion Business Search.
    Requires YELP_FUSION_API_KEY (free tier available).
    """

    name = "yelp_fusion"
    display_name = "Yelp Fusion (API)"
    yields_leads = True
    tier = 1

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        if not settings.YELP_FUSION_API_KEY:
            logger.info("YELP_FUSION_API_KEY not set; skipping.")
            return []
        results: List[dict] = []
        params = {
            "term": query,
            "limit": min(limit, 50),
            "categories": "localflavor",
        }
        if self.location:
            params["location"] = self.location
        else:
            params["location"] = "India"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.yelp.com/v3/businesses/search",
                    params=params,
                    headers={"Authorization": f"Bearer {settings.YELP_FUSION_API_KEY}"},
                )
                data = resp.json()
                for biz in data.get("businesses", [])[:limit]:
                    location = biz.get("location") or {}
                    address = " ".join([a for a in location.get("display_address", []) if a]) or None
                    results.append({
                        "name": biz.get("name", ""),
                        "website": biz.get("url"),  # yelp listing; real site via details
                        "phone": biz.get("phone"),
                        "address": address,
                        "rating": biz.get("rating"),
                        "description": ", ".join(c.get("title", "") for c in biz.get("categories", [])),
                        "category": ", ".join(c.get("title", "") for c in biz.get("categories", [])[:2]),
                        "verified": True,
                        "source": "yelp_fusion",
                    })
        except Exception as e:
            logger.warning("Yelp Fusion search failed for %s: %s", query, e)
        return results
