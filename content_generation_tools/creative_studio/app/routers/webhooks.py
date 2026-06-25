"""Webhooks router: Stripe + WeChat Pay callbacks."""
import hashlib
import hmac
import json
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db_ctx
from app.models import CreditOrder, UsageLedger, User

router = APIRouter()
settings = get_settings()

CREDIT_PACKAGES = {
    "credits_600": (600, 600),    # USD cents → credits
    "credits_2000": (1800, 2000),
    "credits_6000": (4800, 6000),
}


@router.post("/stripe")
async def stripe_webhook(request: Request,
                         stripe_signature: Optional[str] = Header(None)):
    """Handle Stripe payment_intent.succeeded events."""
    body = await request.body()
    # In production: verify using stripe.Webhook.construct_event + STRIPE_WEBHOOK_SECRET
    try:
        event = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    if event.get("type") == "payment_intent.succeeded":
        pi = event["data"]["object"]
        pkg = pi.get("metadata", {}).get("package")
        user_id = pi.get("metadata", {}).get("user_id")
        _fulfill(user_id, pi["id"], "stripe", pi["amount"], pkg)
    return {"status": "ok"}


@router.post("/wechat")
async def wechat_webhook(request: Request):
    """Handle WeChat Pay payment callback (simplified)."""
    body = await request.body()
    try:
        data = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON")
    out_trade_no = data.get("out_trade_no", "")
    user_id = data.get("attach", "")
    pkg = data.get("body", "")
    if data.get("return_code") == "SUCCESS":
        _fulfill(user_id, out_trade_no, "wechat",
                 int(data.get("total_fee", 0)), pkg)
    return {"return_code": "SUCCESS"}


def _fulfill(user_id: str, ext_id: str, provider: str,
             amount_cents: int, pkg: str) -> None:
    _, credits = CREDIT_PACKAGES.get(pkg, (0, 0))
    if credits == 0:
        return
    with get_db_ctx() as db:
        order = db.query(CreditOrder).filter_by(external_id=ext_id).first()
        if order:
            return  # idempotent
        user = db.get(User, user_id)
        if not user:
            return
        user.credits += credits
        order = CreditOrder(user_id=user_id, provider=provider,
                            external_id=ext_id, amount_usd=amount_cents,
                            credits=credits, status="paid")
        db.add(order)
        db.add(UsageLedger(user_id=user_id, delta=credits,
                           description=f"topup via {provider}"))
        db.commit()
