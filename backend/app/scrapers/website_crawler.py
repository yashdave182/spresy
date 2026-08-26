import asyncio
import logging
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse, unquote

from bs4 import BeautifulSoup

from ..config import settings
from ..models import Lead
from ..utils.contact_extractor import extract_contacts_from_text, deobfuscate
from ..utils.http_client import HttpClient, fetch_text
from ..utils.robots import can_fetch, polite_sleep
from .base import BaseScraper

logger = logging.getLogger("spresy.crawler")

CONTACT_KEYWORDS = ("contact", "about", "contact-us", "team", "connect", "reach", "info")
SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".mp4",
    ".mp3", ".zip", ".exe", ".doc", ".docx", ".xls", ".xlsx", ".css", ".js",
)


class WebsiteCrawler(BaseScraper):
    """
    Crawls the websites of discovered leads to find contact pages
    and extract emails/phones. Strictly respects robots.txt.
    """

    name = "website"
    display_name = "Website Crawler"
    yields_leads = True

    def __init__(self, client: HttpClient, location: Optional[str] = None):
        super().__init__(client, location)
        self._sem = asyncio.Semaphore(settings.MAX_CONCURRENCY)

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        # This scraper is driven by website URLs supplied by the orchestrator.
        return []

    async def crawl_site(self, url: str, lead_name: str = "", max_pages: int = None) -> dict:
        max_pages = max_pages or settings.MAX_PAGES_PER_SITE
        url = url if url.startswith("http") else f"https://{url}"
        domain = urlparse(url).netloc

        async with self._sem:
            allowed, delay = await can_fetch(self.client._client, url)
            if not allowed:
                logger.info("robots.txt disallows crawling %s", domain)
                return {}
            await polite_sleep(delay)

        text = await fetch_text(self.client, url)
        if not text:
            return {}

        soup = BeautifulSoup(text, "lxml")
        contact_info = self._parse_page(soup, text, url)

        # Find up to N internal contact-related pages
        to_visit: List[Tuple[str, str]] = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            lower_href = unquote(href).lower()
            if not any(k in lower_href for k in CONTACT_KEYWORDS):
                continue
            if href.startswith(("#", "mailto:", "tel:", "javascript:", "//")):
                continue
            full = urljoin(url, href)
            parsed = urlparse(full)
            if parsed.netloc != domain or parsed.scheme not in ("http", "https"):
                continue
            if full.lower().endswith(SKIP_EXTENSIONS):
                continue
            to_visit.append((full, a.get_text(strip=True)))
            if len(to_visit) >= max_pages:
                break

        # Also add a plain /contact if present
        if not any(p[0].rstrip("/").endswith("contact") for p in to_visit):
            to_visit.append((urljoin(url, "/contact"), "contact"))

        for page_url, _ in to_visit:
            async with self._sem:
                allowed, delay = await can_fetch(self.client._client, page_url)
                if not allowed:
                    continue
                await polite_sleep(delay)
            page_text = await fetch_text(self.client, page_url)
            if not page_text:
                continue
            page_soup = BeautifulSoup(page_text, "lxml")
            page_info = self._parse_page(page_soup, page_text, page_url)
            self._merge_contacts(contact_info, page_info)

        # Title heuristic for name
        if not contact_info.get("name") and lead_name:
            contact_info["name"] = lead_name
        if not contact_info.get("name") and soup.title:
            contact_info["name"] = soup.title.get_text(strip=True)
        if not contact_info.get("website"):
            contact_info["website"] = url
        return contact_info

    def _parse_page(self, soup: BeautifulSoup, text: str, page_url: str) -> dict:
        info: dict = {"emails": set(), "phones": set(), "name": "", "address": "", "description": ""}
        try:
            info["title"] = soup.title.get_text(strip=True) if soup.title else ""
        except Exception:
            pass

        # mailto links are the highest-signal source
        for a in soup.select("a[href^='mailto:']"):
            href = a.get("href", "")
            email = href.split(":", 1)[-1].split("?", 1)[0]
            if email and "@" in email and email not in ("", "email"):
                info["emails"].add(email)

        for a in soup.select("a[href^='tel:']"):
            tel = a.get("href", "").split("tel:", 1)[-1]
            if tel:
                info["phones"].add(tel)

        for meta in soup.select("meta[name='description'], meta[property='og:description']"):
            if meta.get("content"):
                info["description"] = meta["content"][:500]
                break

        for meta in soup.select("meta[name='geo.region'], meta[property='business:city'], meta[name='city']"):
            if meta.get("content"):
                info["address"] = meta["content"][:200]
                break

        # Emails/phones from raw visible text
        raw_text = soup.get_text(" ", strip=True)[:120000]
        contacts = extract_contacts_from_text(deobfuscate(raw_text))
        info["emails"].update(contacts["emails"])
        info["phones"].update(contacts["phones"])
        return info

    def _merge_contacts(self, target: dict, other: dict):
        target.setdefault("emails", set())
        target.setdefault("phones", set())
        target["emails"].update(other.get("emails", set()))
        target["phones"].update(other.get("phones", set()))
        if not target.get("name") and other.get("title"):
            target["name"] = other["title"]
        if not target.get("description") and other.get("description"):
            target["description"] = other["description"]
        if not target.get("address") and other.get("address"):
            target["address"] = other["address"]

    def to_lead(self, info: dict, source: str, website: str) -> Optional[Lead]:
        emails = list(info.get("emails") or [])
        phones = list(info.get("phones") or [])
        return Lead(
            name=info.get("name") or info.get("title") or website,
            website=website,
            email=emails[0] if emails else None,
            phone=phones[0] if phones else None,
            description=info.get("description"),
            address=info.get("address"),
            source=source,
            verified=False,
        )
