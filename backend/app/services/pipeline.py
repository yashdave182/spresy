import asyncio
import logging
from typing import List, Optional, Set
from urllib.parse import urlparse

from ..config import settings
from ..models import JobInfo, JobProgress, Lead, LeadStatus, ScrapeRequest
from ..scrapers.bbb import BBBScraper
from ..scrapers.bing import BingScraper
from ..scrapers.duckduckgo import DuckDuckGoScraper
from ..scrapers.google_maps import GoogleMapsScraper
from ..scrapers.google_places import GooglePlacesScraper
from ..scrapers.hunter import HunterScraper
from ..scrapers.indiamart import IndiaMartScraper
from ..scrapers.justdial import JustDialScraper
from ..scrapers.mca import MCAScraper
from ..scrapers.opencorporates import OpenCorporatesScraper
from ..scrapers.startpage import StartpageScraper
from ..scrapers.sulekha import SulekhaScraper
from ..scrapers.tradeindia import TradeIndiaScraper
from ..scrapers.website_crawler import WebsiteCrawler
from ..scrapers.yelp import YelpScraper
from ..scrapers.yelp_fusion import YelpFusionScraper
from ..scrapers.yellowpages import YellowPagesScraper
from ..scrapers.zaubacorp import ZaubaCorpScraper
from ..services.csv_exporter import write_leads_csv
from ..services.gemini_engine import gemini_engine
from ..services.nim_engine import nim_engine
from ..utils.http_client import HttpClient

logger = logging.getLogger("spresy.pipeline")

# ---- Tier 1: Official APIs (reliable & legal; run first) ----
TIER1_SOURCES = {
    "google_places": GooglePlacesScraper,
    "yelp_fusion": YelpFusionScraper,
    "opencorporates": OpenCorporatesScraper,
    "hunter": HunterScraper,
    "mca": MCAScraper,
}

# ---- Tier 2: Scraping (coverage gaps; India-first) ----
TIER2_SOURCES = {
    "duckduckgo": DuckDuckGoScraper,
    "bing": BingScraper,
    "startpage": StartpageScraper,
    "google_maps": GoogleMapsScraper,
    "bbb": BBBScraper,
    "yelp": YelpScraper,
    "yellowpages": YellowPagesScraper,
    "indiamart": IndiaMartScraper,
    "tradeindia": TradeIndiaScraper,
    "justdial": JustDialScraper,
    "sulekha": SulekhaScraper,
    "zaubacorp": ZaubaCorpScraper,
    "website": WebsiteCrawler,
}

# Full registry (used by frontend + validation)
SOURCES = {**TIER1_SOURCES, **TIER2_SOURCES}

# When no explicit sources given, this is the default order used.
DEFAULT_SOURCES = [
    "google_places", "opencorporates", "hunter", "mca",   # Tier 1
    "yelp_fusion", "duckduckgo", "bing", "startpage",     # Tier 1.5 / search
    "indiamart", "tradeindia", "justdial", "sulekha",     # India directories
    "zaubacorp", "bbb", "yelp", "yellowpages", "website", # directories + crawler
]

# On Vercel: skip scrapers that consistently 403/401/404 and waste time
# MCA=403, OpenCorporates=401, Yelp=403, YellowPages=404, ZaubaCorp=403, BBB=US-only, DuckDuckGo=202 blocked
VERCEL_DEFAULT_SOURCES = [
    "yelp_fusion",           # Official API (if key set)
    "bing",                  # Reliable, returns real results
    "startpage",             # Good fallback search
    "indiamart",             # India-first directory
    "tradeindia",            # India B2B directory
    "sulekha",               # India local services
    "justdial",              # India local directory
    "google_places",         # Official API (if key set)
]


MAX_DISCOVERED_SITES = 20  # Reduced from 60 — website crawler too slow on Vercel

# Domains that are never a business lead — filter before crawling
IRRELEVANT_DOMAINS = {
    "bestbuy.com", "amazon.com", "walmart.com", "britannica.com",
    "merriam-webster.com", "dictionary.com", "wikihow.com",
    "independent.co.uk", "independent.ie", "the-independent.com",
    "bbc.com", "bbc.co.uk", "reuters.com", "bloomberg.com",
    "ndtv.com", "hindustantimes.com", "timesofindia.com", "economictimes.com",
    "quora.com", "reddit.com", "medium.com", "substack.com",
    "github.com", "stackoverflow.com", "npmjs.com",
    "apkpure.com", "apk.support", "play.google.com",
}
# Domains that are directories/search wrappers, not the business itself.
# They're handled by dedicated scrapers; crawling them just wastes requests.
WRAPPER_DOMAINS = {
    "yelp.com", "www.yelp.com", "yellowpages.com", "www.yellowpages.com",
    "bbb.org", "www.bbb.org", "cylex.us.com", "www.cylex.us.com",
    "manta.com", "www.manta.com", "dexknows.com", "www.dexknows.com",
    "duckduckgo.com", "bing.com", "www.bing.com", "startpage.com", "www.startpage.com",
    "google.com", "www.google.com", "googlemaps.com", "www.googlemaps.com",
    "indiamart.com", "www.indiamart.com", "dir.indiamart.com",
    "tradeindia.com", "www.tradeindia.com",
    "justdial.com", "www.justdial.com",
    "sulekha.com", "www.sulekha.com",
    "zaubacorp.com", "www.zaubacorp.com",
    "mca.gov.in", "www.mca.gov.in",
    "facebook.com", "www.facebook.com", "linkedin.com", "www.linkedin.com",
    "instagram.com", "www.instagram.com", "twitter.com", "x.com",
    "gstatic.com", "w3.org", "schema.org", "googleusercontent.com",
    "youtube.com", "www.youtube.com", "play.google.com", "microsoft.com", "support.microsoft.com",
    "techcommunity.microsoft.com", "aliyun.com", "www.aliyun.com", "cn.aliyun.com",
    "en.wikipedia.org", "wikipedia.org", "tripadvisor.com", "tripadvisor.in"
}


class ScrapePipeline:
    """Orchestrates a full scrape: queries -> Tier1 APIs -> Tier2 scraping -> enrichment -> CSV."""

    def __init__(self, job: JobInfo, progress_cb=None):
        self.job = job
        self.progress_cb = progress_cb
        self.req: ScrapeRequest = job.request

    def _update(self, stage: str, message: str, leads: int = 0, total: int = 0):
        percent = int((leads / total) * 100) if total else 0
        self.job.progress = JobProgress(stage=stage, message=message, leads_found=leads, total=total, percent=min(percent, 99))
        if self.progress_cb:
            self.progress_cb(self.job)

    def _active_sources(self):
        """Resolve requested sources to engine classes (default = DEFAULT_SOURCES order)."""
        import os
        if self.req.sources:
            return [SOURCES[s] for s in self.req.sources if s in SOURCES]
        # On Vercel, use a trimmed source list — skip scrapers that always 403/401/404
        if os.environ.get("VERCEL"):
            return [SOURCES[s] for s in VERCEL_DEFAULT_SOURCES if s in SOURCES]
        return [SOURCES[s] for s in DEFAULT_SOURCES]


    async def run(self) -> dict:
        try:
            leads = await self._execute()
            self.job.status = LeadStatus.completed
            self.job.progress.stage = "done"
            self.job.progress.message = "Completed"
            self.job.progress.leads_found = len(leads)
            self.job.progress.total = len(leads)
            self.job.progress.percent = 100
            import os
            output_dir = "/tmp/spresy_output" if os.environ.get("VERCEL") else settings.OUTPUT_DIR
            try:
                csv_path = write_leads_csv(leads, output_dir, self.req.keyword)
            except Exception:
                csv_path = ""  # CSV write failure should not crash the pipeline
            return {
                "leads": [l.model_dump() for l in leads],
                "csv_path": csv_path,
                "stats": {
                    "leads": len(leads),
                    "with_email": sum(1 for l in leads if l.email),
                    "with_phone": sum(1 for l in leads if l.phone),
                    "with_website": sum(1 for l in leads if l.website),
                    "verified": sum(1 for l in leads if l.verified),
                },
            }
        except Exception as e:
            logger.exception("Pipeline failed")
            self.job.status = LeadStatus.failed
            self.job.error = str(e)
            raise

    async def _execute(self) -> List[Lead]:
        req = self.req
        self._update("prepare", "Generating search queries with AI...")
        queries = await gemini_engine.generate_queries(req.keyword, req.location)

        lead_results: List[Lead] = []
        visited_sites: Set[str] = set()

        async with HttpClient() as client:
            engines = [cls(client, req.location) for cls in self._active_sources()]

            async def _run_search(engine, query=None):
                q = query or req.keyword
                try:
                    return await engine.search(q, settings.RESULTS_PER_SOURCE)
                except Exception as e:
                    logger.warning("%s failed on %r: %s", engine.name, q, e)
                    return []

            # ---- Phase 1: Tier 1 official APIs (most reliable) ----
            tier1_engines = [e for e in engines if getattr(e, "tier", 2) == 1 and not getattr(e, "is_enricher", False)]
            hunter = next((e for e in engines if getattr(e, "is_enricher", False)), None)
            tier1_tasks = []
            for engine in tier1_engines:
                for q in queries[:3]:
                    tier1_tasks.append(_run_search(engine, q))
            if tier1_tasks:
                self._update("tier1", f"Querying official APIs ({len(tier1_engines)} sources)...")
                batches = await asyncio.gather(*tier1_tasks)
                for batch in batches:
                    for item in batch:
                        lead_results.append(self._lead_from(item))

            self._update("tier1", f"Tier 1 APIs returned {len(lead_results)} leads", len(lead_results), req.max_leads * 4)

            # ---- Phase 2: Tier 2 search engines (discover business sites) ----
            search_engines = [e for e in engines if not e.yields_leads]
            directory_engines = [e for e in engines if e.yields_leads and getattr(e, "tier", 2) == 2 and e.name != "website"]
            crawler = next((e for e in engines if e.name == "website"), None)

            all_discovered: List[dict] = []
            search_tasks = []
            for engine in search_engines:
                for q in queries[:3]:  # Reduced from 6
                    search_tasks.append(_run_search(engine, q))
            if search_tasks:
                search_batches = await asyncio.gather(*search_tasks)
                for batch in search_batches:
                    for item in batch:
                        url = item.get("website") or item.get("url")
                        if not url:
                            continue
                        domain = urlparse(url).netloc.lower().replace("www.", "")
                        if domain in WRAPPER_DOMAINS or domain in IRRELEVANT_DOMAINS:
                            continue
                        if url not in visited_sites:
                            visited_sites.add(url)
                            all_discovered.append(item)
            self._update("discover", f"Discovered {len(all_discovered)} candidate websites", len(lead_results), req.max_leads * 4)

            # ---- Phase 3: Tier 2 directory sources (India-first) ----
            dir_tasks = []
            for engine in directory_engines:
                for q in queries[:2]:  # Reduced from 4 — faster, less redundancy
                    dir_tasks.append(_run_search(engine, q))
            if dir_tasks:
                dir_batches = await asyncio.gather(*dir_tasks)
                for batch in dir_batches:
                    for item in batch:
                        lead = self._lead_from(item)
                        lead_results.append(lead)
                        # Write to DB immediately so polling shows partial results
                        from .job_manager import job_manager
                        job_manager.add_lead(self.job.id, lead)
                        if len(lead_results) >= req.max_leads * 2:
                            break  # Early exit
                    if len(lead_results) >= req.max_leads * 2:
                        break
            self._update("directories", f"Directory sources returned {len(lead_results)} total leads", len(lead_results), req.max_leads * 4)

            # ---- Phase 4: crawl discovered business websites ----
            # Skip on Vercel (VERCEL=1) — website crawler is too slow for serverless
            import os
            site_leads: List[Lead] = []
            if crawler and all_discovered and not os.environ.get("VERCEL"):
                sites = all_discovered[:MAX_DISCOVERED_SITES]
                self._update("crawl", f"Crawling {len(sites)} websites for contact info...", len(site_leads), len(sites))
                crawl_tasks = [(item.get("website") or item.get("url"), item.get("name", "")) for item in sites]
                site_leads.extend(await self._crawl_batch(crawler, crawl_tasks, len(sites)))

            # ---- Phase 5: Hunter.io email enrichment for leads missing emails ----
            if hunter and hunter.is_enricher:
                self._update("enrich", "Enriching leads with Hunter.io emails...", len(lead_results), req.max_leads * 4)
                await self._enrich_emails(hunter, site_leads + lead_results)

            # ---- Phase 6: combine, dedupe, score, cut ----
            combined = self._dedupe(lead_results + site_leads)
            self._update("score", f"Scoring {len(combined)} unique leads with AI...", len(combined), req.max_leads * 4)
            
            # Since Vercel can timeout, we write leads incrementally as they are scored
            from .job_manager import job_manager
            
            final_leads = []
            
            if req.use_ai:
                full_query = req.keyword
                if req.location:
                    full_query += f" in {req.location}"
                    
                # We do this semi-sequentially or in small batches to write to DB
                sem = asyncio.Semaphore(3)
                async def _score_and_save(lead: Lead):
                    async with sem:
                        if lead.email or lead.phone or lead.website:
                            try:
                                ai_score = await gemini_engine.qualify_lead(lead.name, lead.description or "", full_query)
                                lead.ai_score = ai_score.get("score", 50)
                                lead.ai_summary = ai_score.get("summary", "")
                                lead.category = lead.category or ai_score.get("category", "")
                            except Exception:
                                lead.ai_score = 50.0
                            if nim_engine.available:
                                try:
                                    cls = await nim_engine.classify_lead(lead.name, lead.description or "")
                                    lead.category = lead.category or cls.get("category", "")
                                except Exception:
                                    pass
                        else:
                            lead.ai_score = 0.0
                        
                        if lead.ai_score is None or lead.ai_score >= 30:
                            job_manager.add_lead(self.job.id, lead)
                            final_leads.append(lead)

                await asyncio.gather(*[_score_and_save(l) for l in combined])
            else:
                for lead in combined:
                    job_manager.add_lead(self.job.id, lead)
                    final_leads.append(lead)

            self._update("finalize", f"Finalizing {len(final_leads)} leads", len(final_leads), req.max_leads)
            return final_leads

    @staticmethod
    def _lead_from(item: dict) -> Lead:
        return Lead(**{k: v for k, v in item.items() if k in Lead.model_fields})

    async def _crawl_batch(self, crawler: WebsiteCrawler, sites: List[tuple], total: int) -> List[Lead]:
        sem = asyncio.Semaphore(settings.MAX_CONCURRENCY)

        async def _one(item):
            url, name = item
            async with sem:
                try:
                    info = await crawler.crawl_site(url, lead_name=name)
                    if info:
                        return crawler.to_lead(info, "website", url)
                except Exception as e:
                    logger.debug("crawl failed %s: %s", url, e)
                return None

        leads: List[Lead] = []
        done = 0
        for chunk in _chunks(sites, 5):
            results = await asyncio.gather(*[_one(item) for item in chunk])
            for r in results:
                if r:
                    leads.append(r)
            done += len(chunk)
            self._update("crawl", f"Crawling websites... {done}/{total}", len(leads), total)
        return leads

    async def _enrich_emails(self, hunter: HunterScraper, leads: List[Lead]):
        """Fill missing emails using Hunter.io domain search, batched & rate-limited."""
        sem = asyncio.Semaphore(4)

        async def _one(lead: Lead):
            if lead.email or not lead.website:
                return
            domain = urlparse(lead.website).netloc.replace("www.", "").lower()
            if not domain or "." not in domain or domain in WRAPPER_DOMAINS:
                return
            async with sem:
                try:
                    email = await hunter.find_emails_for_domain(domain)
                    if email:
                        lead.email = email
                except Exception:
                    pass

        await asyncio.gather(*[_one(l) for l in leads if not l.email and l.website])

    async def _score_batch(self, leads: List[Lead], keyword: str) -> List[Lead]:
        """Score leads with Groq (relevance) and NIM (category). Batch, non-blocking."""
        sem = asyncio.Semaphore(3)

        async def _score(lead: Lead):
            async with sem:
                if lead.email or lead.phone or lead.website:
                    try:
                        ai_score = await gemini_engine.qualify_lead(lead.name, lead.description or "", keyword)
                        lead.ai_score = ai_score.get("score", 50)
                        lead.ai_summary = ai_score.get("summary", "")
                        lead.category = lead.category or ai_score.get("category", "")
                    except Exception:
                        lead.ai_score = 50.0
                    if nim_engine.available:
                        try:
                            cls = await nim_engine.classify_lead(lead.name, lead.description or "")
                            lead.category = lead.category or cls.get("category", "")
                        except Exception:
                            pass
                else:
                    lead.ai_score = 0.0
                return lead

        await asyncio.gather(*[_score(l) for l in leads])
        return leads

    @staticmethod
    def _dedupe(leads: List[Lead]) -> List[Lead]:
        seen: dict = {}
        for lead in leads:
            key = None
            if lead.website:
                domain = urlparse(lead.website).netloc.replace("www.", "").lower()
                # Directory-listing URLs aren't unique per business; use name instead
                if domain in WRAPPER_DOMAINS:
                    key = "name:" + (lead.name or "").lower().strip()
                else:
                    key = "domain:" + domain
            if key is None and lead.name:
                key = "name:" + lead.name.lower().strip()
            elif key is None and lead.email:
                key = "email:" + lead.email.lower()

            if not key:
                continue

            if key not in seen:
                seen[key] = lead
            else:
                existing = seen[key]
                # Merge contact info if the other copy has something we lack
                if lead.email and not existing.email:
                    existing.email = lead.email
                if lead.phone and not existing.phone:
                    existing.phone = lead.phone
                if not existing.website and lead.website:
                    existing.website = lead.website
                if not existing.address and lead.address:
                    existing.address = lead.address
                if lead.verified and not existing.verified:
                    existing.verified = True
        return list(seen.values())


def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
