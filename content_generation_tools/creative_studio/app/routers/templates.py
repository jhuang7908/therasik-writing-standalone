"""Templates router — list and get templates from templates/ directory."""
import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

TMPL_DIR = Path(__file__).resolve().parents[2] / "templates"


class TemplateOut(BaseModel):
    template_id: str
    name_zh: str
    style: str
    doc_types: List[str]
    description: Optional[str] = None
    preview_url: Optional[str] = None


def _load_all() -> List[dict]:
    result = []
    for f in sorted(TMPL_DIR.glob("*.json")):
        try:
            result.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return result


@router.get("", response_model=List[TemplateOut])
def list_templates(doc_type: Optional[str] = None, style: Optional[str] = None):
    items = _load_all()
    if doc_type:
        items = [t for t in items if doc_type in t.get("doc_types", [])]
    if style:
        items = [t for t in items if t.get("style") == style]
    return items


@router.get("/{template_id}")
def get_template(template_id: str):
    f = TMPL_DIR / f"{template_id}.json"
    if not f.exists():
        raise HTTPException(404, "Template not found")
    return json.loads(f.read_text(encoding="utf-8"))
