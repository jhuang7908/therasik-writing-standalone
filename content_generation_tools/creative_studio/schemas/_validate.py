"""Validate example ContentDocs against JSON Schema and the Pydantic model."""
import json
from pathlib import Path

import jsonschema

from content_doc import ContentDoc

HERE = Path(__file__).resolve().parent
schema = json.loads((HERE / "content_doc.schema.json").read_text(encoding="utf-8"))

for name in ("example_ppt.json", "example_xhs.json"):
    payload = json.loads((HERE / name).read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)
    doc = ContentDoc.model_validate(payload)
    print(f"OK  {name:18s} doc_type={doc.doc_type.value:12s} blocks={len(doc.blocks)}")

print("ALL VALID")
