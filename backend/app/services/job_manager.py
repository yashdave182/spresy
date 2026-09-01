import uuid
from typing import Optional, List
from sqlalchemy.orm import Session

from ..models import JobInfo, JobResult, LeadStatus, ScrapeRequest, Lead, JobProgress
from ..database import SessionLocal
from ..db_models import JobRecord, LeadRecord

class JobManager:
    """Database-backed job store with incremental writes."""

    def create(self, request: ScrapeRequest) -> JobInfo:
        job_id = uuid.uuid4().hex[:12]
        
        # We store request params in db or we just store keywords
        # In JobRecord we have keyword, location
        
        db = SessionLocal()
        try:
            record = JobRecord(
                job_id=job_id,
                status=LeadStatus.pending.value,
                keyword=request.keyword,
                location=request.location,
            )
            db.add(record)
            db.commit()
            
            return JobInfo(id=job_id, status=LeadStatus.pending, request=request)
        finally:
            db.close()

    def add_lead(self, job_id: str, lead: Lead) -> None:
        """Incremental commit of a single lead."""
        db = SessionLocal()
        try:
            lead_data = lead.model_dump(exclude={"id"}) # ID is autoincremented in DB
            db_lead = LeadRecord(job_id=job_id, **lead_data)
            db.add(db_lead)
            db.commit()
        finally:
            db.close()

    def mark_status(self, job_id: str, status: str, error: Optional[str] = None) -> None:
        db = SessionLocal()
        try:
            job = db.query(JobRecord).filter(JobRecord.job_id == job_id).first()
            if job:
                job.status = status
                if error:
                    job.error = error
                db.commit()
        finally:
            db.close()

    def mark_partial(self, job_id: str) -> None:
        self.mark_status(job_id, "partial")

    def mark_done(self, job_id: str) -> None:
        self.mark_status(job_id, LeadStatus.completed.value)

    def mark_error(self, job_id: str, error: str) -> None:
        self.mark_status(job_id, LeadStatus.failed.value, error)

    def get(self, job_id: str) -> Optional[JobInfo]:
        db = SessionLocal()
        try:
            job = db.query(JobRecord).filter(JobRecord.job_id == job_id).first()
            if not job:
                return None
            
            # Reconstruct the request model for JobInfo compatibility
            req = ScrapeRequest(keyword=job.keyword, location=job.location)
            
            # Map "partial" to completed for the frontend, or handle properly
            status_val = job.status
            if status_val == "partial":
                status_val = LeadStatus.completed.value
            
            return JobInfo(
                id=job.job_id,
                status=LeadStatus(status_val),
                request=req,
                error=job.error,
                progress=JobProgress(stage="done" if status_val == LeadStatus.completed.value else "running")
            )
        finally:
            db.close()

    def get_result(self, job_id: str) -> Optional[JobResult]:
        db = SessionLocal()
        try:
            job = db.query(JobRecord).filter(JobRecord.job_id == job_id).first()
            if not job:
                return None
            
            leads_records = db.query(LeadRecord).filter(LeadRecord.job_id == job_id).all()
            leads = []
            for r in leads_records:
                l_dict = {c.name: getattr(r, c.name) for c in r.__table__.columns}
                # DB id is an auto-increment Integer; Lead.id expects a str — convert it
                l_dict["id"] = str(l_dict.get("id", ""))
                # Remove job_id — not a field on Lead
                l_dict.pop("job_id", None)
                leads.append(Lead(**l_dict))
                
            req = ScrapeRequest(keyword=job.keyword, location=job.location)
            status_val = job.status
            if status_val == "partial":
                status_val = LeadStatus.completed.value
                
            return JobResult(
                id=job.job_id,
                status=LeadStatus(status_val),
                request=req,
                error=job.error,
                progress=JobProgress(stage="done" if status_val == LeadStatus.completed.value else "running", leads_found=len(leads), total=len(leads)),
                leads=leads,
                stats=job.stats or {},
                csv_path=None # Can generate on the fly via another endpoint if needed
            )
        finally:
            db.close()

    def update_stats(self, job_id: str, stats: dict) -> None:
        db = SessionLocal()
        try:
            job = db.query(JobRecord).filter(JobRecord.job_id == job_id).first()
            if job:
                job.stats = stats
                db.commit()
        finally:
            db.close()

job_manager = JobManager()
