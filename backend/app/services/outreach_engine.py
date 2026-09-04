"""
outreach_engine.py — AI-powered outreach orchestrator.

Two operations:
  1. generate_messages(campaign_id)   — background task, fire-and-poll
  2. process_batch(campaign_id)       — short-lived, atomic claim, safe to call repeatedly

Status machine for OutreachRecord:
  pending → generated → approved → claimed → sent
  pending → skipped   (no email / invalid / suppressed)
  claimed → failed    (transient error — retryable, NOT suppressed)
  claimed → bounced   (SMTP 5xx — auto-added to SuppressionRecord)
"""
import asyncio
import logging
import datetime
from typing import Optional

logger = logging.getLogger("spresy.outreach")

FRONTEND_BASE = ""   # Set to your domain for production unsubscribe URLs


def _get_frontend_base() -> str:
    from ..config import settings
    return settings.FRONTEND_URL or "https://spresy.onrender.com"


# ---------------------------------------------------------------------------
# Message generation (fire-and-poll)
# ---------------------------------------------------------------------------

async def generate_messages(campaign_id: str) -> None:
    """
    Background task kicked off by POST /api/campaigns/{id}/generate.
    Sets campaign.status = "generating" → "review" when done.
    Frontend polls GET /api/campaigns/{id} to see progress.
    """
    from ..database import SessionLocal
    from ..db_models import CampaignRecord, UserDocRecord, OutreachRecord, LeadRecord
    from ..services.gemini_engine import gemini_engine
    from ..services.email_validator import validate as validate_email

    db = SessionLocal()
    try:
        campaign = db.query(CampaignRecord).filter(CampaignRecord.id == campaign_id).first()
        if not campaign:
            logger.error("Campaign %s not found", campaign_id)
            return

        campaign.status = "generating"
        db.commit()

        # Load document context
        docs = db.query(UserDocRecord).filter(UserDocRecord.campaign_id == campaign_id).all()
        doc_context = "\n\n---\n\n".join(
            [f"[Document: {d.filename}]\n{d.content_text}" for d in docs if d.content_text]
        )

        # Load all leads from the campaign's job
        leads = db.query(LeadRecord).filter(LeadRecord.job_id == campaign.job_id).all()
        logger.info("Generating messages for %d leads in campaign %s", len(leads), campaign_id)

        for lead in leads:
            # Build outreach record (creates it in pending state)
            rec = OutreachRecord(
                campaign_id=campaign_id,
                lead_id=lead.id,
                to_email=lead.email or None,
            )
            db.add(rec)
            db.flush()  # Get rec.id

            # Step 1: Check email exists
            if not lead.email:
                rec.status = "skipped"
                rec.skip_reason = "no_email"
                db.commit()
                continue

            # Step 2: Validate email (syntax + MX + suppression)
            valid, reason = await validate_email(lead.email, user_id="default")
            if not valid:
                rec.status = "skipped"
                rec.skip_reason = reason
                db.commit()
                continue

            # Step 3: Generate personalized message via AI
            try:
                subject, body = await _generate_one_message(
                    lead=lead,
                    prompt=campaign.prompt,
                    doc_context=doc_context,
                    sender_name=campaign.sender_name or "",
                )
                rec.generated_subject = subject
                rec.generated_message = body
                rec.status = "generated"
            except Exception as e:
                logger.warning("Message generation failed for lead %s: %s", lead.id, e)
                rec.status = "skipped"
                rec.skip_reason = f"generation_error: {e}"

            db.commit()

        campaign.status = "review"
        db.commit()
        logger.info("Campaign %s generation complete — status = review", campaign_id)

    except Exception as e:
        logger.exception("generate_messages failed for campaign %s: %s", campaign_id, e)
        db = SessionLocal()
        campaign = db.query(CampaignRecord).filter(CampaignRecord.id == campaign_id).first()
        if campaign:
            campaign.status = "failed"
            db.commit()
        db.close()
    finally:
        db.close()


async def _generate_one_message(lead, prompt: str, doc_context: str, sender_name: str):
    """Call Gemini to generate a personalized subject + body for one lead."""
    from ..services.gemini_engine import gemini_engine
    from google.genai import types

    lead_info = f"""Company: {lead.name}
Industry: {lead.category or 'Unknown'}
Location: {lead.city or lead.address or 'Unknown'}
Website: {lead.website or 'N/A'}
Description: {lead.description or 'N/A'}"""

    system_prompt = f"""You are an expert cold outreach copywriter. Write a personalized cold email from {sender_name or 'me'} to the business described below.

SENDER CONTEXT (from uploaded documents):
{doc_context or 'No documents provided.'}

USER INSTRUCTIONS:
{prompt}

TARGET BUSINESS:
{lead_info}

RULES:
- Write ONLY the email body (no "Subject:" prefix in the body)
- Be specific to THIS company — reference their name, industry, or location
- Keep it under 200 words
- Sound human, not like a template
- End with a clear, low-friction call-to-action
- Do NOT fabricate specific facts you don't know about the company
- First line: a short, compelling email subject (prefix with "SUBJECT: ")
- Then a blank line
- Then the email body"""

    async def call(client):
        return await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=system_prompt,
            config=types.GenerateContentConfig(temperature=0.7),
        )

    resp = await gemini_engine._execute_with_fallback(call)
    if not resp or not resp.text:
        raise ValueError("Empty response from Gemini")

    # Parse subject from first line
    lines = resp.text.strip().splitlines()
    subject = f"Reaching out — {lead.name}"
    body_start = 0

    for i, line in enumerate(lines):
        if line.upper().startswith("SUBJECT:"):
            subject = line[8:].strip()
            body_start = i + 1
            break

    body = "\n".join(lines[body_start:]).strip()
    return subject, body


# ---------------------------------------------------------------------------
# Batch send (atomic claim)
# ---------------------------------------------------------------------------

async def process_batch(campaign_id: str, batch_size: int = 5) -> dict:
    """
    Process the next batch of approved OutreachRecords.
    Atomically claims rows before processing — safe to call from multiple workers.

    Returns stats: {sent, failed, bounced, remaining, daily_remaining}
    """
    from ..database import SessionLocal
    from ..db_models import (
        CampaignRecord, OutreachRecord, SmtpCredentialRecord, SuppressionRecord
    )
    from ..services.email_sender import (
        send_email, SmtpConfig, _decrypt_password,
        get_daily_sends, increment_daily_sends
    )
    from ..services.email_validator import add_to_suppression

    db = SessionLocal()
    try:
        campaign = db.query(CampaignRecord).filter(CampaignRecord.id == campaign_id).first()
        if not campaign:
            return {"error": "Campaign not found"}

        # Check daily limit
        cred = db.query(SmtpCredentialRecord).filter(
            SmtpCredentialRecord.id == campaign.smtp_credential_id
        ).first()
        if not cred:
            return {"error": "No SMTP credentials configured"}

        sends_today = get_daily_sends(cred.id)
        daily_remaining = cred.daily_limit - sends_today
        if daily_remaining <= 0:
            logger.info("Daily send limit reached for credential %s", cred.id)
            return {"sent": 0, "failed": 0, "bounced": 0, "remaining": _count_remaining(db, campaign_id), "daily_remaining": 0, "limit_reached": True}

        effective_batch = min(batch_size, daily_remaining)

        # ---- ATOMIC CLAIM ----
        # Grab IDs first, then update in one transaction to avoid double-send
        pending_ids = [
            row.id for row in db.query(OutreachRecord.id)
            .filter(
                OutreachRecord.campaign_id == campaign_id,
                OutreachRecord.status == "approved",
            )
            .limit(effective_batch)
            .all()
        ]

        if not pending_ids:
            # Nothing to send — check if campaign is done
            remaining = _count_remaining(db, campaign_id)
            if remaining == 0:
                campaign.status = "completed"
                db.commit()
            return {"sent": 0, "failed": 0, "bounced": 0, "remaining": remaining, "daily_remaining": daily_remaining}

        # Claim them atomically
        db.query(OutreachRecord).filter(
            OutreachRecord.id.in_(pending_ids),
            OutreachRecord.status == "approved",  # Double-check — filter guards against races
        ).update({"status": "claimed"}, synchronize_session=False)
        db.commit()

        # Load claimed records
        records = db.query(OutreachRecord).filter(OutreachRecord.id.in_(pending_ids)).all()

        # Build SMTP config
        smtp_cfg = SmtpConfig(
            host=cred.smtp_host,
            port=cred.smtp_port,
            email=cred.email,
            password=_decrypt_password(cred.encrypted_password),
            sender_name=campaign.sender_name or cred.sender_name or "",
        )

        frontend_base = _get_frontend_base()
        physical_address = campaign.physical_address or "Spresy, India"

        sent = failed = bounced = 0

        for rec in records:
            unsubscribe_url = f"{frontend_base}/api/unsubscribe/{rec.id}"
            success, is_hard_bounce, error_msg = await send_email(
                smtp_cfg=smtp_cfg,
                to_email=rec.to_email,
                subject=rec.generated_subject or f"Reaching out",
                body=rec.generated_message or "",
                physical_address=physical_address,
                unsubscribe_url=unsubscribe_url,
            )

            if success:
                rec.status = "sent"
                rec.sent_at = datetime.datetime.utcnow()
                rec.error = None
                increment_daily_sends(cred.id)
                sent += 1
            elif is_hard_bounce:
                rec.status = "bounced"
                rec.error = error_msg
                # Hard bounce → suppress globally
                add_to_suppression(rec.to_email, "hard_bounce")
                bounced += 1
            else:
                # Transient failure — leave as failed, retryable
                rec.status = "failed"
                rec.error = error_msg
                failed += 1

            db.commit()

        remaining = _count_remaining(db, campaign_id)
        if remaining == 0 and campaign.status == "running":
            campaign.status = "completed"
            db.commit()

        return {
            "sent": sent,
            "failed": failed,
            "bounced": bounced,
            "remaining": remaining,
            "daily_remaining": daily_remaining - sent,
        }

    except Exception as e:
        logger.exception("process_batch failed for campaign %s: %s", campaign_id, e)
        return {"error": str(e)}
    finally:
        db.close()


def _count_remaining(db, campaign_id: str) -> int:
    """Count approved OutreachRecords still waiting to be sent."""
    from ..db_models import OutreachRecord
    return db.query(OutreachRecord).filter(
        OutreachRecord.campaign_id == campaign_id,
        OutreachRecord.status == "approved",
    ).count()


def get_campaign_stats(campaign_id: str) -> dict:
    """Return summary counts for all outreach statuses in a campaign."""
    from ..database import SessionLocal
    from ..db_models import OutreachRecord
    db = SessionLocal()
    try:
        records = db.query(OutreachRecord).filter(OutreachRecord.campaign_id == campaign_id).all()
        counts: dict = {}
        for r in records:
            counts[r.status] = counts.get(r.status, 0) + 1
        counts["total"] = len(records)
        return counts
    finally:
        db.close()
