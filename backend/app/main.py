import logging
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models import JobInfo, JobResult, ScrapeRequest
from .services.job_manager import job_manager

from .database import engine, Base
from . import db_models

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Ensure tables exist (handles Vercel cold-starts where /tmp is wiped)
if settings.DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Spresy Lead Scraper API",
    description="AI-powered legal lead scraping from multiple public sources (Groq + NVIDIA NIM).",
    version="1.0.0",
)

# CORS: allow the deployed frontend origin in production, wildcard for local dev
_allowed_origins = ["*"]
if settings.FRONTEND_URL:
    _allowed_origins = [
        settings.FRONTEND_URL,
        "http://localhost:5173",   # local Vite dev
        "http://localhost:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global error handler — always includes CORS headers so browser can read body
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin", "*")
    tb = traceback.format_exc()
    logging.getLogger("spresy").error(f"Unhandled error: {exc}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "detail": tb},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        },
    )


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/info")
def root():
    return {
        "name": "Spresy Lead Scraper",
        "endpoints": [
            "POST /api/scrape - start a scrape job",
            "GET /api/jobs/{id} - poll job status/progress",
            "GET /api/jobs/{id}/result - get final leads",
            "GET /api/jobs/{id}/csv - download CSV export",
        ],
        "groq_available": bool(settings.GROQ_API_KEY),
        "nim_available": bool(settings.NIM_API_KEY),
        "serpapi_available": bool(settings.SERPAPI_KEY),
    }


@app.post("/api/scrape", response_model=JobInfo)
async def start_scrape(req: ScrapeRequest):
    import asyncio

    # Re-ensure tables exist on every cold start (Vercel wipes /tmp between invocations)
    if settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)

    job = job_manager.create(req)
    job_manager.mark_status(job.id, "running")

    async def _run_pipeline(job_id: str):
        from .services.pipeline import ScrapePipeline
        _job = job_manager.get(job_id)
        pipeline = ScrapePipeline(_job)
        try:
            await pipeline.run()
            job_manager.mark_done(job_id)
        except Exception as e:
            logging.getLogger("spresy").error(f"Scrape failed: {e}")
            job_manager.mark_error(job_id, str(e))

    # Fire and forget — client polls /api/jobs/{id}/result
    asyncio.create_task(_run_pipeline(job.id))
    return job_manager.get(job.id)

@app.get("/api/jobs/{job_id}", response_model=JobInfo)
async def get_job(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs/{job_id}/result", response_model=JobResult)
async def get_result(job_id: str):
    result = job_manager.get_result(job_id)
    if not result:
        job = job_manager.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        # Build a partial result so polling can see progress
        return JobResult(**job.model_dump(), leads=[], stats={})
    return result


@app.get("/api/jobs/{job_id}/csv")
async def download_csv(job_id: str):
    result = job_manager.get_result(job_id)
    if not result or not result.csv_path:
        raise HTTPException(status_code=404, detail="CSV not ready yet")
    path = Path(result.csv_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="CSV file missing")
    return FileResponse(
        path,
        media_type="text/csv",
        filename=path.name,
    )


# ---------------------------------------------------------------------------
# Docker mode: serve the built frontend from /app/frontend/dist
# Activated when SERVE_FRONTEND=true (set in the Dockerfile).
# In Vercel mode this is ignored — frontend is a separate project.
# ---------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if settings.SERVE_FRONTEND and _FRONTEND_DIST.is_dir():
    logging.getLogger("spresy").info(f"Serving frontend from {_FRONTEND_DIST}")

    # Mount static assets (JS, CSS, images) under /assets
    _assets_dir = _FRONTEND_DIST / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="frontend-assets")

    # Serve other static files (favicon, icons, etc.) directly
    @app.get("/favicon.svg")
    async def favicon():
        fav = _FRONTEND_DIST / "favicon.svg"
        if fav.exists():
            return FileResponse(str(fav), media_type="image/svg+xml")
        raise HTTPException(404)

    @app.get("/icons.svg")
    async def icons():
        ico = _FRONTEND_DIST / "icons.svg"
        if ico.exists():
            return FileResponse(str(ico), media_type="image/svg+xml")
        raise HTTPException(404)

    # SPA fallback: serve index.html for all non-API, non-asset routes
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # If there is a matching file in dist/, serve it
        file_path = _FRONTEND_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        # Otherwise serve index.html (SPA client-side routing)
        return HTMLResponse((_FRONTEND_DIST / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=9000, reload=True)

