import logging
import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger("spresy.zaubacorp")


class ZaubaCorpScraper(BaseScraper):
    """
    Tier 2. Zauba Corp — Indian company registry aggregator.
    Yields registered company name, CIN, and registered address.
    """

    name = "zaubacorp"
    display_name = "Zauba Corp (IN companies)"
    yields_leads = True
    tier = 2

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        url = f"https://www.zaubacorp.com/companysearchresults/{quote_plus(query)}"
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                return results
            soup = BeautifulSoup(resp.text, "lxml")
            for row in soup.select("table tr")[:limit + 1]:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                name = cells[0].get_text(strip=True)
                if not name or len(name) < 5:
                    continue
                cin = cells[1].get_text(strip=True) if len(cells) > 1 else None
                registered = cells[2].get_text(strip=True) if len(cells) > 2 else None
                results.append({
                    "name": name,
                    "cin": cin,
                    "address": registered,
                    "description": f"CIN: {cin}" if cin else "",
                    "verified": True,
                    "source": "zaubacorp",
                })
        except Exception as e:
            logger.warning("ZaubaCorp search failed for %s: %s", query, e)
        return results
