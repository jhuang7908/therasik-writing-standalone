#!/usr/bin/env python3
"""
build_dog_production_germline_library_v1.py
===========================================

Build a small, production-oriented dog (Canis lupus familiaris) germline scaffold library (v1)
anchored on the *clinical canine antibodies available inside this repo*.

Inputs (repo-internal):
  - Clinical reference PDBs (VH/VL):
      - projects/Llama_Humanization_Project/semi_auto_workflow/inputs/Bedinvetmab.pdb
      - projects/Llama_Humanization_Project/semi_auto_workflow/inputs/Lokivetmab.pdb
      - data/structures/engineered/Landogrozumab.pdb
  - Dog IMGT germline amino-acid catalogs:
      - data/germlines/canis_lupus_familiaris_ig_aa/{IGHV,IGKV,IGLV,IGHJ,IGKJ,IGLJ}_aa.json

Outputs:
  - data/germlines/canis_lupus_familiaris_ig_aa/dog_production_germline_library_v1.json
  - data/germlines/canis_lupus_familiaris_ig_aa/dog_production_germline_library_v1.md

Notes:
  - This is an engineering-oriented scaffold list. With sparse canine therapeutics, we anchor
    on the in-repo clinical references and IMGT "functional" annotations, rather than trying
    to infer population frequencies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SUITE))


from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys  # noqa: E402


AA3_TO_1 = {
    "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
    "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
    "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
    "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y",
    "MSE": "M",  # selenomethionine
}


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return _load_json(path)
    except Exception:
        return {}
    return {}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _pdb_chain_sequence(pdb_path: Path, chain_id: str) -> str:
    """
    Extract 1-letter sequence for a chain from ATOM records.
    Non-standard residues are skipped (not converted to X) to avoid inflating lengths.
    """
    residues: Dict[Tuple[int, str], str] = {}

    with open(pdb_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.startswith("ATOM"):
                continue
            if len(line) < 27:
                continue
            ch = line[21].strip()
            if ch != chain_id:
                continue
            resname = line[17:20].strip().upper()
            if resname not in AA3_TO_1:
                continue
            try:
                resseq = int(line[22:26].strip())
            except Exception:
                continue
            icode = (line[26] or "").strip()
            key = (resseq, icode)
            # keep first seen residue at that index
            residues.setdefault(key, resname)

    if not residues:
        return ""
    keys = sorted(residues.keys(), key=lambda x: (x[0], x[1]))
    return "".join(AA3_TO_1[residues[k]] for k in keys)


def _v_region_like(annotation) -> str:
    raise NotImplementedError


def _best_v_gene(v_region: str, v_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    raise NotImplementedError


def _functional_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for e in entries:
        hdr = str(e.get("raw_header") or "")
        # IMGT header field 4 is functionality: F/P/ORF in the examples
        # We treat "|F|" as functional.
        if "|F|" in hdr:
            out.append(e)
    return out


def _prefix_identity(a: str, b: str, n: int = 80) -> float:
    """
    Cheap prefilter score: identity over N-terminal prefix.
    """
    a = str(a or "").strip().upper()
    b = str(b or "").strip().upper()
    if not a or not b:
        return 0.0
    n0 = min(int(n), len(a), len(b))
    if n0 <= 0:
        return 0.0
    matches = sum(1 for i in range(n0) if a[i] == b[i])
    return matches / n0


def _topk_by_prefix_identity(query_seq: str, entries: List[Dict[str, Any]], k: int = 40, n: int = 80) -> List[Dict[str, Any]]:
    """
    Return top-k catalog entries by cheap prefix identity, to avoid Kabat numbering on the full catalog.
    """
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for e in entries:
        seq = str(e.get("sequence_aa") or "")
        scored.append((_prefix_identity(query_seq, seq, n=n), e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[: max(1, int(k))]]


def _best_light_v_gene(v_region: str, igkv: List[Dict[str, Any]], iglv: List[Dict[str, Any]]) -> Dict[str, Any]:
    b_k = _best_v_gene_fr_only(v_region, igkv, chain="VL")
    b_l = _best_v_gene_fr_only(v_region, iglv, chain="VL")
    if (b_k.get("identity") or 0.0) >= (b_l.get("identity") or 0.0):
        return {**b_k, "locus": "IGK"}
    return {**b_l, "locus": "IGL"}


def _longest_common_suffix(a: str, b: str, min_k: int = 4) -> Tuple[int, str]:
    a = str(a or "").upper()
    b = str(b or "").upper()
    m = min(len(a), len(b))
    best_k = 0
    for k in range(m, min_k - 1, -1):
        if a[-k:] == b[-k:]:
            best_k = k
            break
    return best_k, (a[-best_k:] if best_k > 0 else "")


def _best_j_gene(fr4: str, j_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Best-effort J match by longest suffix overlap between antibody FR4 and J catalog.
    Returns: gene, overlap_len, overlap_seq.
    """
    fr4 = str(fr4 or "")
    best = {"gene": None, "overlap_len": 0, "overlap_seq": None, "catalog_aa": None, "raw_header": None}
    if not fr4:
        return best
    for e in j_entries:
        gene = e.get("id")
        cat = str(e.get("sequence_aa") or "")
        if not gene or not cat:
            continue
        k, suf = _longest_common_suffix(fr4, cat, min_k=4)
        if k > best["overlap_len"]:
            best = {
                "gene": gene,
                "overlap_len": int(k),
                "overlap_seq": suf or None,
                "catalog_aa": cat,
                "raw_header": e.get("raw_header"),
            }
    return best


def _kabat_fr4_tail(seq: str, n: int = 12) -> str:
    """
    Best-effort: extract the last N residues of the numbered variable domain (FR4 side)
    using Kabat numbering. Falls back to raw sequence tail if numbering fails.
    """
    try:
        kd = get_kabat_numbering(seq)
        if not kd:
            return seq[-n:]
        keys = sorted_keys(kd)
        tail_keys = keys[-n:] if len(keys) >= n else keys
        return "".join(kd[k] for k in tail_keys)
    except Exception:
        return seq[-n:]


def _v_prefix_for_match(seq: str, min_len: int = 40) -> str:
    """
    For IMGT V-REGION catalogs (often truncated before FR4), a robust baseline is to
    compare the *N-terminal prefix* of the chain sequence.
    """
    s = str(seq or "")
    return s if len(s) >= min_len else s


def _fr_positions(chain: str) -> List[Tuple[int, int]]:
    """
    Approximate Kabat FR ranges for FR-only identity.
    (We intentionally avoid CDR ranges to prevent germline assignment being dominated by CDR diversity.)
    """
    if chain == "VH":
        return [(1, 25), (36, 49), (66, 94)]
    # VL (kappa/lambda share similar Kabat FR bounds for this purpose)
    return [(1, 23), (35, 49), (57, 88)]


def _is_fr_key(k: Tuple[int, str], chain: str) -> bool:
    pos, ins = k
    if ins not in ("", " "):
        # keep base keys only for robust comparison
        return False
    for lo, hi in _fr_positions(chain):
        if lo <= pos <= hi:
            return True
    return False


def _best_v_gene_fr_only(query_seq: str, v_entries: List[Dict[str, Any]], chain: str) -> Dict[str, Any]:
    """
    Choose best V gene by FR-only Kabat-position identity.

    Returns:
      gene, identity, n_compared, catalog_aa, raw_header
    """
    best = {"gene": None, "identity": 0.0, "n_compared": 0, "catalog_aa": None, "raw_header": None}
    kd_q = get_kabat_numbering(query_seq)
    if not kd_q:
        return best

    fr_q = {k: kd_q[k] for k in kd_q if _is_fr_key(k, chain=chain)}
    if len(fr_q) < 25:
        return best

    for e in v_entries:
        gene = e.get("id")
        cat = str(e.get("sequence_aa") or "")
        if not gene or not cat:
            continue
        kd_c = get_kabat_numbering(cat)
        if not kd_c:
            continue

        fr_c = {k: kd_c[k] for k in kd_c if _is_fr_key(k, chain=chain)}
        keys = sorted(set(fr_q.keys()) & set(fr_c.keys()))
        if len(keys) < 25:
            continue
        matches = sum(1 for k in keys if fr_q[k] == fr_c[k])
        ident = matches / max(1, len(keys))
        if ident > best["identity"]:
            best = {
                "gene": gene,
                "identity": float(round(ident, 4)),
                "n_compared": int(len(keys)),
                "catalog_aa": cat,
                "raw_header": e.get("raw_header"),
            }
    return best


@dataclass
class ClinicalRef:
    name: str
    pdb_path: Path
    vh_chain: str = "H"
    vl_chain: str = "L"


def main() -> int:
    refs = [
        ClinicalRef(
            name="Bedinvetmab",
            pdb_path=SUITE / "projects" / "Llama_Humanization_Project" / "semi_auto_workflow" / "inputs" / "Bedinvetmab.pdb",
        ),
        ClinicalRef(
            name="Lokivetmab",
            pdb_path=SUITE / "projects" / "Llama_Humanization_Project" / "semi_auto_workflow" / "inputs" / "Lokivetmab.pdb",
        ),
        ClinicalRef(
            name="Landogrozumab",
            pdb_path=SUITE / "data" / "structures" / "engineered" / "Landogrozumab.pdb",
        ),
    ]

    dog_dir = SUITE / "data" / "germlines" / "canis_lupus_familiaris_ig_aa"
    pop_stats_path = dog_dir / "dog_repertoire_and_dla_stats.json"
    pop_stats = _load_optional_json(pop_stats_path)
    ig_hv = _load_json(dog_dir / "IGHV_aa.json")["entries"]
    ig_kv = _load_json(dog_dir / "IGKV_aa.json")["entries"]
    ig_lv = _load_json(dog_dir / "IGLV_aa.json")["entries"]
    ig_hj = _load_json(dog_dir / "IGHJ_aa.json")["entries"]
    ig_kj = _load_json(dog_dir / "IGKJ_aa.json")["entries"]
    ig_lj = _load_json(dog_dir / "IGLJ_aa.json")["entries"]

    ig_hv_f = _functional_entries(ig_hv)
    ig_kv_f = _functional_entries(ig_kv)
    ig_lv_f = _functional_entries(ig_lv)
    ig_hj_f = _functional_entries(ig_hj)
    ig_kj_f = _functional_entries(ig_kj)
    ig_lj_f = _functional_entries(ig_lj)

    inference_params = {
        "v_prefilter": {
            "method": "prefix_identity_topk_then_kabat_fr_only",
            "top_k_prefix": 60,
            "top_k_kabat": 3,
            "prefix_len": 80,
        },
        "j_match": {
            "entries": "IMGT functional only",
            "method": "longest_common_suffix",
            "min_suffix_len": 4,
            "fr4_tail_len": 12,
        },
    }

    clinical_records: List[Dict[str, Any]] = []
    v_hits_h: Dict[str, Dict[str, Any]] = {}
    v_hits_l: Dict[str, Dict[str, Any]] = {}

    for ref in refs:
        if not ref.pdb_path.exists():
            raise FileNotFoundError(f"Missing clinical reference PDB: {ref.pdb_path}")

        vh_seq = _pdb_chain_sequence(ref.pdb_path, ref.vh_chain)
        vl_seq = _pdb_chain_sequence(ref.pdb_path, ref.vl_chain)
        if not vh_seq or not vl_seq:
            raise RuntimeError(f"Failed to extract VH/VL sequences from {ref.pdb_path} (chains {ref.vh_chain}/{ref.vl_chain})")

        v_like_h = _v_prefix_for_match(vh_seq)
        v_like_l = _v_prefix_for_match(vl_seq)

        hv_candidates = _topk_by_prefix_identity(
            v_like_h,
            ig_hv_f,
            k=inference_params["v_prefilter"]["top_k_prefix"],
            n=inference_params["v_prefilter"]["prefix_len"],
        )
        kv_candidates = _topk_by_prefix_identity(
            v_like_l,
            ig_kv_f,
            k=inference_params["v_prefilter"]["top_k_prefix"],
            n=inference_params["v_prefilter"]["prefix_len"],
        )
        lv_candidates = _topk_by_prefix_identity(
            v_like_l,
            ig_lv_f,
            k=inference_params["v_prefilter"]["top_k_prefix"],
            n=inference_params["v_prefilter"]["prefix_len"],
        )

        hv_kabat = hv_candidates[: inference_params["v_prefilter"]["top_k_kabat"]]
        kv_kabat = kv_candidates[: inference_params["v_prefilter"]["top_k_kabat"]]
        lv_kabat = lv_candidates[: inference_params["v_prefilter"]["top_k_kabat"]]

        best_hv = _best_v_gene_fr_only(v_like_h, hv_kabat, chain="VH")
        best_lv = _best_light_v_gene(v_like_l, kv_kabat, lv_kabat)

        fr4_h = _kabat_fr4_tail(vh_seq, n=inference_params["j_match"]["fr4_tail_len"])
        fr4_l = _kabat_fr4_tail(vl_seq, n=inference_params["j_match"]["fr4_tail_len"])

        best_hj = _best_j_gene(fr4_h, ig_hj_f)
        if best_lv.get("locus") == "IGK":
            best_lj = _best_j_gene(fr4_l, ig_kj_f)
        else:
            best_lj = _best_j_gene(fr4_l, ig_lj_f)

        if best_hv.get("gene"):
            v_hits_h.setdefault(best_hv["gene"], {"gene": best_hv["gene"], "seen_in": [], "best_identity": best_hv["identity"]})
            v_hits_h[best_hv["gene"]]["seen_in"].append(ref.name)
            v_hits_h[best_hv["gene"]]["best_identity"] = max(v_hits_h[best_hv["gene"]]["best_identity"], best_hv["identity"])

        if best_lv.get("gene"):
            key = f'{best_lv.get("locus")}:{best_lv["gene"]}'
            v_hits_l.setdefault(key, {"locus": best_lv.get("locus"), "gene": best_lv["gene"], "seen_in": [], "best_identity": best_lv["identity"]})
            v_hits_l[key]["seen_in"].append(ref.name)
            v_hits_l[key]["best_identity"] = max(v_hits_l[key]["best_identity"], best_lv["identity"])

        clinical_records.append({
            "name": ref.name,
            "pdb_path": str(ref.pdb_path.relative_to(SUITE)) if ref.pdb_path.is_relative_to(SUITE) else str(ref.pdb_path),
            "chains": {"VH": ref.vh_chain, "VL": ref.vl_chain},
            "extracted_sequences": {"VH": vh_seq, "VL": vl_seq},
            "kabat_fr4_tail_best_effort": {
                "VH": fr4_h,
                "VL": fr4_l,
            },
            "inferred_germline": {
                "VH_V_gene": best_hv,
                "VH_J_gene_best_effort": best_hj,
                "VL_V_gene": best_lv,
                "VL_J_gene_best_effort": best_lj,
            },
            "inference_parameters": inference_params,
        })

    # Build the small v1 scaffold list from V genes observed in clinical references
    hv_scaffolds = sorted(v_hits_h.values(), key=lambda x: float(x.get("best_identity") or 0.0), reverse=True)
    lv_scaffolds = sorted(v_hits_l.values(), key=lambda x: float(x.get("best_identity") or 0.0), reverse=True)

    payload = {
        "library_id": "dog_production_germline_library_v1",
        "species": "Canis_lupus_familiaris",
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": {
            "clinical_refs_in_repo": [r["name"] for r in clinical_records],
            "clinical_ref_pdbs": [r["pdb_path"] for r in clinical_records],
            "imgt_germline_catalog_dir": str(dog_dir.relative_to(SUITE)),
            "population_stats_file": (
                str(pop_stats_path.relative_to(SUITE)) if pop_stats else None
            ),
            "population_stats_meta": (pop_stats.get("meta") or {}) if pop_stats else {},
        },
        "inference_parameters": inference_params,
        "population_support": {
            "vh_gene_usage": (pop_stats.get("vh_gene_usage") or {}) if pop_stats else {},
            "dla_core_panel": (pop_stats.get("dla_core_panel") or {}) if pop_stats else {},
        },
        "clinical_reference_records": clinical_records,
        "production_scaffolds_vh_v": hv_scaffolds,
        "production_scaffolds_vl_v": lv_scaffolds,
        "policy_notes": [
            "This v1 library is anchored on in-repo clinical canine antibodies + IMGT functional annotation, not population frequencies.",
            "If population-level repertoire / DLA frequency priors are available, they are recorded under sources.population_stats_file and payload.population_support.",
            "Use-case: choose a small set of production-capable dog V-gene scaffolds for caninization / surface reshaping workflows.",
            "J-gene mapping is best-effort because IMGT J-REGION translations may not align 1:1 with FR4 definitions in every pipeline.",
        ],
    }

    out_json = dog_dir / "dog_production_germline_library_v1.json"
    _write_json(out_json, payload)

    # Render a short, human-readable MD summary
    md: List[str] = []
    md.append("# Dog production germline library (v1)")
    md.append("")
    md.append(f"- Built at: `{payload['built_at']}`")
    md.append(f"- Species: `{payload['species']}`")
    md.append("")
    if payload.get("sources", {}).get("population_stats_file"):
        md.append("## Population priors (repertoire / DLA)")
        md.append("")
        md.append(f"- Stats file: `{payload['sources']['population_stats_file']}`")
        meta = payload.get("sources", {}).get("population_stats_meta") or {}
        if meta:
            md.append(f"- Stats meta: `{json.dumps(meta, ensure_ascii=False)}`")
        md.append("")
    md.append("## Clinical canine reference antibodies (repo-internal)")
    md.append("")
    md.append("| name | pdb | inferred VH V | id% | inferred VL V | locus | id% |")
    md.append("|---|---|---|---:|---|---|---:|")
    for r in clinical_records:
        hv = (r.get("inferred_germline") or {}).get("VH_V_gene") or {}
        lv = (r.get("inferred_germline") or {}).get("VL_V_gene") or {}
        md.append("| {name} | `{pdb}` | `{hv}` | {hi:.3f} | `{lv}` | {loc} | {li:.3f} |".format(
            name=r.get("name"),
            pdb=r.get("pdb_path"),
            hv=hv.get("gene") or "—",
            hi=float(hv.get("identity") or 0.0),
            lv=lv.get("gene") or "—",
            loc=lv.get("locus") or "—",
            li=float(lv.get("identity") or 0.0),
        ))
    md.append("")
    md.append("## Production-capable V-gene scaffolds (derived from above)")
    md.append("")
    md.append("### VH V genes")
    md.append("")
    md.append("| gene | best_identity | seen_in |")
    md.append("|---|---:|---|")
    for it in hv_scaffolds:
        md.append("| `{g}` | {i:.3f} | {s} |".format(
            g=it.get("gene"),
            i=float(it.get("best_identity") or 0.0),
            s=", ".join(it.get("seen_in") or []),
        ))
    md.append("")
    md.append("### VL V genes")
    md.append("")
    md.append("| locus | gene | best_identity | seen_in |")
    md.append("|---|---|---:|---|")
    for it in lv_scaffolds:
        md.append("| {loc} | `{g}` | {i:.3f} | {s} |".format(
            loc=it.get("locus"),
            g=it.get("gene"),
            i=float(it.get("best_identity") or 0.0),
            s=", ".join(it.get("seen_in") or []),
        ))
    md.append("")
    md.append("## Notes")
    md.append("")
    for n in payload["policy_notes"]:
        md.append(f"- {n}")
    md.append("")

    out_md = dog_dir / "dog_production_germline_library_v1.md"
    _write_text(out_md, "\n".join(md))

    print(f"[OK] wrote: {out_json}")
    print(f"[OK] wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

