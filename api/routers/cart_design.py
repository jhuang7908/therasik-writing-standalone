from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from collections import Counter
from api.models import CartAssemblerRequest, CartAssemblerResult
from core.car_design.cart_assembler import CartAssemblerEngine

router = APIRouter(prefix="/cart", tags=["CAR-T Design"])
engine = CartAssemblerEngine()


@router.post("/assemble", response_model=CartAssemblerResult)
def assemble_cart(req: CartAssemblerRequest):
    """
    Assemble a CAR-T construct from components.
    Uses the internal SSOT registry (CART_LIBRARY_V3/cart_components_registry.json)
    if an ID is provided, otherwise falls back to custom sequence processing.
    Validates structural topology and applies clinical tiering.
    """
    return engine.assemble(req)


@router.get("/stats")
def cart_stats() -> Dict[str, Any]:
    """Return SSOT registry inventory summary: counts by category, tier, indication, cell-type."""
    elements = list(engine.registry.values())
    cats = Counter(e.get("category", "") for e in elements)
    tiers = Counter(e.get("regulatory_tier", "") for e in elements)
    indications: Counter = Counter()
    cell_types: Counter = Counter()
    for e in elements:
        uc = e.get("usage_context", {}) or {}
        for ind in uc.get("indications", []) or []:
            indications[ind] += 1
        for ct in uc.get("cell_types", []) or []:
            cell_types[ct] += 1
    return {
        "total": len(elements),
        "by_category": dict(cats.most_common()),
        "by_tier": dict(tiers),
        "by_indication": dict(indications.most_common()),
        "by_cell_type": dict(cell_types.most_common()),
    }


@router.get("/invivo_browse")
def cart_invivo_browse() -> Dict[str, Any]:
    """
    Return the complete In-Vivo CAR Module inventory pre-organised as a 3-level tree:
      level1: Ex Vivo / In Vivo (static labels)
      level2: disease  (subcategory-derived)
      level3: vehicle  (delivery modality, inferred from element metadata)
    Each leaf contains the component cards needed by the browser UI.
    """
    elements = list(engine.registry.values())
    invivo = [e for e in elements if e.get("category") == "In-Vivo CAR Module"]

    # ── vehicle inference from element metadata / design_notes ─────────────────
    LNP_IDS = {
        "CD5_scFv_InVivo_Targeting", "OKT8_hu_scFv",
        "CD3_OKT3_LNP_Targeting", "CD8_OKT8_LNP_Targeting_Alias",
        "CD2_Siplizumab_LNP_Targeting", "CD56_Lorvotuzumab_LNP_Targeting",
        "CD7_TH69_LNP_Targeting", "CD16_3G8_LNP_Targeting",
    }
    MRNA_IDS = {"HBA1_3UTR", "HBB_3UTR", "AES_3UTR_Synthetic", "SFFV_Promoter_mRNA"}

    DISEASE_ORDER = [
        "Solid Tumor", "Hematologic (Liquid Tumor)", "Neurological (CNS/Glioma)",
        "Autoimmune (Self-Tolerance/CAAR)", "General/Multi-Target",
        "LNP/mRNA Targeting Ligand", "mRNA Stability Element", "Expression Control",
    ]
    DISEASE_LABELS = {
        "Solid Tumor": "Solid Tumor",
        "Hematologic (Liquid Tumor)": "Hematologic / Blood Cancer",
        "Neurological (CNS/Glioma)": "Neurological / CNS",
        "Autoimmune (Self-Tolerance/CAAR)": "Autoimmune",
        "General/Multi-Target": "General / Multi-Target",
        "LNP/mRNA Targeting Ligand": "LNP Targeting Ligands",
        "mRNA Stability Element": "mRNA Stability (3'UTR)",
        "Expression Control": "Promoter / Expression Control",
    }

    def make_card(e: Dict[str, Any]) -> Dict[str, Any]:
        uc = e.get("usage_context", {}) or {}
        qa = e.get("qa", {}) or {}
        eid = e.get("id", "")
        vehicle = "CAR-T (LNP-mRNA)" if eid in LNP_IDS else \
                  "mRNA element" if eid in MRNA_IDS else \
                  "CAR-T (LNP-mRNA)" if "LNP" in (e.get("name") or "") else \
                  "CAR-T (Viral/Direct)" if "Viral" in (e.get("design_notes") or "") else \
                  "CAR-T"
        return {
            "id": eid,
            "name": e.get("name"),
            "subcategory": e.get("subcategory"),
            "tier": e.get("regulatory_tier"),
            "target": e.get("target") or "",
            "length": e.get("length"),
            "sequence_status": e.get("sequence_status"),
            "indications": uc.get("indications") or [],
            "cell_types": uc.get("cell_types") or [],
            "role": uc.get("role") or "",
            "approval_products": e.get("approval_products") or [],
            "clinical_trials": e.get("clinical_trials") or [],
            "source": qa.get("source") or "",
            "vehicle": vehicle,
            "design_notes": e.get("design_notes") or "",
        }

    tree: Dict[str, Any] = {}
    for sub in DISEASE_ORDER:
        items = [e for e in invivo if e.get("subcategory") == sub]
        if not items:
            continue
        label = DISEASE_LABELS.get(sub, sub)
        cards = [make_card(e) for e in items]
        # group by vehicle within each disease
        by_vehicle: Dict[str, List] = {}
        for c in cards:
            v = c["vehicle"]
            by_vehicle.setdefault(v, []).append(c)
        tree[sub] = {
            "label": label,
            "total": len(cards),
            "vehicles": sorted(by_vehicle.keys()),
            "by_vehicle": by_vehicle,
            "all_cards": cards,
        }

    return {
        "total": len(invivo),
        "diseases": list(tree.keys()),
        "disease_labels": DISEASE_LABELS,
        "tree": tree,
    }


@router.get("/vector_options")
def cart_vector_options() -> Dict[str, Any]:
    """Return the vector-architecture component palette grouped by role:

      promoter / polyA / wpre / utr_5 / utr_3 / sp / two_a / ires

    Used by the frontend Step-3 "Vector Architecture" picker. Each entry includes
    id, name, length, sequence_status, regulatory_tier so the UI can render
    informative dropdowns. Only verified entries are returned for one-click use
    in production; stubs are filtered out.
    """
    # Mapping: which (category, subcategory) buckets feed each role
    # The registry uses fairly free-form subcategories so we list explicitly.
    # For protein elements (SP, 2A) we require sequence_status=VERIFIED.
    # For DNA-only elements (Promoter, polyA, WPRE, UTR, IRES) sequence_status is
    # often absent — accept any entry with a non-empty sequence.
    def keep_protein(e: Dict[str, Any]) -> bool:
        return (e.get("sequence_status") or "").upper() == "VERIFIED" and bool(e.get("sequence"))
    def keep_dna(e: Dict[str, Any]) -> bool:
        return bool(e.get("sequence"))

    def shape(e: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": e.get("id"),
            "name": e.get("name"),
            "subcategory": e.get("subcategory"),
            "length": e.get("length"),
            "tier": e.get("regulatory_tier"),
            "design_notes": e.get("design_notes") or "",
        }

    elements = list(engine.registry.values())

    # Signal peptides: VERIFIED proteins only
    sp_list = [shape(e) for e in elements if e.get("category") == "Signal Peptide" and keep_protein(e)]

    # Promoters / polyA / WPRE / UTRs (DNA — accept any with sequence)
    promoters: List[Dict[str, Any]] = []
    polyas: List[Dict[str, Any]] = []
    wpres: List[Dict[str, Any]] = []
    utrs_5: List[Dict[str, Any]] = []
    utrs_3: List[Dict[str, Any]] = []
    for e in elements:
        if e.get("category") not in ("Regulatory Element", "In-Vivo CAR Module"):
            continue
        if not keep_dna(e):
            continue
        eid = (e.get("id") or "").lower()
        name = (e.get("name") or "").lower()
        sub  = (e.get("subcategory") or "").lower()
        if "promoter" in eid or "promoter" in name or "ltr" in sub:
            promoters.append(shape(e))
        elif "polya" in eid or "polya" in name:
            polyas.append(shape(e))
        elif "wpre" in eid or "wpre" in name:
            wpres.append(shape(e))
        elif "5utr" in eid or "5'utr" in name or "5_utr" in eid:
            utrs_5.append(shape(e))
        elif "3utr" in eid or "3'utr" in name or "3_utr" in eid or sub == "mrna stability element":
            utrs_3.append(shape(e))

    # 2A peptides (protein), IRES (DNA)
    two_a = [shape(e) for e in elements
             if e.get("id") in {"T2A", "P2A", "F2A", "E2A"} and keep_protein(e)]
    ires  = [shape(e) for e in elements
             if (e.get("id") or "").startswith("IRES") and keep_dna(e)]

    return {
        "vector_modes": ["lentivirus", "aav", "retrovirus", "mRNA-LNP", "transposon"],
        "defaults": {
            "lentivirus":  {"promoter": "EF1a_Promoter", "polyA": "BGH_polyA",  "wpre": "WPRE"},
            "retrovirus":  {"promoter": "MSCV_LTR",      "polyA": "BGH_polyA",  "wpre": None},
            "aav":         {"promoter": "EF1a_Promoter", "polyA": "SV40_polyA", "wpre": None},
            "mRNA-LNP":    {"promoter": "T7_Promoter",   "polyA": "120A_tail",  "wpre": None},
            "transposon":  {"promoter": "EF1a_Promoter", "polyA": "BGH_polyA",  "wpre": None},
        },
        "sp": sp_list,
        "promoter": promoters,
        "polyA": polyas,
        "wpre": wpres,
        "utr_5": utrs_5,
        "utr_3": utrs_3,
        "two_a": two_a,
        "ires": ires,
    }


@router.get("/catalog_grouped")
def cart_catalog_grouped(
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    indication: Optional[str] = Query(None),
    cell_type: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    verified_only: bool = Query(False),
) -> Dict[str, Any]:
    """
    Same filters as /catalog but returns items grouped by subcategory for hierarchical UI.
    """
    flat = cart_catalog(category=category, subcategory=subcategory, indication=indication,
                        cell_type=cell_type, tier=tier,
                        target=None, verified_only=verified_only)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in flat["items"]:
        sub = item.get("subcategory") or "Other"
        grouped.setdefault(sub, []).append(item)
    return {
        "count": flat["count"],
        "filters": flat["filters"],
        "subcategories": sorted(grouped.keys()),
        "by_subcategory": grouped,
    }


@router.get("/catalog")
def cart_catalog(
    category: Optional[str] = Query(None, description="Filter by canonical category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory (exact match)"),
    indication: Optional[str] = Query(None, description="Hematologic | Solid Tumor | Autoimmune | Research"),
    cell_type: Optional[str] = Query(None, description="CAR-T | CAR-NK | CAR-M | CAR-Treg | γδ T | iPSC-CAR | Universal"),
    tier: Optional[str] = Query(None, description="T1 | T2 | T3"),
    target: Optional[str] = Query(None, description="For Antigen Binder: target token substring (e.g. CD19, HER2)"),
    verified_only: bool = Query(True, description="Only return components with VERIFIED sequence"),
) -> Dict[str, Any]:
    """
    Browse the CAR-T component registry with rich filters.
    Returns id, name, tier, target, indications, cell_types, length, source/provenance.
    """
    elements = list(engine.registry.values())

    def matches(e: Dict[str, Any]) -> bool:
        if category and e.get("category") != category:
            return False
        if subcategory and e.get("subcategory") != subcategory:
            return False
        if tier and e.get("regulatory_tier") != tier:
            return False
        if verified_only and e.get("sequence_status") != "VERIFIED":
            return False
        uc = e.get("usage_context", {}) or {}
        if indication and indication not in (uc.get("indications") or []):
            return False
        if cell_type and cell_type not in (uc.get("cell_types") or []):
            return False
        if target:
            tgt = (e.get("target") or "").lower()
            if target.lower() not in tgt:
                return False
        return True

    items: List[Dict[str, Any]] = []
    for e in elements:
        if not matches(e):
            continue
        uc = e.get("usage_context", {}) or {}
        qa = e.get("qa", {}) or {}
        items.append({
            "id": e.get("id"),
            "name": e.get("name"),
            "category": e.get("category"),
            "subcategory": e.get("subcategory"),
            "tier": e.get("regulatory_tier"),
            "target": e.get("target") or "",
            "length": e.get("length"),
            "indications": uc.get("indications") or [],
            "cell_types": uc.get("cell_types") or [],
            "role": uc.get("role") or "",
            "approval_products": e.get("approval_products") or [],
            "clinical_trials": e.get("clinical_trials") or [],
            "source": qa.get("source") or "",
            "sequence_status": e.get("sequence_status"),
            "humanization_status": e.get("humanization_status") or "",
        })

    # Stable ordering: tier (T1 > T2 > T3) then name
    tier_rank = {"T1": 0, "T2": 1, "T3": 2}
    items.sort(key=lambda x: (tier_rank.get(x["tier"], 9), x["name"] or ""))

    return {
        "count": len(items),
        "filters": {
            "category": category, "indication": indication,
            "cell_type": cell_type, "tier": tier, "target": target,
            "verified_only": verified_only,
        },
        "items": items,
    }


@router.get("/component_sequence")
def cart_component_sequence(id: str = Query(..., description="Registry component ID")) -> Dict[str, Any]:
    """Return sequence payload for a single registry component ID."""
    e = engine.registry.get(id.lower())
    if not e:
        return {"found": False, "id": id, "message": "Component not found in CAR registry"}
    seq = e.get("sequence") or ""
    return {
        "found": True,
        "id": e.get("id"),
        "name": e.get("name"),
        "category": e.get("category"),
        "subcategory": e.get("subcategory"),
        "sequence_status": e.get("sequence_status"),
        "length": e.get("length") if e.get("length") is not None else len(seq),
        "sequence": seq,
    }
