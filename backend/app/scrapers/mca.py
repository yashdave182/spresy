import logging
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger("spresy.mca")


class MCAScraper(BaseScraper):
    """
    Tier 1 India company registry (MCA - Ministry of Corporate Affairs).
    Uses the public MCA master data API endpoints. No key required.
    Yields registered Indian companies (name, CIN, address).
    """

    name = "mca"
    display_name = "MCA India (registry)"
    yields_leads = True
    tier = 1

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        # Try MCA public company name search JSON endpoint
        try:
            resp = await self.client.get(
                "https://www.mca.gov.in/mcafoportal/showCompanyData.do",
                params={"companyName": query},
            )
            if resp.status_code == 200:
                # Parse HTML table if present
                soup = BeautifulSoup(resp.text, "lxml")
                rows = soup.select("table tr")
                for row in rows[1:limit + 1]:
                    cells = row.find_all("td")
                    if len(cells) < 2:
                        continue
                    name = cells[0].get_text(strip=True)
                    if name and name.lower() not in ("company name", ""):
                        results.append({
                            "name": name,
                            "cin": cells[1].get_text(strip=True) if len(cells) > 1 else None,
                            "address": cells[2].get_text(strip=True) if len(cells) > 2 else None,
                            "verified": True,
                            "source": "mca",
                        })
        except Exception as e:
            logger.debug("MCA HTML search failed: %s", e)

        # Fallback: MCA master data API (JSON) used by their portal
        if not results:
            try:
                resp = await self.client.post(
                    "https://www.mca.gov.in/mcafoportal/showCompanyNameData.do",
                    data={"company": query, "searchType": "MNC"},
                )
                import json
                try:
                    data = resp.json()
                    for item in data if isinstance(data, list) else data.get("data", []):
                        if len(results) >= limit:
                            break
                        results.append({
                            "name": item.get("COMPANY_NAME") or item.get("companyName", ""),
                            "cin": item.get("CIN") or item.get("cin"),
                            "address": item.get("REGISTERED_OFFICE_ADDRESS") or item.get("address"),
                            "verified": True,
                            "source": "mca",
                        })
                except Exception:
                    pass
            except Exception as e:
                logger.debug("MCA JSON search failed: %s", e)
        return results
