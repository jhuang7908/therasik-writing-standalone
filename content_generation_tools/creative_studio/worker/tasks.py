"""Celery application + generation task."""
from __future__ import annotations

import json
import logging
import os
import sys
import traceback
import uuid
from pathlib import Path

from celery import Celery

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    "creative_studio",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "worker.tasks.run_generation_task": {"queue": "fast"},
    },
)

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def run_generation_task(self, job_id: str, job_params: dict):
    """Main pipeline:
       1. LLM → ContentDoc JSON
       2. Image router → resolved images
       3. Renderer → output file (.pptx / .html / .png)
       4. Upload to object storage (S3 / R2)
       5. Update DB job record
    """
    from app.db import get_db_ctx
    from app.models import Job, JobStatus, UsageLedger
    from worker.llm_router import generate_content_doc
    from worker.image_router import resolve_images

    doc_type = job_params.get("doc_type", "ppt")
    template_id = job_params.get("template_id", "default")
    brief = job_params.get("request_summary", "")
    image_tier = job_params.get("image_tier", "auto")

    def _update_status(db, job, status, **kwargs):
        job.status = status
        for k, v in kwargs.items():
            setattr(job, k, v)
        db.commit()

    try:
        # Mark running
        with get_db_ctx() as db:
            job = db.get(Job, job_id)
            if not job:
                logger.error("Job %s not found", job_id)
                return
            _update_status(db, job, JobStatus.running)

        # Step 1: LLM → ContentDoc
        logger.info("[%s] Step 1: LLM content generation", job_id)
        content_doc = generate_content_doc(brief, doc_type, template_id)
        content_doc.setdefault("meta", {})["doc_id"] = job_id

        # Step 2: Image resolution
        logger.info("[%s] Step 2: Image routing (tier=%s)", job_id, image_tier)
        content_doc = resolve_images(content_doc, doc_type, image_tier)

        # Step 3: File rendering
        logger.info("[%s] Step 3: File rendering (doc_type=%s)", job_id, doc_type)
        out_path = _render(content_doc, doc_type, template_id, job_id)

        # Step 4: Upload (stub — returns local path in dev)
        result_url = _upload(out_path, job_id)

        # Step 5: Update DB
        image_credits = content_doc.get("_meta", {}).get("image_credits", 0)
        total_credits = job_params.get("credit_estimate", 100) + image_credits
        with get_db_ctx() as db:
            job = db.get(Job, job_id)
            _update_status(db, job, JobStatus.done,
                           content_doc=content_doc,
                           result_url=result_url,
                           credit_actual=total_credits,
                           qa_report={"status": "ok",
                                      "blocks": len(content_doc.get("blocks", [])),
                                      "llm_backend": content_doc.get("_meta", {}).get("llm_backend"),
                                      "image_credits": image_credits})
            # Deduct credits
            db.query(type(job.user)).filter_by(id=job.user_id).update(
                {"credits": type(job.user).credits - total_credits}
            )
            db.add(UsageLedger(user_id=job.user_id, job_id=job_id,
                               delta=-total_credits, description="generation"))
            db.commit()

        logger.info("[%s] Done. result_url=%s", job_id, result_url)

    except Exception as exc:
        logger.error("[%s] Failed: %s", job_id, exc)
        try:
            with get_db_ctx() as db:
                job = db.get(Job, job_id)
                if job:
                    _update_status(db, job, JobStatus.failed,
                                   error_message=str(exc)[:500])
        except Exception:
            pass
        raise self.retry(exc=exc)


# ---------- helpers ----------

def _render(content_doc: dict, doc_type: str, template_id: str, job_id: str) -> Path:
    if doc_type == "ppt":
        from renderer.ppt_renderer import render_ppt
        out = OUTPUT_DIR / f"{job_id}.pptx"
        render_ppt(content_doc, None, str(out))
        return out
    elif doc_type in ("xiaohongshu", "wechat"):
        from renderer.html_renderer import render_html
        out = OUTPUT_DIR / f"{job_id}.html"
        render_html(content_doc, doc_type, template_id, str(out))
        return out
    else:
        # whitepaper → PDF via HTML→PDF
        from renderer.html_renderer import render_html
        out = OUTPUT_DIR / f"{job_id}.html"
        render_html(content_doc, doc_type, template_id, str(out))
        return out


def _upload(local_path: Path, job_id: str) -> str:
    """Upload to S3/R2; returns URL. Falls back to local path in dev."""
    if not settings.s3_access_key:
        return str(local_path)
    import boto3
    key = f"jobs/{job_id}/{local_path.name}"
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint or None,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )
    s3.upload_file(str(local_path), settings.s3_bucket, key,
                   ExtraArgs={"ContentType": _mime(local_path)})
    if settings.s3_endpoint:
        return f"{settings.s3_endpoint}/{settings.s3_bucket}/{key}"
    return f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{key}"


def _mime(p: Path) -> str:
    return {".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".html": "text/html",
            ".pdf": "application/pdf",
            ".png": "image/png"}.get(p.suffix, "application/octet-stream")
