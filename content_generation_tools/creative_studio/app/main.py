"""Creative Studio — FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import auth, jobs, templates, webhooks

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: could warm model caches, check DB, etc.
    yield
    # shutdown

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/auth",      tags=["auth"])
app.include_router(jobs.router,      prefix="/api/jobs",      tags=["jobs"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(webhooks.router,  prefix="/api/webhooks",  tags=["webhooks"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.app_version}
