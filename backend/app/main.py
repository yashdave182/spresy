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

# Ensure tables exist on all DB types (handles Vercel PostgreSQL and SQLite fallback)
# checkfirst=True makes this a no-op if tables already exist
try:
    Base.metadata.create_all(bind=engine, checkfirst=True)
except Exception as _db_init_err:
    logging.getLogger("spresy").warning(f"DB table init warning: {_db_init_err}")

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

    # Re-ensure tables exist (safe no-op if already present)
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception:
        pass

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
# Outreach system routes
# ---------------------------------------------------------------------------

from fastapi import UploadFile, File, Form
from typing import List as TList, Optional as TOpt
import uuid, os, datetime


# --- SMTP Credentials ---

@app.post("/api/smtp")
async def save_smtp(
    email: str = Form(...),
    smtp_host: str = Form(...),
    smtp_port: int = Form(587),
    password: str = Form(...),
    sender_name: str = Form(""),
    daily_limit: int = Form(25),
):
    from .db_models import SmtpCredentialRecord
    from .services.email_sender import encrypt_password
    from .database import SessionLocal
    db = SessionLocal()
    try:
        rec = SmtpCredentialRecord(
            user_id="default",
            email=email.strip().lower(),
            smtp_host=smtp_host.strip(),
            smtp_port=smtp_port,
            encrypted_password=encrypt_password(password),
            sender_name=sender_name.strip(),
            daily_limit=daily_limit,
        )
        db.add(rec)
        db.commit()
        return {"id": rec.id, "email": rec.email, "smtp_host": rec.smtp_host}
    finally:
        db.close()


@app.get("/api/smtp")
async def list_smtp():
    from .db_models import SmtpCredentialRecord
    from .database import SessionLocal
    db = SessionLocal()
    try:
        recs = db.query(SmtpCredentialRecord).filter(SmtpCredentialRecord.user_id == "default").all()
        return [{"id": r.id, "email": r.email, "smtp_host": r.smtp_host, "daily_limit": r.daily_limit} for r in recs]
    finally:
        db.close()


@app.delete("/api/smtp/{cred_id}")
async def delete_smtp(cred_id: str):
    from .db_models import SmtpCredentialRecord
    from .database import SessionLocal
    db = SessionLocal()
    try:
        rec = db.query(SmtpCredentialRecord).filter(SmtpCredentialRecord.id == cred_id).first()
        if not rec:
            raise HTTPException(404, "Credential not found")
        db.delete(rec)
        db.commit()
        return {"deleted": True}
    finally:
        db.close()


# --- Document Upload ---

@app.post("/api/upload")
async def upload_doc(file: UploadFile = File(...)):
    from .services.doc_parser import extract_text
    import aiofiles

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex
    ext = Path(file.filename or "file").suffix or ".bin"
    save_path = upload_dir / f"{file_id}{ext}"

    async with aiofiles.open(save_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    text = await extract_text(str(save_path), file.filename or "")
    return {
        "file_id": file_id,
        "filename": file.filename,
        "file_path": str(save_path),
        "extracted_text_preview": text[:500],
        "char_count": len(text),
    }


# --- Campaigns ---

@app.post("/api/campaigns")
async def create_campaign(
    job_id: str = Form(...),
    prompt: str = Form(...),
    smtp_credential_id: str = Form(""),
    sender_name: str = Form(""),
    physical_address: str = Form(""),
    email_subject_template: str = Form(""),
    batch_size: int = Form(5),
    doc_file_paths: str = Form(""),   # comma-separated file_paths from /api/upload
    doc_filenames: str = Form(""),    # comma-separated original filenames
):
    from .db_models import CampaignRecord, UserDocRecord
    from .database import SessionLocal
    from .services.doc_parser import extract_text
    db = SessionLocal()
    try:
        campaign = CampaignRecord(
            user_id="default",
            job_id=job_id,
            smtp_credential_id=smtp_credential_id or None,
            prompt=prompt,
            email_subject_template=email_subject_template or None,
            sender_name=sender_name or None,
            physical_address=physical_address or None,
            batch_size=batch_size,
            status="draft",
        )
        db.add(campaign)
        db.flush()

        # Attach uploaded documents
        paths = [p.strip() for p in doc_file_paths.split(",") if p.strip()]
        names = [n.strip() for n in doc_filenames.split(",") if n.strip()]
        for i, path in enumerate(paths):
            filename = names[i] if i < len(names) else Path(path).name
            text = await extract_text(path, filename)
            doc = UserDocRecord(
                campaign_id=campaign.id,
                filename=filename,
                file_path=path,
                content_text=text,
            )
            db.add(doc)

        db.commit()
        return {"id": campaign.id, "status": campaign.status, "job_id": campaign.job_id}
    finally:
        db.close()


@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    from .db_models import CampaignRecord
    from .database import SessionLocal
    from .services.outreach_engine import get_campaign_stats
    db = SessionLocal()
    try:
        c = db.query(CampaignRecord).filter(CampaignRecord.id == campaign_id).first()
        if not c:
            raise HTTPException(404, "Campaign not found")
        stats = get_campaign_stats(campaign_id)
        return {
            "id": c.id, "job_id": c.job_id, "status": c.status,
            "prompt": c.prompt, "sender_name": c.sender_name,
            "batch_size": c.batch_size, "created_at": c.created_at,
            "stats": stats,
        }
    finally:
        db.close()


# --- Message Generation (fire-and-poll) ---

@app.post("/api/campaigns/{campaign_id}/generate")
async def start_generation(campaign_id: str):
    import asyncio
    from .services.outreach_engine import generate_messages
    from .db_models import CampaignRecord
    from .database import SessionLocal
    db = SessionLocal()
    try:
        c = db.query(CampaignRecord).filter(CampaignRecord.id == campaign_id).first()
        if not c:
            raise HTTPException(404, "Campaign not found")
        if c.status not in ("draft", "failed"):
            raise HTTPException(400, f"Cannot generate from status '{c.status}'")
    finally:
        db.close()

    asyncio.create_task(generate_messages(campaign_id))
    return {"status": "generating", "message": "Generation started. Poll GET /api/campaigns/{id} for status."}


# --- Review & Approve ---

@app.get("/api/campaigns/{campaign_id}/messages")
async def list_messages(campaign_id: str):
    from .db_models import OutreachRecord, LeadRecord
    from .database import SessionLocal
    db = SessionLocal()
    try:
        records = db.query(OutreachRecord).filter(OutreachRecord.campaign_id == campaign_id).all()
        result = []
        for r in records:
            lead = db.query(LeadRecord).filter(LeadRecord.id == r.lead_id).first()
            result.append({
                "id": r.id,
                "lead_name": lead.name if lead else "",
                "to_email": r.to_email,
                "subject": r.generated_subject,
                "message": r.generated_message,
                "status": r.status,
                "skip_reason": r.skip_reason,
                "user_edited": r.user_edited,
                "sent_at": r.sent_at,
                "error": r.error,
            })
        return result
    finally:
        db.close()


@app.put("/api/outreach/{outreach_id}")
async def edit_message(outreach_id: str, subject: str = Form(None), message: str = Form(None)):
    from .db_models import OutreachRecord
    from .database import SessionLocal
    db = SessionLocal()
    try:
        rec = db.query(OutreachRecord).filter(OutreachRecord.id == outreach_id).first()
        if not rec:
            raise HTTPException(404, "Outreach record not found")
        if rec.status not in ("generated", "approved", "failed"):
            raise HTTPException(400, f"Cannot edit message with status '{rec.status}'")
        if subject is not None:
            rec.generated_subject = subject
        if message is not None:
            rec.generated_message = message
        rec.user_edited = True
        db.commit()
        return {"id": rec.id, "status": rec.status, "user_edited": True}
    finally:
        db.close()


@app.post("/api/outreach/{outreach_id}/approve")
async def approve_message(outreach_id: str):
    from .db_models import OutreachRecord
    from .database import SessionLocal
    db = SessionLocal()
    try:
        rec = db.query(OutreachRecord).filter(OutreachRecord.id == outreach_id).first()
        if not rec:
            raise HTTPException(404, "Outreach record not found")
        if rec.status != "generated":
            raise HTTPException(400, f"Can only approve messages with status 'generated', got '{rec.status}'")
        rec.status = "approved"
        db.commit()
        return {"id": rec.id, "status": "approved"}
    finally:
        db.close()


@app.post("/api/campaigns/{campaign_id}/approve-all")
async def approve_all_messages(campaign_id: str):
    from .db_models import OutreachRecord, CampaignRecord
    from .database import SessionLocal
    db = SessionLocal()
    try:
        count = db.query(OutreachRecord).filter(
            OutreachRecord.campaign_id == campaign_id,
            OutreachRecord.status == "generated",
        ).update({"status": "approved"}, synchronize_session=False)
        campaign = db.query(CampaignRecord).filter(CampaignRecord.id == campaign_id).first()
        if campaign:
            campaign.status = "running"
        db.commit()
        return {"approved": count, "campaign_status": "running"}
    finally:
        db.close()


# --- Sending ---

@app.post("/api/campaigns/{campaign_id}/send-batch")
async def send_batch(campaign_id: str):
    from .db_models import CampaignRecord
    from .database import SessionLocal
    from .services.outreach_engine import process_batch
    db = SessionLocal()
    try:
        c = db.query(CampaignRecord).filter(CampaignRecord.id == campaign_id).first()
        if not c:
            raise HTTPException(404, "Campaign not found")
        if c.status not in ("running", "paused"):
            raise HTTPException(400, f"Campaign status is '{c.status}', must be running or paused to send")
        if c.status == "paused":
            c.status = "running"
            db.commit()
        batch_size = c.batch_size
    finally:
        db.close()

    result = await process_batch(campaign_id, batch_size=batch_size)
    return result


@app.post("/api/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    from .db_models import CampaignRecord
    from .database import SessionLocal
    db = SessionLocal()
    try:
        c = db.query(CampaignRecord).filter(CampaignRecord.id == campaign_id).first()
        if not c:
            raise HTTPException(404, "Campaign not found")
        c.status = "paused"
        db.commit()
        return {"status": "paused"}
    finally:
        db.close()


# --- Unsubscribe & Suppression (CAN-SPAM) ---

@app.get("/api/unsubscribe/{outreach_id}")
async def unsubscribe(outreach_id: str):
    from .db_models import OutreachRecord
    from .database import SessionLocal
    from .services.email_validator import add_to_suppression
    db = SessionLocal()
    try:
        rec = db.query(OutreachRecord).filter(OutreachRecord.id == outreach_id).first()
        if not rec or not rec.to_email:
            return HTMLResponse("<h2>Unsubscribe link invalid or expired.</h2>")
        add_to_suppression(rec.to_email, "unsubscribed")
        return HTMLResponse(f"""
        <html><body style="font-family:sans-serif;padding:40px;max-width:500px;margin:auto">
        <h2>You have been unsubscribed</h2>
        <p><strong>{rec.to_email}</strong> has been removed from future outreach.</p>
        </body></html>
        """)
    finally:
        db.close()


@app.get("/api/suppressions")
async def list_suppressions():
    from .db_models import SuppressionRecord
    from .database import SessionLocal
    db = SessionLocal()
    try:
        recs = db.query(SuppressionRecord).filter(SuppressionRecord.user_id == "default").all()
        return [{"id": r.id, "email": r.email, "reason": r.reason, "created_at": r.created_at} for r in recs]
    finally:
        db.close()


@app.post("/api/suppressions")
async def add_suppression(email: str = Form(...), reason: str = Form("manual")):
    from .services.email_validator import add_to_suppression
    added = add_to_suppression(email.strip().lower(), reason)
    return {"added": added, "email": email.strip().lower()}




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

