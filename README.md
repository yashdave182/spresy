# Spresy — AI Lead Scraper

A legal, AI-powered lead generation scraper. Type a keyword or sentence and a location, and it
finds real businesses/contacts across multiple public sources, extracts emails & phone numbers,
scores relevance with **Groq Cloud** and **NVIDIA NIM**, and exports everything to CSV.

## Features

- **Simple frontend** — one form: keyword + location + max leads → CSV download
- **Tier 1 · Official APIs (reliable & legal, run first)**
  - **Google Places API** — business name, address, phone, website, rating
  - **Yelp Fusion API** — similar data (free tier)
  - **OpenCorporates** — company registry search (India `in` jurisdiction by default)
  - **Hunter.io** — verified business email finder (also used to enrich leads missing emails)
  - **MCA India** — company registry (CIN, registered office, public)
- **Tier 2 · Scraping (coverage gaps, India-first)**
  - Search engines: DuckDuckGo, Bing, Startpage, Google Maps (via SerpAPI)
  - India directories: **IndiaMART, TradeIndia, JustDial, Sulekha, Zauba Corp**
  - Directories: Yelp, YellowPages, BBB
  - **Website Crawler** — visits each discovered site's `/contact`, `/about`, `/team` pages, extracts `mailto:` / `tel:` links and body text
- **AI engines**
  - **Groq Cloud** — expands your keyword into many search queries, scores lead relevance 0–100
  - **NVIDIA NIM** — embeddings + LLM classification for categorizing & de-duplicating leads
- **Legal scraping** — respects `robots.txt`, polite rate limits with jitter, clear User-Agent, only public data
- **CSV export** — UTF-8 with BOM (Excel-friendly), sanitized fields

## Quick Start

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example .env   # then edit .env and add your API keys
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 — the API serves the frontend from `../frontend`.

> The frontend is a static page. Serve it from the backend root or open `frontend/index.html`.
> If you host it separately, set `API_BASE` in `frontend/app.js`.

## API

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/api/scrape` | Start a scrape job `{keyword, location, max_leads, use_ai, sources}` |
| GET | `/api/jobs/{id}` | Poll progress |
| GET | `/api/jobs/{id}/result` | Get final leads + stats |
| GET | `/api/jobs/{id}/csv` | Download the CSV export |

### Example

```bash
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"keyword":"real estate agents","location":"Austin, TX","max_leads":40,"use_ai":true}'
```

## API Keys

| Key | Service | Tier | Used for |
| --- | ------- | ---- | -------- |
| `GOOGLE_PLACES_API_KEY` | https://console.cloud.google.com (Places API) | 1 | Business name/address/phone/website/rating |
| `YELP_FUSION_API_KEY` | https://www.yelp.com/developers | 1 | Business search API |
| `OPENCORPORATES_API_KEY` | https://opencorporates.com/api | 1 | Company registry (optional, free tier works) |
| `HUNTER_API_KEY` | https://hunter.io | 1 | Verified email finder + enrichment |
| `GROQ_API_KEY` | https://console.groq.com | AI | Query expansion, lead scoring, extraction |
| `NIM_API_KEY` | https://build.nvidia.com | AI | Embeddings, classification |
| `SERPAPI_KEY` | https://serpapi.com | 2 | Google Maps local results (optional) |

**India-first:** By default OpenCorporates uses the `in` jurisdiction and the MCA + Zauba Corp
sources query Indian company registries. IndiaMART, TradeIndia, JustDial, and Sulekha cover
Indian B2B and local-service leads. Leave `sources` empty in the request to use the full
Tier 1 → Tier 2 order; the app works without keys using rule-based fallbacks.

## Legal & Ethical Scraping

- Respects `robots.txt` per-domain (cached), skips disallowed pages
- Polite delays with jitter between requests; bounded concurrency
- Identifiable, honest User-Agent
- Only collects **publicly available** contact info
- **Use responsibly:** respect site terms, don't spam, comply with local privacy laws (GDPR/CCPA/CAN-SPAM). This tool is for lead research, not bulk unsolicited mail.

## CSV Columns

`name, website, email, phone, address, city, state, country, category, description, source, ai_score, ai_summary, rating, verified, cin`

## Project Layout

```
backend/
  app/
    main.py                 # FastAPI app + endpoints
    config.py               # env settings
    models.py               # Pydantic schemas
    scrapers/               # one adapter per source + website crawler
      google_places.py      # Tier 1: Google Places API
      yelp_fusion.py        # Tier 1: Yelp Fusion API
      opencorporates.py     # Tier 1: company registry (in jurisdiction default)
      hunter.py             # Tier 1: Hunter.io email finder + enrichment
      mca.py                # Tier 1: India MCA company registry
      indiamart.py          # Tier 2: IndiaMART (India B2B)
      tradeindia.py         # Tier 2: TradeIndia (India B2B)
      justdial.py           # Tier 2: JustDial (needs Playwright)
      sulekha.py            # Tier 2: Sulekha (needs Playwright)
      zaubacorp.py          # Tier 2: Zauba Corp (India companies)
      bing.py / duckduckgo.py / startpage.py   # search engines
      google_maps.py / bbb.py / yelp.py / yellowpages.py
      website_crawler.py    # crawls /contact /about /team, extracts mailto/tel + text
    services/
      pipeline.py           # Tier1 → Tier2 → enrichment → scoring → export
      groq_engine.py        # Groq Cloud integration
      nim_engine.py         # NVIDIA NIM integration
      csv_exporter.py       # CSV writing
      job_manager.py        # background jobs
    utils/
      contact_extractor.py  # email/phone regex engine
      robots.py             # robots.txt compliance
      http_client.py        # rate-limited async HTTP
      playwright_fetcher.py # optional headless Chromium for anti-bot sources
frontend/
  index.html, style.css, app.js   # simple UI
.env.example
```
