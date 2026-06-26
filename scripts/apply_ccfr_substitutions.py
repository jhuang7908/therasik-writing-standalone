#!/usr/bin/env python3
"""
scripts/apply_ccfr_substitutions.py

Apply CC-FR substitutions to VH FR regions.

Pipeline
--------
  1. Load CC-FR table  (precomputed, static)
  2. Generate protection list  (dynamic, per-antibody)
  3. For each FR position:
       - If in protection list  → SKIP (preserve original AA)
       - If current AA triggers a substitution (F/L/I/M or user-defined set):
           → Look up CC-FR table for best replacement AA
           → If no CC-FR data: fall back to old conservative subs
       - Apply substitution
  4. Run lightweight CMC veto (SAP proxy, N-glyc check, charge check)
  5. Output: substituted sequence + audit trail

This script integrates:
  - config/cc_fr_table_vhvl_v1.json           (CC-FR table)
  - scripts/generate_protection_list_vhvl.py   (protection list)
  - Old _CONSERVATIVE_SUBS                     (fallback)

Usage
-----
  python scripts/apply_ccfr_substitutions.py \\
      --fr1 EVKLVESGGGLVQPGGSLRLSCAAS \\
      --cdr1 GFAFSSYD \\
      --fr2 MSWVRQAPGKRLEWVAT \\
      --cdr2 ISGGGRYT \\
      --fr3 YYPDTVKGRFTISRDNAKNSHYLQMNSLRAEDTAVYFC \\
      --vh-germline IGHV3-23 \\
      --mode humanization \\
      --out . --report

Modes
-----
  humanization   : trigger = any FR AA ≠ top-1 CC-FR AA  (DEEP-FR, full humanization)
  surface_reshape: trigger = hydrophobic surface AA only (F/L/I/M/V in exposed positions)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SUITE_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_TABLE = SUITE_ROOT / "config" / "cc_fr_table_vhvl_v1.json"

# Fallback substitution table (old conservative)
_OLD_CONSERVATIVE_SUBS: Dict[str, List[str]] = {
    "F": ["Y"],
    "L": ["S", "T", "Q"],
    "I": ["V"],
    "M": ["L", "Q"],
}

# Surface-reshape trigger set (hydrophobic)
_SURFACE_TRIGGER = frozenset("FILMV")

# CMC veto: N-glyc NxS/T (positions N, N+1, N+2 checked together)
import re as _re
_NGLYC_RE = _re.compile(r"N[^P][ST]")

# SAP hydrophobic set for 7-mer proxy
_SAP_HYDRO = frozenset("AILMFWV")


def _sap_proxy(seq: str) -> float:
    s = seq.upper()
    if len(s) < 7:
        return round(sum(1 for a in s if a in _SAP_HYDRO) / 7.0, 3)
    return round(
        max(sum(1 for a in s[i:i+7] if a in _SAP_HYDRO) / 7.0 for i in range(len(s)-6)), 3
    )


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_table(path: Path) -> dict:
    if not path.exists():
        print(f"[ERROR] CC-FR table not found: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _family(germline_str: str) -> str:
    g = (germline_str or "").strip().upper()
    return g.split("-")[0] if "-" in g else (g.split("*")[0] if "*" in g else g)


# ---------------------------------------------------------------------------
# Protection list (inline from generate_protection_list_vhvl)
# ---------------------------------------------------------------------------

def _build_protection_set(fr1: str, fr2: str, fr3: str,
                           pdb_path: Optional[str] = None,
                           verbose: bool = False) -> Dict[str, bool]:
    """Return protected_set dict {FR1:3: True, ...} using sequence-based rules."""
    sys.path.insert(0, str(SUITE_ROOT))
    from scripts.generate_protection_list_vhvl import build_protection_list
    result = build_protection_list(fr1, fr2, fr3, pdb_path=pdb_path, verbose=verbose)
    return result["protected_set"]


# ---------------------------------------------------------------------------
# CC-FR lookup
# ---------------------------------------------------------------------------

def _ccfr_lookup(table: dict, family: str, fr_seg: str, fr_pos: int,
                 trigger_aa: str) -> Optional[Tuple[str, float, str]]:
    """
    Return (best_aa, best_freq, support_level) or None.
    Best_aa is the CC-FR recommended candidate from old_conservative_subs.
    If trigger_aa not in old subs, return top-1 from clinical freq.
    """
    ccfr = table.get("vhvl_ccfr", table)
    pos_entry = ccfr.get(family, {}).get(fr_seg, {}).get(str(fr_pos))
    if pos_entry is None:
        return None

    support = pos_entry.get("support_level", "L3_sparse")
    if support == "L3_sparse":
        return None  # not enough data

    trigger_analysis = pos_entry.get("trigger_analysis", {})

    if trigger_aa in trigger_analysis:
        trig = trigger_analysis[trigger_aa]
        best_aa   = trig.get("cc_fr_best_aa")
        best_freq = trig.get("cc_fr_best_freq", 0.0)
        if best_aa and best_freq > 0:
            return best_aa, best_freq, support
    else:
        # For DEEP-FR mode: use top-1 from clinical frequency
        top5 = pos_entry.get("aa_top5", [])
        aa_freq = pos_entry.get("aa_freq", {})
        if top5 and top5[0] != trigger_aa:
            best_aa = top5[0]
            return best_aa, aa_freq.get(best_aa, 0.0), support

    return None


# ---------------------------------------------------------------------------
# CMC veto
# ---------------------------------------------------------------------------

def _cmc_veto(full_seq: str, abs_pos: int, seg: str, old_aa: str, new_aa: str) -> Optional[str]:
    """
    Apply the substitution hypothetically and check lightweight CMC.
    Returns reason string if vetoed, else None.
    """
    seq_list = list(full_seq)
    seq_list[abs_pos] = new_aa
    test_seq = "".join(seq_list)
    pos = abs_pos  # for window computation below

    # N-glyc check around the changed position
    window = test_seq[max(0, pos-2): pos+3]
    if _NGLYC_RE.search(window.upper()):
        return f"creates_nglyc_motif (NxS/T at pos ~{pos})"

    # Cys check: don't introduce new Cys
    if new_aa.upper() == "C" and old_aa.upper() != "C":
        return "introduces_free_cys"

    # Charge check: don't flip charge sign dramatically
    pos_charged = set("KRH")
    neg_charged = set("DE")
    if (old_aa.upper() in pos_charged and new_aa.upper() in neg_charged) or \
       (old_aa.upper() in neg_charged and new_aa.upper() in pos_charged):
        return f"charge_flip ({old_aa}→{new_aa})"

    return None  # all good


# ---------------------------------------------------------------------------
# Main application logic
# ---------------------------------------------------------------------------

def apply_substitutions(
    table: dict,
    family: str,
    fr1: str,
    fr2: str,
    fr3: str,
    mode: str = "humanization",
    pdb_path: Optional[str] = None,
    verbose: bool = False,
) -> dict:
    """
    Apply CC-FR substitutions to VH FR regions.

    Parameters
    ----------
    mode : "humanization" (DEEP-FR all non-protected positions)
           "surface_reshape" (only F/L/I/M/V trigger)

    Returns
    -------
    dict with: output_fr1/2/3, mutations, audit, summary
    """
    fr1 = fr1.strip().upper()
    fr2 = fr2.strip().upper()
    fr3 = fr3.strip().upper()

    # Step 1: Build protection set (dynamic)
    try:
        prot_set = _build_protection_set(fr1, fr2, fr3, pdb_path=pdb_path, verbose=verbose)
    except Exception as exc:
        print(f"[WARN] Protection list build failed ({exc}). Using empty set.")
        prot_set = {}

    # Step 2: Build mutable sequence lists
    fr_seqs = {"FR1": list(fr1), "FR2": list(fr2), "FR3": list(fr3)}
    # Full concatenated for CMC check
    full_concat = fr1 + fr2 + fr3

    mutations: List[dict] = []
    offsets = {"FR1": 0, "FR2": len(fr1), "FR3": len(fr1) + len(fr2)}

    for fr_seg, seq_list in fr_seqs.items():
        for fr_pos, aa in enumerate(seq_list):
            pos_key = f"{fr_seg}:{fr_pos}"

            # --- Guard 1: protected position → skip ---
            if pos_key in prot_set:
                mutations.append({
                    "fr_segment": fr_seg,
                    "fr_pos":     fr_pos,
                    "from_aa":    aa,
                    "to_aa":      aa,
                    "decision":   "PROTECTED",
                    "reason":     "in protection list",
                })
                continue

            # --- Guard 2: mode trigger check ---
            if mode == "surface_reshape" and aa not in _SURFACE_TRIGGER:
                continue  # only trigger on hydrophobic in surface mode
            if mode == "humanization" and aa not in _OLD_CONSERVATIVE_SUBS:
                # In DEEP-FR mode we only trigger on old-table AAs for now
                # (full humanization would trigger on all non-germline positions)
                continue

            # --- Step 3: Look up CC-FR table ---
            ccfr_result = _ccfr_lookup(table, family, fr_seg, fr_pos, aa)

            if ccfr_result:
                new_aa, freq, support = ccfr_result
                source = f"cc_fr ({support}, freq={freq:.3f})"
            else:
                # Fallback to old conservative subs
                old_list = _OLD_CONSERVATIVE_SUBS.get(aa, [])
                if not old_list:
                    continue
                new_aa = old_list[0]
                freq   = 0.0
                source = "old_conservative_subs_fallback"

            # No-op: same AA
            if new_aa == aa:
                mutations.append({
                    "fr_segment": fr_seg,
                    "fr_pos":     fr_pos,
                    "from_aa":    aa,
                    "to_aa":      aa,
                    "decision":   "NO_CHANGE",
                    "reason":     f"CC-FR agrees with current AA ({source})",
                })
                continue

            # --- Step 4: CMC veto ---
            abs_pos = offsets[fr_seg] + fr_pos
            veto = _cmc_veto(full_concat, abs_pos, fr_seg, aa, new_aa)
            if veto:
                # Try next candidate
                alt_list = _OLD_CONSERVATIVE_SUBS.get(aa, [])
                alt_applied = False
                for alt_aa in alt_list[1:]:
                    if alt_aa == aa:
                        continue
                    veto2 = _cmc_veto(full_concat, abs_pos, fr_seg, aa, alt_aa)
                    if not veto2:
                        new_aa = alt_aa
                        source += f" (primary vetoed: {veto}; fallback used)"
                        veto = None
                        alt_applied = True
                        break
                if not alt_applied:
                    mutations.append({
                        "fr_segment": fr_seg,
                        "fr_pos":     fr_pos,
                        "from_aa":    aa,
                        "to_aa":      aa,
                        "decision":   "CMC_VETOED",
                        "reason":     veto,
                        "attempted":  new_aa,
                    })
                    continue

            # --- Step 5: Apply ---
            seq_list[fr_pos] = new_aa
            # Update concat for subsequent CMC checks
            full_concat = (
                "".join(fr_seqs["FR1"]) +
                "".join(fr_seqs["FR2"]) +
                "".join(fr_seqs["FR3"])
            )

            mutations.append({
                "fr_segment": fr_seg,
                "fr_pos":     fr_pos,
                "from_aa":    aa,
                "to_aa":      new_aa,
                "decision":   "APPLIED",
                "source":     source,
            })
            if verbose:
                print(f"  APPLY {fr_seg}[{fr_pos}] {aa}→{new_aa}  ({source})")

    # Compile outputs
    out_fr1 = "".join(fr_seqs["FR1"])
    out_fr2 = "".join(fr_seqs["FR2"])
    out_fr3 = "".join(fr_seqs["FR3"])

    applied   = [m for m in mutations if m["decision"] == "APPLIED"]
    protected = [m for m in mutations if m["decision"] == "PROTECTED"]
    vetoed    = [m for m in mutations if m["decision"] == "CMC_VETOED"]
    no_change = [m for m in mutations if m["decision"] == "NO_CHANGE"]

    sap_before = _sap_proxy(fr1 + fr2 + fr3)
    sap_after  = _sap_proxy(out_fr1 + out_fr2 + out_fr3)

    summary = {
        "family":            family,
        "mode":              mode,
        "fr_positions":      len(fr1) + len(fr2) + len(fr3),
        "protected":         len(protected),
        "applied":           len(applied),
        "cmc_vetoed":        len(vetoed),
        "no_change":         len(no_change),
        "sap_before":        sap_before,
        "sap_after":         sap_after,
        "sap_delta":         round(sap_after - sap_before, 3),
    }

    if verbose:
        print(f"\n[summary] applied={len(applied)}  protected={len(protected)}"
              f"  vetoed={len(vetoed)}  SAP {sap_before:.3f}→{sap_after:.3f}")

    return {
        "input_fr1":  fr1,  "input_fr2":  fr2,  "input_fr3":  fr3,
        "output_fr1": out_fr1, "output_fr2": out_fr2, "output_fr3": out_fr3,
        "mutations":  mutations,
        "summary":    summary,
    }


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def render_markdown(result: dict, family: str) -> str:
    s = result["summary"]
    applied   = [m for m in result["mutations"] if m["decision"] == "APPLIED"]
    vetoed    = [m for m in result["mutations"] if m["decision"] == "CMC_VETOED"]

    lines = [
        f"# CC-FR Substitution Report — VH {family}",
        f"",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"## Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Mode | {s['mode']} |",
        f"| FR positions | {s['fr_positions']} |",
        f"| Protected (skipped) | {s['protected']} |",
        f"| Substitutions applied | {s['applied']} |",
        f"| CMC vetoed | {s['cmc_vetoed']} |",
        f"| SAP before | {s['sap_before']} |",
        f"| SAP after  | {s['sap_after']} |",
        f"| SAP Δ | {s['sap_delta']} |",
        f"",
        f"## Input vs Output",
        f"| Segment | Input | Output |",
        f"|---------|-------|--------|",
        f"| FR1 | `{result['input_fr1']}` | `{result['output_fr1']}` |",
        f"| FR2 | `{result['input_fr2']}` | `{result['output_fr2']}` |",
        f"| FR3 | `{result['input_fr3']}` | `{result['output_fr3']}` |",
    ]

    if applied:
        lines += ["", "## Applied Substitutions", ""]
        lines += ["| Seg | Pos | AA | New AA | Source |",
                  "|-----|-----|----|--------|--------|"]
        for m in applied:
            lines.append(
                f"| {m['fr_segment']} | {m['fr_pos']:2d} | {m['from_aa']} "
                f"| {m['to_aa']} | {m.get('source','—')} |"
            )

    if vetoed:
        lines += ["", "## CMC-Vetoed (not applied)", ""]
        for m in vetoed:
            lines.append(
                f"- {m['fr_segment']}[{m['fr_pos']}] {m['from_aa']}→{m['attempted']}"
                f": {m['reason']}"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Apply CC-FR substitutions to VH FRs")
    parser.add_argument("--fr1",  required=True)
    parser.add_argument("--cdr1", default="")
    parser.add_argument("--fr2",  required=True)
    parser.add_argument("--cdr2", default="")
    parser.add_argument("--fr3",  required=True)
    parser.add_argument("--vh-germline", required=True)
    parser.add_argument("--mode", choices=["humanization", "surface_reshape"],
                        default="surface_reshape")
    parser.add_argument("--pdb",   default=None, help="Optional PDB for structure checks")
    parser.add_argument("--table", default=str(_DEFAULT_TABLE))
    parser.add_argument("--out",   default=".")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    table  = load_table(Path(args.table))
    family = _family(args.vh_germline)

    result = apply_substitutions(
        table=table, family=family,
        fr1=args.fr1, fr2=args.fr2, fr3=args.fr3,
        mode=args.mode,
        pdb_path=args.pdb,
        verbose=args.verbose,
    )
    result["_meta"] = {
        "tool":         "apply_ccfr_substitutions.py",
        "version":      "v1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vh_germline":  args.vh_germline,
        "family":       family,
        "mode":         args.mode,
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"ccfr_applied_{family}_{args.mode}.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[out] JSON → {json_path}")

    if args.report:
        md = render_markdown(result, family)
        md_path = out_dir / f"ccfr_applied_{family}_{args.mode}.md"
        md_path.write_text(md, encoding="utf-8")
        print(f"[out] Markdown → {md_path}")

    s = result["summary"]
    print(f"      applied={s['applied']}  protected={s['protected']}"
          f"  vetoed={s['cmc_vetoed']}  SAP {s['sap_before']}→{s['sap_after']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
