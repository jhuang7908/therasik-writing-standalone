from __future__ import annotations
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/offline", tags=["offline"])

# Storage for offline requests
OFFLINE_REQUESTS_ROOT = Path("data/offline_requests")
OFFLINE_REQUESTS_ROOT.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("uvicorn.error")

class OfflineRequest(BaseModel):
    service: str
    name: str
    organization: str
    email: str
    target: str
    timeline: str
    description: str
    af2_section: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

def send_offline_email(request: OfflineRequest):
    """
    Simulates sending an email. In a production environment, 
    configure SMTP settings here.
    """
    subject = f"Offline Request: {request.service} - {request.name} ({request.organization})"
    body = (
        f"Service: {request.service}\n"
        f"Name: {request.name}\n"
        f"Organization: {request.organization}\n"
        f"Email: {request.email}\n"
        f"Target: {request.target}\n"
        f"Timeline: {request.timeline}\n\n"
        f"Description:\n{request.description}\n"
    )
    if request.af2_section:
        body += f"\n{request.af2_section}\n"

    # Log to console for the user to see
    logger.info("="*60)
    logger.info(f"NEW OFFLINE REQUEST SUBMITTED TO contact@insynbio.com")
    logger.info(f"Subject: {subject}")
    logger.info("-" * 20)
    logger.info(body)
    logger.info("="*60)

    # In a real scenario, you'd use smtplib or a service here:
    # import smtplib
    # from email.mime.text import MIMEText
    # msg = MIMEText(body)
    # msg['Subject'] = subject
    # msg['From'] = "system@insynbio.com"
    # msg['To'] = "contact@insynbio.com"
    # with smtplib.SMTP('localhost') as s:
    #     s.send_message(msg)

@router.post("/request")
async def create_offline_request(request: OfflineRequest, background_tasks: BackgroundTasks):
    # 1. Save to disk
    request_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.name.replace(' ', '_')}"
    file_path = OFFLINE_REQUESTS_ROOT / f"{request_id}.json"
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(request.dict(), f, indent=4, ensure_ascii=False)

    # 2. "Send" email in background (simulated via logging)
    background_tasks.add_task(send_offline_email, request)

    return {
        "status": "success",
        "message": "Request submitted successfully. Our team will contact you soon.",
        "request_id": request_id
    }
