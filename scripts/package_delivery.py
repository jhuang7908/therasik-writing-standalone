"""
InSynBio 
===========================
、、，
 README.md  ZIP 。

【 vs 】
  （ delivery_zip）:
    - {id}_Client_zh.pdf       （）
    - {id}_Client_en.pdf       （，）
    - {id}_sequences.fasta     
    - {id}_mouse.pdb           
    - {id}_humanized_final.pdb （）
    - README.md                

【humanized_final  — 】
  -  vernier_round2  PASS → final = vernier_round2 PDB
    （ SSOT  sequence_annotation  vernier_round2，）
  -  → final = v3/v2/v1  final_version 

  （）:
    - {id}_V44_Audit.md/pdf    QA 
    - {id}_results.json        
    - {id}_Dev_Report.md       
    - *_reeval_report.json     

:
    python scripts/package_delivery.py <antibody_id> <project_dir> [--zip]

:
    python scripts/package_delivery.py 9c1 projects/9c1_Redesign
    python scripts/package_delivery.py 9c1 projects/9c1_Redesign --zip
"""

import sys
import shutil
import json
import zipfile
import time
from pathlib import Path
from datetime import datetime

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))


def _find_file(candidates: list) -> Path:
    for c in candidates:
        c = Path(c)
        if c.exists():
            return c
    return None


def _rglob_first(base: Path, patterns: list[str]) -> Path:
    """Return first match of any filename pattern under base, else None."""
    try:
        for pat in patterns:
            for p in base.rglob(pat):
                if p.is_file():
                    return p
    except Exception:
        return None
    return None


def _safe_copy(src: Path, dst: Path):
    """，src == dst 。"""
    if src and src.exists():
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
        return True
    return False


def package_delivery(antibody_id: str, project_dir: Path, make_zip: bool = False) -> Path:
    """
    。

    （）:
        delivery_{id}/
        ├── README.md
        ├── reports/
        │   ├── {id}_Client_zh.pdf       — （）
        │   └── {id}_Client_en.pdf       — （，）
        ├── sequences/
        │   └── {id}_sequences.fasta
        └── structures/
            ├── {id}_mouse.pdb
            └── {id}_humanized_final.pdb

    （ projects/ ，）:
        - {id}_V44_Audit.md / .pdf
        - {id}_results.json
        - {id}_Dev_Report.md
    """
    project_dir  = Path(project_dir)
    final_dir = SUITE / f"delivery_{antibody_id}"
    build_dir = SUITE / f"delivery_{antibody_id}__build"

    # SECURITY + WINDOWS ROBUSTNESS:
    # Build into a fresh directory, then swap into final_dir when possible.
    # This prevents historical/internal file leakage AND avoids hard failure
    # when a PDF in final_dir is locked/opened by another process.
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)
    (build_dir / "reports").mkdir(parents=True, exist_ok=True)
    (build_dir / "sequences").mkdir(parents=True, exist_ok=True)
    (build_dir / "structures").mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  : {antibody_id.upper()}")
    print(f"  : {build_dir.relative_to(SUITE)}")
    print(f"{'='*60}")

    delivered = []
    missing   = []

    def add(src_candidates: list, dst: Path, label: str, required: bool = True):
        src = _find_file(src_candidates)
        if _safe_copy(src, dst):
            delivered.append(f"  ✓ [{label}]  {dst.relative_to(SUITE)}")
        elif required:
            missing.append(f"  ✗ [{label}]   — : {[str(c) for c in src_candidates]}")

    # ── Pre-step: ensure standard reports exist (best-effort) ─────────────────
    # If project has {id}_results.json (single source of truth), try to render
    # standardized client report MD and generate PDF when missing.
    results_json = project_dir / f"{antibody_id}_results.json"
    reports_dir = project_dir / "reports"
    client_md = reports_dir / f"{antibody_id}_Client_zh.md"
    client_pdf = reports_dir / f"{antibody_id}_Client_zh.pdf"
    audit_md = reports_dir / f"{antibody_id}_V44_Audit.md"
    audit_pdf = reports_dir / f"{antibody_id}_V44_Audit.pdf"

    pre_step_rendered_pdf = False
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        if results_json.exists():
            from scripts.render_vhvl_v44_reports import render_client_zh, run_pre_delivery_gate_report_checks
            standard_path = SUITE / "config" / "vh_vl_humanization_v44.json"
            if standard_path.exists():
                result_obj = json.loads(results_json.read_text(encoding="utf-8"))
                standard_obj = json.loads(standard_path.read_text(encoding="utf-8"))
                result_obj["_render_project_dir"] = str(project_dir.resolve())
                md_text = render_client_zh(result_obj, standard_obj)
                fails = run_pre_delivery_gate_report_checks(result_obj, md_text)
                if fails:
                    raise ValueError("Pre-Delivery Gate failed: " + "; ".join(fails))
                client_md.write_text(md_text, encoding="utf-8")
                print(f"  ✓  MD : {client_md}")
            # Regenerate PDF when MD exists (always refresh on package)
            if client_md.exists():
                try:
                    from scripts.md_to_pdf import render_pdf
                    render_pdf(str(client_md), str(client_pdf))
                    pre_step_rendered_pdf = True
                except Exception as e:
                    print(f"  [WARN]  PDF : {e}")
        if audit_md.exists() and not audit_pdf.exists():
            from scripts.md_to_pdf import render_pdf
            render_pdf(str(audit_md), str(audit_pdf))
    except Exception as e:
        print(f"  [WARN] （）: {e}")

    # ── （）PDF ──────────────────────────────────────────────────
    #  run  canonical PDF； Windows  _new 
    add([
        project_dir / "reports" / f"{antibody_id}_Client_zh.pdf",
        project_dir / "reports" / f"{antibody_id}_Client_zh__new.pdf",
        project_dir / "reports" / f"{antibody_id}_Client_zh_new.pdf",
        project_dir / f"{antibody_id}_Client_zh.pdf",
    ], build_dir / "reports" / f"{antibody_id}_Client_zh.pdf",
       " PDF（）", required=True)

    # ： run  PDF， PDF （）
    if pre_step_rendered_pdf:
        delivered_pdf = build_dir / "reports" / f"{antibody_id}_Client_zh.pdf"
        if delivered_pdf.exists():
            age_s = time.time() - delivered_pdf.stat().st_mtime
            if age_s > 120:
                print(f"  [WARN]  PDF （{age_s:.0f}s ），，")

    # ── （）PDF —  ──────────────────────────────────────────
    add([
        project_dir / "reports" / f"{antibody_id}_Client_en.pdf",
        project_dir / f"{antibody_id}_Client_en.pdf",
    ], build_dir / "reports" / f"{antibody_id}_Client_en.pdf",
       " PDF（）", required=False)

    # ──  FASTA ───────────────────────────────────────────────────────────
    add([
        project_dir / f"{antibody_id}_sequences.fasta",
        project_dir / "sequences" / f"{antibody_id}_sequences.fasta",
    ], build_dir / "sequences" / f"{antibody_id}_sequences.fasta",
       " FASTA", required=True)

    # ──  PDB ─────────────────────────────────────────────────────
    mouse_src = _find_file([
        project_dir / "structures" / f"{antibody_id}_mouse.pdb",
        project_dir / f"{antibody_id}_mouse.pdb",
    ]) or _rglob_first(project_dir, [f"{antibody_id}_mouse.pdb", f"*{antibody_id}*mouse*.pdb"])
    if mouse_src is None:
        mouse_src = _find_file([
            final_dir / "structures" / f"{antibody_id}_mouse.pdb",
        ])
    if _safe_copy(mouse_src, build_dir / "structures" / f"{antibody_id}_mouse.pdb"):
        delivered.append(f"  ✓ [ PDB]  {(build_dir / 'structures' / f'{antibody_id}_mouse.pdb').relative_to(SUITE)}")
    else:
        missing.append(f"  ✗ [ PDB]  ")

    # ──  PDB ───────────────────────────────────────────────────
    # RULE: humanized_final MUST match report SSOT. When vernier_round2 exists (structure PASS),
    #       final = vernier_round2 PDB. Otherwise final = v3/v2/v1 by final_version.
    meta0 = {}
    if results_json.exists():
        try:
            meta0 = json.loads(results_json.read_text(encoding="utf-8"))
        except Exception:
            meta0 = {}
    seqs = meta0.get("sequences") or {}
    struct_info = meta0.get("structure") or {}
    internal = meta0.get("_internal") or {}

    # Priority 1: vernier_round2 exists and passed structure → final = vernier_round2 PDB
    final_src = None
    for ev_key in ("evaluation_v3_vernier_round2", "evaluation_v2_vernier_round2", "evaluation_v1_vernier_round2"):
        ev = internal.get(ev_key) if isinstance(internal, dict) else None
        if not isinstance(ev, dict):
            continue
        note = (ev.get("_internal_note") or {}).get("vernier_round2") if isinstance(ev.get("_internal_note"), dict) else {}
        if not isinstance(note, dict):
            continue
        if not (seqs.get("vernier_round2_VH") and seqs.get("vernier_round2_VL")):
            continue
        attempts = note.get("attempts") or []
        passed = any(isinstance(a, dict) and a.get("pass") for a in attempts)
        if not passed:
            continue
        vr2_pdb = struct_info.get("vernier_round2_pdb")
        if vr2_pdb:
            vr2_path = Path(str(vr2_pdb).replace("\\", "/"))
            for base in (SUITE, project_dir):
                p = base / vr2_path if not vr2_path.is_absolute() else vr2_path
                if p.exists():
                    final_src = p
                    break
        if final_src is None:
            final_src = _rglob_first(project_dir, [
                f"{antibody_id}_humanized_*_vernier_round2*.pdb",
                f"{antibody_id}_humanized*vernier*.pdb",
            ])
        if final_src:
            break

    # Priority 2: fallback to v3/v2/v1 by final_version
    if final_src is None:
        final_version0 = (meta0.get("_meta", {}) or {}).get("final_version", "") or ""
        if final_version0 not in ("v1", "v2", "v3"):
            final_version0 = ""
        ver_order = [final_version0] if final_version0 else []
        for v in ("v3", "v2", "v1"):
            if v not in ver_order:
                ver_order.append(v)
        candidates = []
        for v in ver_order:
            candidates.append(project_dir / "structures" / f"{antibody_id}_humanized_{v}.pdb")
            candidates.append(project_dir / f"{antibody_id}_humanized_{v}.pdb")
        candidates += [
            project_dir / "structures" / f"{antibody_id}_humanized.pdb",
            project_dir / f"{antibody_id}_humanized.pdb",
        ]
        final_src = _find_file(candidates)
    if final_src is None:
        # Prefer final_version first, else highest versioned humanized PDB under project_dir
        pats = []
        if final_version0:
            pats.append(f"{antibody_id}_humanized_{final_version0}.pdb")
        pats += [
            f"{antibody_id}_humanized_v3.pdb",
            f"{antibody_id}_humanized_v2.pdb",
            f"{antibody_id}_humanized_v1.pdb",
            f"{antibody_id}_humanized_v*.pdb",
            f"{antibody_id}_humanized*.pdb",
            f"*{antibody_id}*humanized*.pdb",
        ]
        final_src = _rglob_first(project_dir, pats)
    if final_src is None:
        final_src = _find_file([
            final_dir / "structures" / f"{antibody_id}_humanized.pdb",
        ])
    final_dst = build_dir / "structures" / f"{antibody_id}_humanized_final.pdb"
    # ： vernier_round2  SSOT ，final  vernier_round2（）
    _vr2_passed = False
    for _k in ("evaluation_v3_vernier_round2", "evaluation_v2_vernier_round2", "evaluation_v1_vernier_round2"):
        _ev = internal.get(_k) if isinstance(internal, dict) else None
        if isinstance(_ev, dict):
            _note = (_ev.get("_internal_note") or {}).get("vernier_round2") or {}
            if any(isinstance(a, dict) and a.get("pass") for a in (_note.get("attempts") or [])):
                _vr2_passed = True
                break
    vr2_expected = bool(seqs.get("vernier_round2_VH") and seqs.get("vernier_round2_VL") and _vr2_passed)
    _from_vr2 = final_src and ("vernier_round2" in str(final_src).lower() or "vernier" in final_src.name.lower())
    if vr2_expected and final_src and not _from_vr2:
        raise RuntimeError(
            "humanized_final  vernier_round2 PDB（ SSOT），。"
            f"  structure.vernier_round2_pdb  _internal.evaluation_*_vernier_round2。"
        )
    if _safe_copy(final_src, final_dst):
        src_label = final_src.name if final_src else "—"
        delivered.append(f"  ✓ [ PDB]  {final_dst.relative_to(SUITE)}  (: {src_label})")
    else:
        missing.append(f"  ✗ [ PDB]  ")

    # ──  PDB（，）────────────────
    def _seq_key(v):
        return (seqs.get(f"{v}_VH") or "", seqs.get(f"{v}_VL") or "")

    versions_to_deliver = []
    seen_keys = set()
    for ver, label in [
        ("v1", "v1（CDR ）"),
        ("v2", "v2（+ Vernier ）"),
        ("v3", "v3（+ CMC ）"),
        ("vernier_round2", "vernier_round2（）"),
    ]:
        k = _seq_key(ver)
        if not (k[0] and k[1]) or k in seen_keys:
            continue
        seen_keys.add(k)
        versions_to_deliver.append((ver, label))
    for ver, label in versions_to_deliver:
        ver_src = _find_file([
            project_dir / "structures" / f"{antibody_id}_humanized_{ver}.pdb",
            project_dir / f"{antibody_id}_humanized_{ver}.pdb",
        ])
        if ver_src is None and ver == "vernier_round2":
            vr2_pdb = struct_info.get("vernier_round2_pdb")
            if vr2_pdb:
                vr2_path = Path(str(vr2_pdb).replace("\\", "/"))
                for base in (SUITE, project_dir):
                    p = base / vr2_path if not vr2_path.is_absolute() else vr2_path
                    if p.exists():
                        ver_src = p
                        break
            if ver_src is None:
                ver_src = _rglob_first(project_dir, [
                    f"{antibody_id}_humanized_*_vernier_round2*.pdb",
                    f"{antibody_id}_humanized*vernier*.pdb",
                ])
        if ver_src and ver_src.exists():
            ver_dst = build_dir / "structures" / f"{antibody_id}_humanized_{ver}.pdb"
            if _safe_copy(ver_src, ver_dst):
                delivered.append(f"  ✓ [{label}  PDB]  {ver_dst.relative_to(SUITE)}")

    # ── README.md ────────────────────────────────────────────────────────────
    meta = {}
    if results_json.exists():
        with open(results_json, encoding="utf-8") as f:
            meta = json.load(f)

    final_version = meta.get("_meta", {}).get("final_version", "—")
    vh_gene       = meta.get("germline", {}).get("VH_gene", "—")
    vl_gene       = meta.get("germline", {}).get("VL_gene", "—")
    pI_val        = meta.get("developability", {}).get("pI", {}).get(final_version, "—")
    imm_risk      = meta.get("immunogenicity", {}).get("risk_level", {}).get(final_version, "—")
    rmsd_max      = meta.get("structure", {}).get("cdr_rmsd_max", "—")
    pI_status     = "✅  5.5–8.5" if isinstance(pI_val, (int, float)) and 5.5 <= pI_val <= 8.5 else "—"
    rmsd_status   = "✅ < 1.5 Å"     if isinstance(rmsd_max, (int, float)) and rmsd_max < 1.5 else "—"

    readme = f"""# {antibody_id.upper()}  — 

****: {datetime.now().strftime("%Y-%m-%d")}  
****: InSynBio VH/VL  V4.4  
****: {final_version} | ****: {vh_gene} + {vl_gene}

---

## 

### reports/ — 
|  |  |
|---|---|
| `{antibody_id}_Client_zh.pdf` | **（）** ←  |
| `{antibody_id}_Client_en.pdf` | （，） |

### sequences/ — 
|  |  |
|---|---|
| `{antibody_id}_sequences.fasta` | （FASTA ） |

FASTA ：`>antibody_version|chain|type|status`  
- `status = final` 

### structures/ — 
|  |  |
|---|---|
| `{antibody_id}_mouse.pdb` | （ABodyBuilder2） |
| `{antibody_id}_humanized_final.pdb` |  ({final_version}) （） |
"""
    # （）
    struct_dir = build_dir / "structures"
    for f in sorted(struct_dir.glob(f"{antibody_id}_humanized_*.pdb")):
        name = f.name
        if "final" in name:
            continue
        ver = name.replace(f"{antibody_id}_humanized_", "").replace(".pdb", "")
        ver_desc = {"v1": "v1（CDR ）", "v2": "v2（+ Vernier）", "v3": "v3（+ CMC）", "vernier_round2": "vernier_round2（）"}.get(ver, ver)
        readme += f"| `{name}` | {ver_desc}  |\n"
    readme += f"""
>  **PyMOL**、**UCSF ChimeraX**  [Mol*](https://molstar.org/viewer/) 。  
> ****：；（ v2=v3），。

---

## 

|  |  |  |
|---|---|---|
|  pI (Fab) | {pI_val} | {pI_status} |
| CDR  RMSD () | {rmsd_max} Å | {rmsd_status} |
| （Immunogenicity） | {imm_risk} | {"⚠️  PBMC " if imm_risk == "HIGH" else "—"} |

 `reports/{antibody_id}_Client_zh.pdf`。

---

* InSynBio AbEngineCore V4.4  | {datetime.now().strftime("%Y-%m-%d")}*
"""

    readme_path = build_dir / "README.md"
    readme_path.write_text(readme, encoding="utf-8")
    delivered.append(f"  ✓ [README.md]  {readme_path.relative_to(SUITE)}")

    # ──  ─────────────────────────────────────────────────────────────
    print("\n:")
    for d in delivered:
        print(d)
    if missing:
        print("\n⚠️  （）:")
        for m in missing:
            print(m)

    print("\n（）:")
    internal = [
        f"  — {antibody_id}_V44_Audit.md / .pdf  (QA )",
        f"  — {antibody_id}_results.json          ()",
        f"  — {antibody_id}_Dev_Report.md         (，)",
    ]
    for i in internal:
        print(i)

    # ── Swap build_dir → final_dir (best-effort) ─────────────────────────────
    out_dir = build_dir
    if not missing:
        try:
            if final_dir.exists():
                backup = SUITE / f"delivery_{antibody_id}__backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                final_dir.rename(backup)
            build_dir.rename(final_dir)
            out_dir = final_dir
        except Exception as e:
            # Windows 。： final_dir，（）
            print(f"\n  [WARN]  {final_dir.relative_to(SUITE)}（）。。")
            print(f"         : {e}")

            n_ok, n_fail = 0, 0
            try:
                final_dir.mkdir(parents=True, exist_ok=True)
                for src in build_dir.rglob("*"):
                    if not src.is_file():
                        continue
                    rel = src.relative_to(build_dir)
                    dst = final_dir / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(src, dst)
                        n_ok += 1
                    except Exception:
                        n_fail += 1

                out_dir = final_dir
                if n_fail == 0:
                    print(f"  ✓ : {final_dir.relative_to(SUITE)}")
                else:
                    print(f"  ✓  {n_ok}  {final_dir.relative_to(SUITE)}；{n_fail} （ PDF ）")
            except Exception as e2:
                out_dir = build_dir
                print(f"  [WARN] ，: {build_dir.relative_to(SUITE)}")
                print(f"         : {e2}")

    # ── ZIP  ─────────────────────────────────────────────────────────────
    if make_zip:
        zip_name = f"{antibody_id}_delivery_{datetime.now().strftime('%Y%m%d')}.zip"
        zip_path = SUITE / zip_name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # ZIP white-list: only files created by this script in out_dir
            # Always keep ZIP folder name as delivery_{id}/ for customer.
            for f in out_dir.rglob("*"):
                if f.is_file():
                    arc = Path(f"delivery_{antibody_id}") / f.relative_to(out_dir)
                    zf.write(f, arc)
        size_kb = zip_path.stat().st_size // 1024
        print(f"\n  ✓ ZIP : {zip_name}  ({size_kb} KB)")
        print(f"     →  ZIP ")
        return zip_path

    print(f"\n  : {out_dir.relative_to(SUITE)}")
    return out_dir


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(": python scripts/package_delivery.py <antibody_id> <project_dir> [--zip]")
        print(": python scripts/package_delivery.py 9c1 projects/9c1_Redesign --zip")
        sys.exit(1)

    ab_id  = sys.argv[1]
    proj   = SUITE / sys.argv[2]
    zipped = "--zip" in sys.argv

    package_delivery(ab_id, proj, make_zip=zipped)
