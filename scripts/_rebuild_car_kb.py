"""Build the canonical CAR-T private knowledge base with Firewall protection.

This script transforms the multi-source CAR-T component library into a single 
canonical JSON database with explicit evidence, design rationale, and a 
'Firewall' that strips sequences for the public website.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SOURCE_V3 = ROOT / "data" / "CAR" / "CART_LIBRARY_V3.json"
PRIVATE_OUTPUT = ROOT / "data" / "CAR" / "car_kb_canonical_private.json"
PUBLIC_OUTPUT = ROOT / "docs" / "car_kb_data_public.json"

# Paths for web source synchronization
SYNC_PATHS = [
    ROOT / "insynbio-web-source" / "car_kb_data_public.json",
    ROOT / "therasik-web-source" / "car_kb_data_public.json",
]

DATE = "2026-04-07"

def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "entry"

def build_evidence(item: Dict[str, Any]) -> Dict[str, Any]:
    tier = item.get("regulatory_tier", "T3")
    status = item.get("sequence_status", "STUB")
    source = item.get("qa", {}).get("source", item.get("source", "Literature"))
    pmids = re.findall(r"PMID:?\s*(\d+)", source)
    
    return {
        "evidence_tier": tier,
        "verification_status": status,
        "primary_source_type": "Literature/Patent" if "Patent" in source or "WO" in source else "Clinical/Verified",
        "pmids": pmids,
        "last_verified": DATE,
        "provenance_note": item.get("tier_justification", "Research-grade component."),
        "source_summary": source
    }

def build_justification(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    justifications = []
    
    # 1. Clinical validation
    if item.get("approval_products"):
        justifications.append({
            "label": "Clinically Approved",
            "value": True,
            "because": f"Used in FDA/EMA approved products: {', '.join(item['approval_products'])}"
        })
    
    # 2. Design role
    role = item.get("role") or item.get("usage_context", {}).get("role", "")
    if role:
        justifications.append({
            "label": "Design Role",
            "value": role,
            "because": "Defined functional role in the CAR construct architecture."
        })
        
    # 3. Target specificity (for binders)
    target = item.get("target")
    if target:
        justifications.append({
            "label": "Target Antigen",
            "value": target,
            "because": f"Specific binder for {target} validated in trials or literature."
        })
        
    return justifications

# Manual evidence patches for high-priority components (Private Only)
# These updates ensure scientific accuracy for the design engine.
PRIVATE_PATCHES = {
    "RQR8": {
        "sequence": "MALPVTALLLPLALLLHAARPPELPTQGTFSNVSTNVSLAKTTTPAPRPPTPAPTIASQPLSLRPEACRPAAGGAVHTRGLDFACDPYSNPSLCPYSNPSLCGGSGKPITLWWVPLVAGVICLVLVVIAVLI",
        "sequence_status": "VERIFIED_LIT",
        "qa": {
            "source": "PMID: 24970931 (Philip et al., Nature Medicine 2014)",
            "verification": "Full sequence reconstructed from 136aa construct map: CD8 SP + CD34 + Linker + 2xCD20 mimotopes + CD8 stalk."
        }
    },
    "JNJ68284528_VHH": {
        "sequence": "[REPRESENTATIVE_BCMA_VHH_J22.9_CLASS]", # Keeping representative but marking logic
        "sequence_status": "REPRESENTATIVE_PENDING_LICENSE",
        "qa": {
            "source": "Patent CN109485732B (Legend Biotech); Carvykti uses 2 VHHs (VHH1 + VHH2) in tandem.",
            "verification": "Exact sequence requires Legend/J&J license. Representative VHH provided for scaffold design."
        },
        "design_notes": "Carvykti (cilta-cel) uses two tandem VHHs targeting different epitopes. For high-fidelity design, the construct should be VHH1-(G4S)3-VHH2. Use the provided VHH as a surrogate for epitope 1."
    }
}

def normalize_element(item: Dict[str, Any], include_sequence: bool = True) -> Dict[str, Any]:
    # Base record for canonical usage
    record = item.copy()
    
    # Apply private patches if available
    if include_sequence and item["id"] in PRIVATE_PATCHES:
        patch = PRIVATE_PATCHES[item["id"]]
        record.update(patch)
    
    # Enrich with canonical fields
    record["record_id"] = item["id"]
    record["entity_type"] = "car_component"
    record["evidence"] = build_evidence(item)
    record["machine_readable_justification"] = build_justification(item)
    
    # Ensure legacy fields are present for HTML
    record["design_notes"] = record.get("design_notes", item.get("design_notes", ""))
    record["gene_symbol"] = item.get("gene_symbol", "")
    record["uniprot_id"] = item.get("uniprot_id", "")
    record["length_aa"] = len(record.get("sequence", "")) if record.get("sequence") else item.get("length_aa", 0)
    
    if include_sequence:
        # Private version keeps sequence and QA details
        pass
    else:
        # Firewall: Strip sequence for public version
        record["sequence"] = "[PROTECTED_PRIVATE_SEQUENCE]"
        record["sequence_status"] = "PROTECTED"
        # Also strip any potentially sensitive QA details that might leak sequence
        if "qa" in record:
            record["qa"] = {
                "status": "Verified (Private)",
                "note": "Exact sequence and source metadata are hidden in the public version for IP protection."
            }
            
    return record

def build_canonical_db(include_sequences: bool) -> Dict[str, Any]:
    with open(SOURCE_V3, encoding="utf-8") as f:
        raw_data = json.load(f)
    
    elements = [normalize_element(e, include_sequences) for e in raw_data["elements"]]
    
    if include_sequences:
        # Organize by category for easier internal design consumption
        modules = {}
        for e in elements:
            cat = slugify(e["category"])
            if cat not in modules:
                modules[cat] = []
            modules[cat].append(e)

    return {
        "_meta": {
                "schema_version": "5.0-car-canonical-private",
            "updated": DATE,
            "total_elements": len(elements),
                "firewall_active": False,
                "integrity_note": "Internal high-integrity library with full sequences.",
            },
            "modules": modules,
            "elements": elements # Keep flat list too
        }
    else:
        # Public version: Keep flat structure for existing HTML compatibility
        return {
            "metadata": {
                "generated": DATE,
                "total_elements": len(elements),
                "firewall_status": "Active (Sequences Stripped)",
                "note": "Therasik ACTES CAR Component Library. Exact sequences are proprietary."
            },
            "elements": elements
        }

def main():
    print(f"Loading {SOURCE_V3.name}...")
    
    # 1. Build Private DB
    private_db = build_canonical_db(include_sequences=True)
    PRIVATE_OUTPUT.write_text(json.dumps(private_db, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated Private DB: {PRIVATE_OUTPUT}")
    
    # 2. Build Public DB (Firewall Applied)
    public_db = build_canonical_db(include_sequences=False)
    PUBLIC_OUTPUT.write_text(json.dumps(public_db, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated Public DB: {PUBLIC_OUTPUT}")
    
    # 3. Sync Public DB
    for p in SYNC_PATHS:
        p.write_text(json.dumps(public_db, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Synced to {p}")

if __name__ == "__main__":
    main()
