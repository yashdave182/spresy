import datetime
import uuid
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, DateTime, Integer, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from .database import Base


def _new_id() -> str:
    return uuid.uuid4().hex


class JobRecord(Base):
    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False, default="pending")
    keyword = Column(String, nullable=False)
    location = Column(String, nullable=True)
    error = Column(String, nullable=True)
    stats = Column(JSON, nullable=True, default={})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    leads = relationship("LeadRecord", back_populates="job", cascade="all, delete-orphan")


class LeadRecord(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.job_id", ondelete="CASCADE"), index=True, nullable=False)

    name = Column(String, nullable=False, default="")
    website = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    category = Column(String, nullable=True)
    description = Column(String, nullable=True)
    source = Column(String, nullable=True)
    ai_score = Column(Float, nullable=True)
    ai_summary = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    verified = Column(Boolean, default=False)
    cin = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("JobRecord", back_populates="leads")


# ---------------------------------------------------------------------------
# Outreach system tables
# ---------------------------------------------------------------------------

class SmtpCredentialRecord(Base):
    """Encrypted SMTP credentials for sending emails."""
    __tablename__ = "smtp_credentials"

    id                 = Column(String, primary_key=True, default=_new_id)
    user_id            = Column(String, default="default", index=True, nullable=False)
    email              = Column(String, nullable=False)
    smtp_host          = Column(String, nullable=False)   # e.g. smtp.gmail.com
    smtp_port          = Column(Integer, default=587)
    encrypted_password = Column(String, nullable=False)   # Fernet-encrypted
    daily_limit        = Column(Integer, default=25)
    sender_name        = Column(String, nullable=True)
    created_at         = Column(DateTime, default=datetime.datetime.utcnow)

    campaigns = relationship("CampaignRecord", back_populates="smtp_credential")
    send_logs = relationship("SendLogRecord", back_populates="credential", cascade="all, delete-orphan")


class CampaignRecord(Base):
    """An outreach campaign targeting leads from a scrape job."""
    __tablename__ = "campaigns"

    id                   = Column(String, primary_key=True, default=_new_id)
    user_id              = Column(String, default="default", index=True, nullable=False)
    job_id               = Column(String, ForeignKey("jobs.job_id"), nullable=False)
    smtp_credential_id   = Column(String, ForeignKey("smtp_credentials.id"), nullable=True)
    prompt               = Column(String, nullable=False)
    email_subject_template = Column(String, nullable=True)
    sender_name          = Column(String, nullable=True)
    physical_address     = Column(String, nullable=True)   # CAN-SPAM required
    status               = Column(String, default="draft") # draft/generating/review/running/paused/completed
    batch_size           = Column(Integer, default=5)
    delay_seconds        = Column(Integer, default=10)
    created_at           = Column(DateTime, default=datetime.datetime.utcnow)

    smtp_credential = relationship("SmtpCredentialRecord", back_populates="campaigns")
    docs            = relationship("UserDocRecord", back_populates="campaign", cascade="all, delete-orphan")
    outreach        = relationship("OutreachRecord", back_populates="campaign", cascade="all, delete-orphan")


class UserDocRecord(Base):
    """Uploaded documents (resume, portfolio) attached to a campaign."""
    __tablename__ = "user_docs"

    id           = Column(String, primary_key=True, default=_new_id)
    campaign_id  = Column(String, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    filename     = Column(String, nullable=False)
    file_path    = Column(String, nullable=False)
    content_text = Column(String, nullable=True)   # extracted text for AI context
    created_at   = Column(DateTime, default=datetime.datetime.utcnow)

    campaign = relationship("CampaignRecord", back_populates="docs")


class OutreachRecord(Base):
    """One outreach message to one lead — the atomic unit of work."""
    __tablename__ = "outreach"

    # Status flow:
    #   pending → generated → approved → claimed → sent
    #   pending → skipped   (no email / invalid / suppressed)
    #   claimed → failed    (transient error — retryable, NOT suppressed)
    #   claimed → bounced   (SMTP 5xx — auto-added to SuppressionRecord)

    id                = Column(String, primary_key=True, default=_new_id)
    campaign_id       = Column(String, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id           = Column(Integer, ForeignKey("leads.id"), nullable=False)
    channel           = Column(String, default="email")
    to_email          = Column(String, nullable=True)
    generated_subject = Column(String, nullable=True)
    generated_message = Column(String, nullable=True)
    user_edited       = Column(Boolean, default=False)
    status            = Column(String, default="pending", index=True)
    skip_reason       = Column(String, nullable=True)   # why skipped (no_email/invalid/suppressed)
    error             = Column(String, nullable=True)
    sent_at           = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.datetime.utcnow)

    campaign = relationship("CampaignRecord", back_populates="outreach")


class SuppressionRecord(Base):
    """Global suppression list — emails that must never be contacted again."""
    __tablename__ = "suppressions"

    id         = Column(String, primary_key=True, default=_new_id)
    user_id    = Column(String, default="default", index=True, nullable=False)
    email      = Column(String, nullable=False, index=True)   # normalized lowercase
    reason     = Column(String, nullable=False)               # hard_bounce/unsubscribed/manual
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "email", name="uq_suppression_user_email"),)


class SendLogRecord(Base):
    """Per-credential daily send counter. Single source of truth for daily limits."""
    __tablename__ = "send_log"

    id            = Column(String, primary_key=True, default=_new_id)
    credential_id = Column(String, ForeignKey("smtp_credentials.id", ondelete="CASCADE"), nullable=False)
    date          = Column(String, nullable=False)   # YYYY-MM-DD UTC
    count         = Column(Integer, default=0)

    credential = relationship("SmtpCredentialRecord", back_populates="send_logs")

    __table_args__ = (UniqueConstraint("credential_id", "date", name="uq_sendlog_cred_date"),)

