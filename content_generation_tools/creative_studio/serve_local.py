#!/usr/bin/env python3
"""
Creative Studio — Lightweight local server (SQLite, no Celery/Redis/Postgres).

Usage:
    python serve_local.py --deepseek-key sk-xxx [--openai-key sk-xxx] [--port 8100]

Requirements:
    pip install fastapi uvicorn sqlalchemy aiosqlite python-jose[cryptography] passlib[bcrypt] pydantic-settings openai python-pptx

Then open:  file:///...ui_prototype/console.html
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ── add project root to path so worker/renderer imports work ──────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("creative_studio")

# ── parse CLI args first so we can set env vars before pydantic-settings loads ─
_parser = argparse.ArgumentParser(description="Creative Studio local server")
_parser.add_argument("--deepseek-key", default=os.environ.get("DEEPSEEK_API_KEY", ""))
_parser.add_argument("--openai-key",   default=os.environ.get("OPENAI_API_KEY", ""))
_parser.add_argument("--anthropic-key", default=os.environ.get("ANTHROPIC_API_KEY", ""))
_parser.add_argument("--kimi-key",      default=os.environ.get("KIMI_API_KEY", ""))
_parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8100)))
_parser.add_argument("--host", default="0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
_args, _ = _parser.parse_known_args()

if _args.deepseek_key:
    os.environ["DEEPSEEK_API_KEY"] = _args.deepseek_key
if _args.openai_key:
    os.environ["OPENAI_API_KEY"] = _args.openai_key
if _args.anthropic_key:
    os.environ["ANTHROPIC_API_KEY"] = _args.anthropic_key
if _args.kimi_key:
    os.environ["KIMI_API_KEY"] = _args.kimi_key

# ── config ────────────────────────────────────────────────────────────────────
# On Render, /data is the persistent disk mount; locally use ./outputs
_DATA_ROOT    = Path("/data") if Path("/data").exists() and os.environ.get("PORT") else ROOT
SECRET_KEY    = os.environ.get("SECRET_KEY", "local-dev-secret-change-in-prod")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ALGORITHM     = "HS256"
TOKEN_EXPIRE  = 60 * 24  # minutes
OUTPUT_DIR    = _DATA_ROOT / "outputs"
DB_PATH       = _DATA_ROOT / "local_studio.db"
DEMO_USER     = {"username": "admin", "password": "nova123",
                 "email": "admin@insynbio.com", "credits": 999999999, "plan": "admin"}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = _DATA_ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _extract_pdf_text(path: Path, max_chars: int = 4000) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages[:20]:
                t = page.extract_text()
                if t:
                    text_parts.append(t.strip())
        full = "\n\n".join(text_parts)
        return full[:max_chars] + ("…" if len(full) > max_chars else "")
    except Exception as exc:
        logger.warning("PDF extract failed: %s", exc)
        return ""

# ── SQLite / SQLAlchemy ───────────────────────────────────────────────────────
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass

class JobRow(Base):
    __tablename__ = "jobs"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = Column(String, default="admin")
    doc_type     = Column(String, default="ppt")
    template_id  = Column(String, default="default")
    status       = Column(String, default="queued")   # queued|running|done|failed
    brief        = Column(Text, default="")
    result_url   = Column(String, default="")
    error_msg    = Column(Text, default="")
    credit_actual= Column(Integer, default=0)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    content_doc  = Column(Text, default="")

Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── auth helpers ──────────────────────────────────────────────────────────────
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2  = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def _make_token(sub: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE)
    return jwt.encode({"sub": sub, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

def _verify_token(token: str = Depends(oauth2)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return sub
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ── Pydantic schemas ──────────────────────────────────────────────────────────
class LoginReq(BaseModel):
    username: str
    password: str

class RegisterReq(BaseModel):
    email: str
    password: str

class JobReq(BaseModel):
    doc_type:        str = "ppt"
    template_id:     str = "default"
    request_summary: str
    image_tier:      str = "auto"
    lang:            str = "zh"
    slide_count:     int = 8
    document_text:   str = ""     # extracted text from uploaded PDF/doc
    use_multi_agent: bool = True   # default: use multi-agent pipeline
    agent_tier:      str = "standard"  # standard|premium

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Creative Studio Local", version="0.1.0-local", docs_url="/api/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # local dev — allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve UI pages ─────────────────────────────────────────────────────────────
UI_DIR = ROOT / "ui_prototype"

@app.get("/", include_in_schema=False)
def serve_landing():
    return FileResponse(UI_DIR / "landing.html")

@app.get("/console", include_in_schema=False)
@app.get("/console.html", include_in_schema=False)
def serve_console():
    return FileResponse(UI_DIR / "console.html")

@app.get("/landing", include_in_schema=False)
@app.get("/landing.html", include_in_schema=False)
def serve_landing2():
    return FileResponse(UI_DIR / "landing.html")

# ── health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "local-sqlite",
            "deepseek_key": bool(os.environ.get("DEEPSEEK_API_KEY")),
            "openai_key":   bool(os.environ.get("OPENAI_API_KEY")),
            "kimi_key":     bool(os.environ.get("KIMI_API_KEY"))}

# ── auth ──────────────────────────────────────────────────────────────────────
@app.post("/api/auth/register")
def register(req: RegisterReq):
    # In local mode, any registration succeeds and creates a session
    token = _make_token(req.email)
    return {"access_token": token, "token_type": "bearer",
            "user": {"email": req.email, "credits": 200, "plan": "starter"}}

@app.post("/api/auth/token")
def token_login(form: OAuth2PasswordRequestForm = Depends()):
    if form.username == DEMO_USER["username"] and form.password == DEMO_USER["password"]:
        return {"access_token": _make_token(form.username), "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="用户名或密码错误")

@app.post("/api/auth/login")
def login(req: LoginReq):
    if req.username in (DEMO_USER["username"], DEMO_USER["email"]) and req.password == DEMO_USER["password"]:
        token = _make_token(req.username)
        return {"access_token": token, "token_type": "bearer",
                "user": {"email": DEMO_USER["email"], "credits": DEMO_USER["credits"], "plan": DEMO_USER["plan"]}}
    # In local dev, accept any login (just log the attempt)
    logger.info("Local login: %s (non-demo user, accepting in dev mode)", req.username)
    token = _make_token(req.username)
    return {"access_token": token, "token_type": "bearer",
            "user": {"email": req.username, "credits": 200, "plan": "starter"}}

@app.get("/api/auth/me")
def me(sub: str = Depends(_verify_token)):
    if sub == DEMO_USER["username"]:
        return {"email": DEMO_USER["email"], "credits": DEMO_USER["credits"], "plan": DEMO_USER["plan"]}
    return {"email": sub, "credits": 200, "plan": "starter"}

# ── templates ─────────────────────────────────────────────────────────────────
@app.get("/api/templates")
def get_templates():
    tpl_dir = ROOT / "templates"
    if not tpl_dir.exists():
        return []
    results = []
    for f in tpl_dir.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as jf:
                tpl = json.load(jf)
                # Ensure template_id is set
                if "template_id" not in tpl:
                    tpl["template_id"] = f.stem
                results.append(tpl)
        except Exception as e:
            logger.warning("Failed to load template %s: %s", f.name, e)
    # Sort by name or ID
    results.sort(key=lambda x: x.get("template_id", ""))
    return results

# ── file upload ───────────────────────────────────────────────────────────────
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...),
                      sub: str = Depends(_verify_token)):
    ext = Path(file.filename or "upload").suffix.lower()
    fname = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / fname
    dest.write_bytes(await file.read())
    extracted = ""
    if ext == ".pdf":
        extracted = _extract_pdf_text(dest)
        logger.info("PDF extracted: %d chars", len(extracted))
    return {"filename": fname, "original": file.filename,
            "size": dest.stat().st_size, "extracted_text": extracted}

# ── jobs ──────────────────────────────────────────────────────────────────────
@app.post("/api/jobs", status_code=201)
def create_job(req: JobReq, db: Session = Depends(get_db),
               sub: str = Depends(_verify_token)):
    job = JobRow(
        id=str(uuid.uuid4()),
        user_id=sub,
        doc_type=req.doc_type,
        template_id=req.template_id,
        status="queued",
        brief=req.request_summary,
    )
    db.add(job); db.commit(); db.refresh(job)

    # Process synchronously in a thread so we don't block the event loop
    import threading
    t = threading.Thread(target=_run_job, args=(job.id, req), daemon=True)
    t.start()

    return {"id": job.id, "status": "queued",
            "doc_type": req.doc_type, "template_id": req.template_id}

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db),
            sub: str = Depends(_verify_token)):
    job = db.get(JobRow, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    result = {
        "id": job.id,
        "status": job.status,
        "doc_type": job.doc_type,
        "template_id": job.template_id,
        "result_url": job.result_url,
        "credit_actual": job.credit_actual,
        "error_message": job.error_msg,
    }
    if job.content_doc:
        try:
            result["content_doc"] = json.loads(job.content_doc)
        except Exception:
            pass
    return result

@app.get("/api/jobs")
def list_jobs(db: Session = Depends(get_db), sub: str = Depends(_verify_token)):
    jobs = db.query(JobRow).filter_by(user_id=sub).order_by(JobRow.created_at.desc()).limit(20).all()
    return [{"id": j.id, "status": j.status, "doc_type": j.doc_type,
             "credit_actual": j.credit_actual, "created_at": str(j.created_at)} for j in jobs]

@app.get("/api/outputs/{filename}")
def get_output(filename: str, sub: str = Depends(_verify_token)):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(path), filename=filename)

# ── core generation pipeline (synchronous) ───────────────────────────────────
def _run_job(job_id: str, req: JobReq):
    db = SessionLocal()
    try:
        job = db.get(JobRow, job_id)
        job.status = "running"; db.commit()

        deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        openai_key   = os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        kimi_key     = os.environ.get("KIMI_API_KEY", "")
        keys = {
            "deepseek": deepseek_key or None,
            "openai": openai_key or None,
            "anthropic": anthropic_key or None,
            "kimi": kimi_key or None
        }

        # Step 1: LLM → ContentDoc  (multi-agent or single-call)
        if req.use_multi_agent and req.doc_type == "ppt":
            logger.info("[%s] Multi-agent pipeline (brief=%.60s, tier=%s)",
                        job_id, req.request_summary, req.agent_tier)
            from worker.multi_agent import run_multi_agent_pipeline
            content_doc = run_multi_agent_pipeline(
                brief=req.request_summary,
                doc_type=req.doc_type,
                slide_count=req.slide_count,
                lang=req.lang,
                doc_text=req.document_text,
                keys=keys,
                model_tier=req.agent_tier,
            )
        else:
            logger.info("[%s] Single-call LLM (brief=%.60s)", job_id, req.request_summary)
            content_doc = _call_llm(req)
            # Enforce slide count for single-call path
            if req.doc_type == "ppt" and req.slide_count:
                content_doc = _adjust_slide_count(content_doc, req.slide_count)

        # Step 2: Image generation (GPT-Image-2 / gpt-image-1)
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key and req.image_tier != "template_only":
            try:
                from worker.image_router import resolve_images
                content_doc.setdefault("_meta", {})["doc_id"] = job_id
                content_doc = resolve_images(content_doc, req.doc_type, req.image_tier)
                ic = content_doc.get("_meta", {}).get("image_credits", 0)
                logger.info("[%s] Images resolved, image_credits=%s", job_id, ic)
            except Exception as img_exc:
                logger.warning("[%s] Image routing failed (skipping): %s", job_id, img_exc)

        # Step 3: Render PPTX
        out_path = OUTPUT_DIR / f"{job_id}.pptx"
        from renderer.ppt_renderer import render_ppt
        qa = render_ppt(content_doc, None, str(out_path))
        logger.info("[%s] Rendered %s slides → %s", job_id, qa["slide_count"], out_path)

        image_credits = content_doc.get("_meta", {}).get("image_credits", 0)
        credits = 50 + req.slide_count * 5 + image_credits
        job.status       = "done"
        job.result_url   = f"/api/outputs/{out_path.name}"
        job.credit_actual = credits
        job.content_doc  = json.dumps(content_doc, ensure_ascii=False)
        db.commit()
        logger.info("[%s] Done ✓", job_id)

    except Exception as exc:
        logger.error("[%s] Failed: %s", job_id, exc, exc_info=True)
        job = db.get(JobRow, job_id)
        if job:
            job.status = "failed"
            job.error_msg = str(exc)[:500]
            db.commit()
    finally:
        db.close()

def _call_llm(req: JobReq) -> dict:
    """DeepSeek primary → GPT-4o-mini fallback."""
    from worker.llm_router import SYSTEM_PROMPT, _strip_json
    import re, json as _json

    system = SYSTEM_PROMPT + f"\n\n幻灯片数量要求：{req.slide_count} 页（包括封面和总结）。语言：{'中文' if req.lang=='zh' else req.lang}。"
    user_msg = f"业务类型: {req.doc_type}\n用户需求: {req.request_summary}\n模板风格参考: {req.template_id}\n幻灯片数量: {req.slide_count} 页"

    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    openai_key   = os.environ.get("OPENAI_API_KEY", "")

    if deepseek_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com/v1")
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": system},
                          {"role": "user",   "content": user_msg}],
                max_tokens=6000, temperature=0.6,
            )
            raw = resp.choices[0].message.content
            logger.info("LLM: deepseek-chat succeeded")
            return _json.loads(_strip_json(raw))
        except Exception as e:
            logger.warning("DeepSeek failed: %s, trying OpenAI fallback", e)

    if openai_key:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user_msg}],
            max_tokens=6000, temperature=0.6,
        )
        raw = resp.choices[0].message.content
        logger.info("LLM: gpt-4o-mini succeeded")
        return _json.loads(_strip_json(raw))

    raise RuntimeError("No API key configured. Run: python serve_local.py --deepseek-key sk-xxx")

def _adjust_slide_count(doc: dict, target: int) -> dict:
    """Trim or pad blocks to hit the target slide count."""
    blocks = doc.get("blocks", [])
    if len(blocks) == target:
        return doc
    if len(blocks) > target:
        # Keep first and last, trim middle
        keep = blocks[:target-1] + [blocks[-1]]
        doc["blocks"] = keep[:target]
    else:
        # Pad with extra content slides
        from renderer.ppt_renderer import DEFAULT_TEMPLATE
        last = blocks[-1] if blocks else {}
        while len(doc["blocks"]) < target:
            n = len(doc["blocks"]) + 1
            doc["blocks"].insert(-1, {
                "block_id": f"slide_{n}",
                "layout": "title_bullets",
                "text": {"title": f"第 {n} 章", "headline": "", "subheadline": "",
                         "body_paragraphs": ["内容待填写"]},
                "bullets": ["内容点 1", "内容点 2", "内容点 3"],
            })
    return doc

# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════╗
║      Creative Studio — Local Server                     ║
║                                                          ║
║  🌐  首页:    http://{_args.host}:{_args.port}/            ║
║  🖥️  操作台:  http://{_args.host}:{_args.port}/console     ║
║  📖  API文档: http://{_args.host}:{_args.port}/api/docs    ║
║                                                          ║
║  DeepSeek: {'✓ loaded' if os.environ.get('DEEPSEEK_API_KEY') else '✗ missing  --deepseek-key sk-xxx'}                  ║
║  OpenAI:   {'✓ loaded' if os.environ.get('OPENAI_API_KEY')   else '✗ missing  --openai-key sk-xxx'}                    ║
║  Claude:   {'✓ loaded' if os.environ.get('ANTHROPIC_API_KEY') else '✗ missing  --anthropic-key sk-xxx'}                 ║
║  Kimi:     {'✓ loaded' if os.environ.get('KIMI_API_KEY')      else '✗ missing  --kimi-key sk-xxx'}                      ║
║                                                          ║
║  演示账号:  admin / nova123                              ║
╚══════════════════════════════════════════════════════════╝
""")
    uvicorn.run(app, host=_args.host, port=_args.port, log_level="info")
