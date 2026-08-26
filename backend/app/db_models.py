import datetime
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, DateTime, Integer
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from .database import Base

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
