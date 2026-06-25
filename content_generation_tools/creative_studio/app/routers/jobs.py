"""Jobs router: create, poll, download."""
import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Job, JobStatus, UsageLedger, User
from app.routers.auth import current_user
from worker.tasks import run_generation_task

router = APIRouter()


# ---------- request/response models ----------
class CreateJobIn(BaseModel):
    doc_type: Literal["ppt", "xiaohongshu", "wechat", "whitepaper"]
    template_id: str
    request_summary: str
    image_tier: Optional[str] = "auto"  # auto|template_only|stock|standard|premium
    brand: Optional[dict] = None
    uploaded_doc_url: Optional[str] = None


class JobOut(BaseModel):
    id: str
    status: str
    doc_type: str
    template_id: Optional[str]
    credit_estimate: int
    credit_actual: int
    result_url: Optional[str]
    qa_report: Optional[dict]
    error_message: Optional[str]


# ---------- helpers ----------
CREDIT_ESTIMATE = {"ppt": 120, "xiaohongshu": 60, "wechat": 80, "whitepaper": 200}


def _deduct(user: User, amount: int, job_id: str, db: Session) -> None:
    if user.credits < amount:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED,
                            f"Insufficient credits ({user.credits}). Need {amount}.")
    user.credits -= amount
    db.add(UsageLedger(user_id=user.id, job_id=job_id,
                       delta=-amount, description="generation"))
    db.commit()


# ---------- endpoints ----------
@router.post("", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def create_job(body: CreateJobIn, user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    estimate = CREDIT_ESTIMATE.get(body.doc_type, 100)
    job = Job(
        id=uuid.uuid4(),
        user_id=user.id,
        doc_type=body.doc_type,
        template_id=body.template_id,
        status=JobStatus.queued,
        credit_estimate=estimate,
        request_summary=body.request_summary,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    # Dispatch to Celery (non-blocking)
    run_generation_task.apply_async(
        args=[str(job.id), body.dict()],
        queue="fast",
    )
    return _job_out(job)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, user: User = Depends(current_user),
            db: Session = Depends(get_db)):
    job = _require_job(job_id, user, db)
    return _job_out(job)


@router.get("", response_model=List[JobOut])
def list_jobs(limit: int = 20, user: User = Depends(current_user),
              db: Session = Depends(get_db)):
    jobs = (db.query(Job).filter_by(user_id=user.id)
            .order_by(Job.created_at.desc()).limit(limit).all())
    return [_job_out(j) for j in jobs]


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_job(job_id: str, user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    job = _require_job(job_id, user, db)
    if job.status not in (JobStatus.queued,):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Only queued jobs can be cancelled")
    job.status = JobStatus.failed
    job.error_message = "Cancelled by user"
    db.commit()


def _require_job(job_id: str, user: User, db: Session) -> Job:
    job = db.get(Job, job_id)
    if not job or str(job.user_id) != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


def _job_out(j: Job) -> JobOut:
    return JobOut(
        id=str(j.id), status=j.status.value, doc_type=j.doc_type,
        template_id=j.template_id, credit_estimate=j.credit_estimate,
        credit_actual=j.credit_actual, result_url=j.result_url,
        qa_report=j.qa_report, error_message=j.error_message,
    )
