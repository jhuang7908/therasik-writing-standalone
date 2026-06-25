"""
Therasik downstream experiment submission + 5% credit rebate.

When a client accepts an analysis result on the Therasik Console and decides
to forward it to the InSynBio wet-lab pipeline (synthesis, expression,
binding QC, in vivo, etc.), they receive a 5% credit rebate on the credits
spent on the originating analysis run. This is purely a commercial loyalty
mechanism — no algorithmic disclosure occurs.

Pricing reference: 1 CNY = 50 credits.

Endpoints
---------
POST  /downstream/submit       — record the intent + apply rebate
GET   /downstream/orders       — list current user's submissions
GET   /downstream/config       — surface rebate % / pricing notes for the UI
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api import auth_db
from api.routers.auth import _bind_tenant, get_session_payload

router = APIRouter(prefix="/downstream", tags=["Downstream"])

REBATE_PCT = float(os.environ.get("THERASIK_DOWNSTREAM_REBATE_PCT", "5.0"))
PRICE_CNY_PER_50_CREDITS = float(os.environ.get("THERASIK_CNY_PER_50_CREDITS", "1.0"))


def _ensure_table() -> None:
    auth_db.init_db()
    with auth_db._lock:
        conn = auth_db._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS downstream_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid INTEGER NOT NULL,
                    service_id TEXT,
                    run_id TEXT,
                    credits_spent INTEGER NOT NULL DEFAULT 0,
                    rebate_credits INTEGER NOT NULL DEFAULT 0,
                    experiment_kind TEXT,
                    note TEXT,
                    extra TEXT,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_downstream_uid ON downstream_orders (uid, created_at DESC)"
            )
            conn.commit()
        finally:
            conn.close()


class DownstreamSubmitRequest(BaseModel):
    service_id: Optional[str] = Field(None, max_length=80)
    run_id: Optional[str] = Field(None, max_length=120)
    credits_spent: int = Field(..., ge=0, le=10_000_000)
    experiment_kind: Optional[str] = Field(
        None, max_length=80,
        description="e.g. synthesis, expression, binding_qc, in_vivo, cmc_wet"
    )
    note: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[str] = Field(None, max_length=120)


class DownstreamSubmitResponse(BaseModel):
    ok: bool
    order_id: int
    rebate_credits: int
    rebate_pct: float
    new_balance: int
    message: str


def _require_therasik(request: Request) -> str:
    tenant = _bind_tenant(request)
    host = (request.headers.get("host", "") or "").split(":")[0].lower()
    is_local = host in ("127.0.0.1", "localhost")
    if tenant != "therasik" and not is_local:
        raise HTTPException(403, "Downstream submission is only available on console.therasik.com")
    return tenant


@router.post("/submit", response_model=DownstreamSubmitResponse)
def downstream_submit(
    request: Request,
    body: DownstreamSubmitRequest,
    payload: Dict[str, Any] = Depends(get_session_payload),
) -> DownstreamSubmitResponse:
    _require_therasik(request)
    uid = int(payload["uid"])
    _ensure_table()

    rebate = int(round(body.credits_spent * (REBATE_PCT / 100.0)))
    if rebate < 1 and body.credits_spent > 0:
        rebate = 1

    extra_payload = {
        "contact_email": body.contact_email,
        "user_agent": (request.headers.get("user-agent", "") or "")[:200],
    }

    with auth_db._lock:
        conn = auth_db._connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO downstream_orders
                (uid, service_id, run_id, credits_spent, rebate_credits, experiment_kind, note, extra, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    (body.service_id or "")[:80],
                    (body.run_id or "")[:120],
                    int(body.credits_spent),
                    rebate,
                    (body.experiment_kind or "")[:80],
                    (body.note or "")[:500],
                    json.dumps(extra_payload, ensure_ascii=False),
                    time.time(),
                ),
            )
            conn.commit()
            order_id = int(cur.lastrowid)
        except sqlite3.Error as e:
            raise HTTPException(500, f"Failed to record downstream order: {e}")
        finally:
            conn.close()

    new_balance = auth_db.add_credits(uid, rebate) if rebate > 0 else 0

    return DownstreamSubmitResponse(
        ok=True,
        order_id=order_id,
        rebate_credits=rebate,
        rebate_pct=REBATE_PCT,
        new_balance=new_balance,
        message=(
            f"已记录下游实验意向。{REBATE_PCT:.1f}% 积分回扣已发放（+{rebate} credits）。"
            " 我们的运营团队将在 1 个工作日内通过站内/邮件联系您安排实验。"
        ),
    )


@router.get("/orders")
def downstream_orders(
    request: Request,
    payload: Dict[str, Any] = Depends(get_session_payload),
) -> Dict[str, Any]:
    _require_therasik(request)
    uid = int(payload["uid"])
    _ensure_table()
    with auth_db._lock:
        conn = auth_db._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, service_id, run_id, credits_spent, rebate_credits,
                       experiment_kind, note, created_at
                FROM downstream_orders
                WHERE uid = ?
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (uid,),
            ).fetchall()
            orders: List[Dict[str, Any]] = [dict(r) for r in rows]
        finally:
            conn.close()
    return {"ok": True, "orders": orders, "rebate_pct": REBATE_PCT}


@router.get("/config")
def downstream_config(request: Request) -> Dict[str, Any]:
    _require_therasik(request)
    return {
        "rebate_pct": REBATE_PCT,
        "pricing_cny_per_50_credits": PRICE_CNY_PER_50_CREDITS,
        "pricing_note": f"1 CNY = 50 credits · 下游实验回扣 {REBATE_PCT:.1f}%",
        "experiment_kinds": [
            {"id": "synthesis", "label_zh": "基因合成 / 表达"},
            {"id": "binding_qc", "label_zh": "亲和力实验 (SPR/BLI)"},
            {"id": "cmc_wet", "label_zh": "CMC 湿实验 (SEC/CE/HIC)"},
            {"id": "in_vivo", "label_zh": "动物实验 / PK"},
            {"id": "other", "label_zh": "其他 (备注说明)"},
        ],
    }
