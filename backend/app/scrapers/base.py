import logging
from typing import List, Optional

from ..models import Lead
from ..utils.http_client import HttpClient

logger = logging.getLogger("spresy.scraper")


class BaseScraper:
    """Base class for all source adapters."""

    name = "base"
    display_name = "Base"
    # Whether this adapter returns lead objects directly (with contact info)
    yields_leads = False

    def __init__(self, client: HttpClient, location: Optional[str] = None):
        self.client = client
        self.location = location

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        """Main entry point. Returns raw results (dicts) or Lead objects."""
        raise NotImplementedError

    async def close(self):
        pass

    @staticmethod
    def _to_lead(data: dict, source: str) -> Lead:
        return Lead(**{**data, "source": source})
