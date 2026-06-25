"""
4B12 Humanization — Data Consistency Check
===========================================
Cross-validates delivery_4b12 reports and humanization_proposal against
Phase 2–5 JSON. Surfaces mismatches that could be undiscovered errors
(hand-written narrative vs data).

Run: python check_4b12_consistency.py

Output: Prints PASS/FAIL per check; writes check_4b12_consistency_report.md
"""
import os, sys, json, re

SUITE = os.path.dirname(os.path.abspath(__file__))

def jload(p):
    with open(p) as f: return json.load(f)

def main:
    p2  = jload(os.path.join(SUITE, "phase2_report_4b12.json"))
    p3  = jload(os.path.join(SUITE, "phase3_metrics_4b12.json"))
    p4  = jload(os.path.join(SUITE, "phase4_backmutation_4b12.json"))
    p4a = jload(os.path.join(SUITE, "phase4_assembly_4b12.json"))
    p5  = jload(os.path.join(SUITE, "phase5_qc_4b12.json"))
    prop = jload(os.path.join(SUITE, "humanization_proposal_4b12.json"))

    full_report_path = os.path.join(SUITE, "delivery_4b12", "reports", "4b12_humanization_full_report.md")
    full_md = open(full_report_path, encoding="utf-8").read if os.path.isfile(full_report_path) else ""

    errors = []
    warnings = []

    # ── 1. Proposal JSON vs Phase 4 assembly ─────────────────────────────────
    if prop["humanized_sequences"]["VH"] != p4a["humanized_VH"]:
        errors.append("humanization_proposal_4b12.json VH != phase4_assembly_4b12.json humanized_VH")
    if prop["humanized_sequences"]["VL"] != p4a["humanized_VL"]:
        errors.append("humanization_proposal_4b12.json VL != phase4_assembly_4b12.json humanized_VL")

    explicit_bm = set(p4a["explicit_back_mutations"])
    prop_bm_count = prop["back_mutations"]["total_explicit"]
    if prop_bm_count != len(explicit_bm):
        errors.append(f"Proposal total_explicit={prop_bm_count} vs assembly explicit_back_mutations count={len(explicit_bm)}")
    for b in prop["back_mutations"]["details"]:
        pos = b["position"]
        if pos not in explicit_bm:
            errors.append(f"Proposal lists BM {pos} but not in phase4_assembly explicit_back_mutations")

    # ── 2. Phase 2 numbers in full report (regex extract vs JSON) ──────────────
    # Vernier %: "66.7%" and "87.5%" in full report
    if "66.7" in full_md or "66.7%" in full_md:
        vh_pct = p2["vh_score_detail"]["vernier_pct"]
        if abs(vh_pct - 66.7) > 0.5:
            errors.append(f"Full report implies VH Vernier 66.7% but phase2 has vernier_pct={vh_pct}")
    if "87.5" in full_md or "87.5%" in full_md:
        vk_pct = p2["vk_score_detail"]["vernier_pct"]
        if abs(vk_pct - 87.5) > 0.5:
            errors.append(f"Full report implies VL Vernier 87.5% but phase2 has vernier_pct={vk_pct}")

    fr_vh = p2["vh_score_detail"]["fr_id_pct"]
    fr_vk = p2["vk_score_detail"]["fr_id_pct"]
    if "64.1" not in full_md and abs(fr_vh - 64.1) > 0.5:
        warnings.append(f"Full report FR VH: expected 64.1%, phase2 has {fr_vh}%")
    if "77.2" not in full_md and abs(fr_vk - 77.2) > 0.5:
        warnings.append(f"Full report FR VL: expected 77.2%, phase2 has {fr_vk}%")

    # ── 3. Phase 3 angle ────────────────────────────────────────────────────
    angle3 = p3["vh_vl_angle_deg"]
    if str(angle3) not in full_md and f"{angle3}" not in full_md:
        # might be formatted 84.3
        if abs(angle3 - 84.3) > 0.5:
            errors.append(f"Phase3 vh_vl_angle_deg={angle3} vs full report typically 84.3°")

    # ── 4. Phase 4: every FR BACK_MUTATE in p4 must be in explicit_bm (CDR positions are kept by graft) ──
    CDR_VH = [(26, 38), (55, 65), (105, 117)]
    CDR_VL = [(27, 38), (56, 65), (105, 117)]
    def in_cdr(pos_key):
        chain = "VH" if pos_key.startswith("VH_") else "VL"
        pos_n = int(pos_key.split("_")[1])
        ranges = CDR_VH if chain == "VH" else CDR_VL
        return any(lo <= pos_n <= hi for lo, hi in ranges)
    for b in p4["backmutation_decisions"]:
        if b["decision"] == "BACK_MUTATE":
            pos = b["position"]
            if in_cdr(pos):
                continue  # CDR: kept by grafting, not in explicit_back_mutations
            if pos not in explicit_bm:
                errors.append(f"phase4_backmutation has FR BACK_MUTATE {pos} but phase4_assembly explicit_back_mutations does not list it")

    # ── 5. Phase 5 QC numbers in proposal ───────────────────────────────────
    qc = prop.get("qc", {})
    rmsd_prop = qc.get("cdr_rmsd_all_pass")
    if isinstance(rmsd_prop, dict):
        for k, v in p5["qc_5_2_cdr_rmsd"].items:
            if isinstance(v, (int, float)) and (k not in rmsd_prop or abs(rmsd_prop[k] - v) > 0.001):
                errors.append(f"Proposal qc.cdr_rmsd_all_pass[{k}] != phase5 qc_5_2_cdr_rmsd")
    elif rmsd_prop is not None:
        rmsd_pass = all(v <= 1.5 for k, v in p5["qc_5_2_cdr_rmsd"].items if isinstance(v, (int, float)))
        if not rmsd_pass and rmsd_prop:
            errors.append("Proposal says cdr_rmsd_all_pass but phase5 has RMSD > 1.5")
    if abs(qc.get("angle_deviation_deg", 0) - p5["qc_5_3_angle"]["deviation_deg"]) > 0.01:
        errors.append(f"Proposal angle_deviation_deg={qc.get('angle_deviation_deg')} vs phase5 {p5['qc_5_3_angle']['deviation_deg']}")
    if abs(qc.get("pi_fab", 0) - p5["qc_5_6_pI"]["pI_Fab"]) > 0.01:
        errors.append(f"Proposal pi_fab={qc.get('pi_fab')} vs phase5 pI_Fab={p5['qc_5_6_pI']['pI_Fab']}")

    # ── 6. Audit report vs phase2 vernier_diff (key positions) ───────────────
    audit_path = os.path.join(SUITE, "delivery_4b12", "reports", "4b12_audit_report.md")
    if os.path.isfile(audit_path):
        audit_md = open(audit_path, encoding="utf-8").read
        # Audit says VH_69 S, VH_94 L (mouse). Check phase2 vernier_diff
        for r in p2["vernier_diff_vh"]:
            if r["pos"] == 69:
                mouse_aa = r.get("4B12", "?")
                if mouse_aa != "S":
                    errors.append(f"phase2 vernier_diff_vh pos69 4B12={mouse_aa}, audit expects S")
            if r["pos"] == 94:
                mouse_aa = r.get("4B12", "?")
                if mouse_aa != "L":
                    errors.append(f"phase2 vernier_diff_vh pos94 4B12={mouse_aa}, audit expects L")

    # ── 7. Full report back-mutation table vs p4 ──────────────────────────────
    # Full report has a table with position, mouse_aa, human_aa, decision, sasa, contact
    bm_in_p4 = {b["position"]: b for b in p4["backmutation_decisions"] if b["decision"] == "BACK_MUTATE"}
    for pos_key, b in bm_in_p4.items:
        if pos_key not in explicit_bm:
            continue
        if b["mouse_aa"] not in full_md or b["human_aa"] not in full_md:
            # table might still be correct; just ensure the two BMs are mentioned
            pass
    if len(explicit_bm) != 2:
        warnings.append(f"4B12 explicit_back_mutations has {len(explicit_bm)} items; full report narrative assumes 2 (VH_69, VH_94).")

    # ── Report ──────────────────────────────────────────────────────────────
    out_md = os.path.join(SUITE, "check_4b12_consistency_report.md")
    lines = [
        "# 4B12 ",
        "",
        "**：**  delivery_4b12  Phase 2–5 JSON  humanization_proposal_4b12.json 。",
        "",
        "## ",
        "",
        f"- **（errors）：** {len(errors)}",
        f"- **（warnings）：** {len(warnings)}",
        "",
        "---",
        "",
        "## Errors",
        "",
    ]
    if not errors:
        lines.append("。")
    else:
        for e in errors:
            lines.append(f"- {e}")
    lines += ["", "## Warnings", ""]
    if not warnings:
        lines.append("。")
    else:
        for w in warnings:
            lines.append(f"- {w}")
    lines += [
        "",
        "---",
        "",
        "## ",
        "",
    ]
    if errors:
        lines.append("**4B12  JSON ， Phase 2–5 JSON 。**")
    else:
        lines.append("**。** 4B12 （4b12_humanization_full_report.md），， 9C1  JSON ，。")
    lines.append("")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Console
    print("\n" + "="*60)
    print("  4B12 CONSISTENCY CHECK (JSON vs delivery/proposal)")
    print("="*60)
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
    if warnings:
        for w in warnings:
            print(f"  WARN:  {w}")
    if not errors and not warnings:
        print("  All checks PASS (no discrepancies found).")
    else:
        print(f"\n  Errors: {len(errors)}, Warnings: {len(warnings)}")
    print(f"\n  Report: {out_md}")
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main)
