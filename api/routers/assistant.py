"""
Therasik AI assistant API — DeepSeek-chat only, credit by answer length tier.
"""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api import assistant_engine, auth_db
from api.routers.auth import _bind_tenant, _tenant_from_request, get_session_payload

router = APIRouter(prefix="/assistant", tags=["Assistant"])

SERVICE_BRIEF_THERASIK = "therasik_assistant_brief"
SERVICE_DETAIL_THERASIK = "therasik_assistant_detail"
SERVICE_BRIEF_INSYNBIO = "insynbio_assistant_brief"
SERVICE_DETAIL_INSYNBIO = "insynbio_assistant_detail"


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    mode: Literal["brief", "detail"] = "brief"
    report_context: Optional[Dict[str, Any]] = None


class AssistantChatResponse(BaseModel):
    ok: bool
    assistant_name: str = "Therasik"
    answer: str
    char_count: int
    max_chars: int
    credits_charged: int
    balance: int
    mode: str
    disclaimer: str


def _get_assistant_config(request: Request) -> Dict[str, str]:
    tenant = _bind_tenant(request)
    # Allow local testing (127.0.0.1 or localhost) to pass the checks
    host = (request.headers.get("host", "") or "").split(":")[0].lower()
    is_local = host in ("127.0.0.1", "localhost")
    
    # site query param can override tenant for cross-site testing if local
    site = request.query_params.get("site", "").lower()
    if is_local and site:
        tenant = site

    if tenant == "therasik":
        return {
            "tenant": "therasik",
            "name": "Therasik",
            "brief_service": SERVICE_BRIEF_THERASIK,
            "detail_service": SERVICE_DETAIL_THERASIK,
            "disclaimer": "AI 解读仅供参考，不构成实验、临床或注册建议；正式结论以平台计算报告为准。",
            "locale": "zh"
        }
    elif tenant == "insynbio":
        return {
            "tenant": "insynbio",
            "name": "InSynBio",
            "brief_service": SERVICE_BRIEF_INSYNBIO,
            "detail_service": SERVICE_DETAIL_INSYNBIO,
            "disclaimer": "AI interpretation is for reference only and does not constitute experimental, clinical, or regulatory advice. Official conclusions are based on the platform's calculation reports.",
            "locale": "en"
        }
    else:
        if not is_local:
            raise HTTPException(403, "Assistant is not available for this tenant")
        # Default for local if not specified
        return {
            "tenant": "insynbio",
            "name": "InSynBio",
            "brief_service": SERVICE_BRIEF_INSYNBIO,
            "detail_service": SERVICE_DETAIL_INSYNBIO,
            "disclaimer": "AI interpretation is for reference only.",
            "locale": "en"
        }


@router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(
    request: Request,
    body: AssistantChatRequest,
    payload: Dict[str, Any] = Depends(get_session_payload),
) -> AssistantChatResponse:
    config = _get_assistant_config(request)
    uid = int(payload["uid"])
    if not assistant_engine.check_rate_limit(uid):
        raise HTTPException(429, "Too many requests; try again in a minute")

    from api.pricing_constants import (
        ASSISTANT_BRIEF_CREDITS,
        ASSISTANT_DETAIL_CREDITS,
        TRIAL_ASSISTANT_FREE_TURNS,
    )

    chat_count = auth_db.count_assistant_chats(uid)

    limits = assistant_engine.MODE_LIMITS[body.mode]
    credits = (
        0
        if chat_count < TRIAL_ASSISTANT_FREE_TURNS
        else (ASSISTANT_BRIEF_CREDITS if body.mode == "brief" else ASSISTANT_DETAIL_CREDITS)
    )
    service_id = config["brief_service"] if body.mode == "brief" else config["detail_service"]

    bal = int(payload.get("credits") or 0)
    if credits > 0:
        ok, bal, msg = auth_db.debit_user(
            uid,
            credits,
            service_id,
            run_id=None,
            extra={"mode": body.mode, "phase": "pre", "tenant": config["tenant"]},
        )
        if not ok:
            raise HTTPException(402, f"Insufficient credits ({msg})")

    try:
        result = assistant_engine.run_assistant_chat(
            user_message=body.message,
            mode=body.mode,
            report_context=body.report_context,
            locale=config["locale"],
            assistant_name=config["name"],
        )
    except RuntimeError as e:
        code = str(e)
        if code == "deepseek_not_configured":
            auth_db.add_credits(uid, credits)
            raise HTTPException(503, f"{config['name']} assistant is temporarily unavailable; credits refunded")
        auth_db.add_credits(uid, credits)
        raise HTTPException(502, "Assistant upstream error; credits refunded")
    except Exception:
        auth_db.add_credits(uid, credits)
        raise HTTPException(502, "Assistant error; credits refunded")

    return AssistantChatResponse(
        ok=True,
        assistant_name=config["name"],
        answer=result["answer"],
        char_count=int(result["char_count"]),
        max_chars=int(result["max_chars"]),
        credits_charged=credits,
        balance=bal,
        mode=body.mode,
        disclaimer=config["disclaimer"],
    )


@router.get("/config")
def assistant_config(request: Request) -> Dict[str, Any]:
    """Public pricing / limits for console UI."""
    from api.pricing_constants import ASSISTANT_BRIEF_CREDITS, ASSISTANT_DETAIL_CREDITS

    config = _get_assistant_config(request)
    tenant = config.get("tenant", "insynbio")
    if tenant == "therasik":
        pricing_note = "1 CNY = 50 credits"
        brief_credits = 5
        detail_credits = 20
        brief_cny = 0.10
        detail_cny = 0.40
    else:
        pricing_note = "$10 = 1,000 credits"
        brief_credits = ASSISTANT_BRIEF_CREDITS
        detail_credits = ASSISTANT_DETAIL_CREDITS
        brief_cny = None
        detail_cny = None
    from api.pricing_constants import TRIAL_ASSISTANT_FREE_TURNS

    return {
        "assistant_name": config["name"],
        "model": "deepseek-chat",
        "pricing_note": pricing_note,
        "trial_assistant_free_turns": TRIAL_ASSISTANT_FREE_TURNS,
        "modes": {
            "brief": {
                "label": "Answer" if config["locale"] == "en" else "回答",
                "max_chars": 250,
                "credits": brief_credits,
                "cny_approx": brief_cny,
            },
            "detail": {
                "label": "Think" if config["locale"] == "en" else "思索",
                "max_chars": 500,
                "credits": detail_credits,
                "cny_approx": detail_cny,
            },
        },
        "disclaimer": config["disclaimer"],
    }
