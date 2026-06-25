from __future__ import annotations
import os
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
import stripe
from api import auth_db
from api.routers.auth import get_session_payload

router = APIRouter(prefix="/payments", tags=["Payments"])

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

class CreateCheckoutRequest(BaseModel):
    amount_usd: int  # e.g. 50 for $50.00

@router.post("/create-checkout-session")
async def create_checkout_session(
    req: CreateCheckoutRequest,
    req_obj: Request,
    payload: Dict[str, Any] = Depends(get_session_payload)
):
    if not stripe.api_key:
        raise HTTPException(500, "Stripe not configured")
    
    # Calculate credits: $10 = 1,000 credits (see api/pricing_constants.py)
    from api.pricing_constants import usd_to_credits

    credits_to_add = usd_to_credits(req.amount_usd)
    
    try:
        # Determine the base URL dynamically from the request headers to support both console.insynbio.com and www.insynbio.com
        origin = req_obj.headers.get("origin") or req_obj.headers.get("referer") or os.environ.get("INSYNBIO_BASE_URL", "https://console.insynbio.com")
        if origin.endswith("/"):
            origin = origin[:-1]
            
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"{credits_to_add} InSynBio Credits",
                    },
                    "unit_amount": req.amount_usd * 100, # in cents
                },
                "quantity": 1,
            }],
            mode="payment",
            billing_address_collection="required",
            phone_number_collection={"enabled": True},
            shipping_address_collection={
                "allowed_countries": ["US", "CN", "GB", "CA", "SG", "AU", "DE", "FR", "JP"],
            },
            success_url=f"{origin}/?payment=success",
            cancel_url=f"{origin}/?payment=cancel",
            metadata={
                "uid": payload["uid"],
                "credits": credits_to_add
            }
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    # Allow local testing without a signature
    if not STRIPE_WEBHOOK_SECRET:
        print("[PAYMENT] Warning: STRIPE_WEBHOOK_SECRET not set, accepting payload without signature verification")
        try:
            import json
            event = json.loads(payload)
        except Exception:
            raise HTTPException(400, "Invalid JSON payload")
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            raise HTTPException(400, "Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(400, "Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        uid = session["metadata"]["uid"]
        credits = int(session["metadata"]["credits"])
        
        # Add credits to user
        new_balance = auth_db.add_credits(int(uid), credits)
        print(f"[PAYMENT] Added {credits} credits to user {uid}. New balance: {new_balance}")

    return {"status": "success"}
