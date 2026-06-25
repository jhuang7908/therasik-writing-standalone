"""
Regression Tests
================
Framework tests (1-4):
  1. Create project from template.
  2. Machine QA PASS -> MACHINE_QA_PASSED_HUMAN_PENDING.
  3. Injected machine FAIL is detected -> MACHINE_QA_FAILED.
  4. QA script modules import cleanly.

Content-level QA FAIL cases (5-8):
  5. Hallucinated reference (no DOI/PMID/PMCID/URL) -> reference_claim_qa FAIL.
  6. AI-style prose (hedge words, transition openers) -> ai_style_qa FAIL.
  7. Fragmented paragraphs (all single-sentence) -> paragraph_structure_qa FAIL.
  8. Figure referenced in manuscript but no figures.csv -> figure_contract_qa FAIL.

Content-level QA PASS cases (9-11):
  9. Valid references and claims (source_ref column) -> reference_claim_qa PASS.
 10. Clean academic prose -> ai_style_qa PASS.
 11. Structured paragraphs -> paragraph_structure_qa PASS.

Gate reader robustness (12-13):
 12. Status: pass (lowercase) is normalised to PASS.
 13. Status: PASS -- see notes (trailing comment) is normalised to PASS.

Validator (14):
 14. validate_basic_skill.py returns 0 and prints PASS on valid skill dir.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
CREATE = SKILL_DIR / "scripts" / "create_project_from_template.py"
RUNNER = SKILL_DIR / "scripts" / "run_full_workflow.py"
VALIDATOR = SKILL_DIR / "scripts" / "validate_basic_skill.py"
QA_DIR = SKILL_DIR / "scripts" / "qa"
PYTHON = Path(sys.executable)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=str(cwd), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
    )


def preseed_machine_qa_pass(project: Path) -> None:
    qa = project / "03_QA"
    qa.mkdir(parents=True, exist_ok=True)
    for fname in (
        "paragraph_structure_QA.md",
        "ai_style_human_voice_QA.md",
        "reference_claim_support_QA.md",
        "figure_contract_QA.md",
    ):
        (qa / fname).write_text(
            "Status: PASS\n\nPre-seeded by regression test.\n",
            encoding="utf-8",
        )


def parse_audit(stdout: str) -> dict:
    start = stdout.find("{")
    if start == -1:
        return {}
    try:
        return json.loads(stdout[start:])
    except json.JSONDecodeError:
        return {}


def run_qa_script(script_name: str, project_root: Path,
                  extra_args: list[str] | None = None) -> tuple[int, str, str]:
    script_path = QA_DIR / script_name
    cmd = [str(PYTHON), str(script_path), "--project-root", str(project_root)]
    if extra_args:
        cmd += extra_args
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=60)
    return proc.returncode, proc.stdout, proc.stderr


def read_qa_status(qa_file: Path) -> str:
    """Read Status: line and normalise to uppercase first token only."""
    if not qa_file.exists():
        return "MISSING"
    for line in qa_file.read_text(encoding="utf-8").splitlines()[:40]:
        if line.strip().lower().startswith("status:"):
            raw = line.split(":", 1)[1].strip()
            import re
            token = re.split(r"[\s\-—–]", raw)[0].upper()
            return token if token else "UNKNOWN"
    return "UNKNOWN"


def make_project(base_dir: Path, name: str) -> Path:
    project = base_dir / name
    proc = run(
        [str(PYTHON), str(CREATE), str(project), "--project-id", name],
        SKILL_DIR,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"create_project failed for '{name}': {proc.stderr[:200]}")
    return project


def make_valid_references_csv(db: Path) -> None:
    db.mkdir(parents=True, exist_ok=True)
    with (db / "references.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "doi", "pmid", "pmcid", "url"])
        w.writerow(["ref001", "A Real Study", "10.1234/real", "", "", ""])


def make_valid_claims_csv(db: Path, ref_col: str = "reference_id") -> None:
    with (db / "claims.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["claim_id", "claim_text", ref_col])
        w.writerow(["cl001", "This finding is real", "ref001"])


CLEAN_PROSE = """\
# Mechanisms of Antibody-Mediated Complement Activation

Antibody-mediated complement activation is central to adaptive immunity.
The classical pathway is initiated when C1q binds to the Fc region of IgG or IgM antibodies
complexed with antigen, triggering sequential activation of C1r and C1s serine proteases.
This proteolytic cascade ultimately deposits C3b on the target surface,
opsonising pathogens for phagocytosis and nucleating the membrane-attack complex.

Structure-activity relationships in Fc-mediated complement engagement have been characterised
by cryo-electron microscopy and hydrogen-deuterium exchange mass spectrometry.
The CH2 domain glycosylation state modulates binding affinity for C1q,
with afucosylated species showing enhanced pro-inflammatory signalling.
Point substitutions at positions E333 and K334 alter the binding geometry
of the C1q globular head domain without perturbing overall antibody structure.

Therapeutic implications follow directly from these mechanisms.
Effector-null variants carrying L234A/L235A (LALA) substitutions are used where
complement-independent binding is desired, as in checkpoint inhibitors.
Conversely, Fc engineering to enhance C1q recruitment is pursued for
anti-tumour antibodies where complement-dependent cytotoxicity contributes to efficacy.
The balance between these opposing engineering goals depends on the target biology
and the intended clinical indication.
"""

STRUCTURED_PARAGRAPHS = """\
# Structured Test Manuscript

The complement system represents a key effector arm of innate and adaptive immunity.
It is activated through three distinct pathways: classical, lectin, and alternative.
Each pathway converges on the cleavage of C3, producing C3a and C3b,
which mediate opsonisation, inflammation, and membrane-attack complex formation.
The tight regulation of this system prevents damage to host tissues.

Antibody-dependent complement activation through the classical pathway begins
when C1q recognises IgG or IgM in immune complexes on target surfaces.
Binding of multiple C1q globular heads cross-links and activates the C1r/C1s
protease module, which cleaves C4 and C2 to assemble the classical C3 convertase.
Structural studies have revealed the molecular basis of this specificity.

Fc engineering strategies exploit these structural insights to modulate complement activity.
The LALA mutation pair (L234A/L235A) in the CH2 domain ablates C1q binding,
producing effector-silent antibodies used in contexts where complement engagement
would cause toxicity or off-target killing.
Enhancement mutations such as K326W/E333S increase C1q affinity and are explored
in oncology applications where complement-dependent cytotoxicity is desirable.
"""


def main() -> int:
    results = []
    overall = "PASS"

    def record(name: str, ok: bool, **extra) -> None:
        nonlocal overall
        entry = {"name": name, "pass": ok, **extra}
        results.append(entry)
        if not ok:
            overall = "FAIL"

    with tempfile.TemporaryDirectory(prefix="therasik_skill_test_") as tmp:
        root = Path(tmp)

        # ── Test 1: create project from template ──────────────────────────────
        demo = root / "demo"
        proc = run(
            [str(PYTHON), str(CREATE), str(demo), "--project-id", "synthetic_demo"],
            SKILL_DIR,
        )
        record("create_demo_project", proc.returncode == 0, stderr=proc.stderr[-300:])
        if proc.returncode != 0:
            print(json.dumps({"status": "FAIL", "results": results}, indent=2))
            return 1

        # ── Test 2: machine gates PASS -> MACHINE_QA_PASSED_HUMAN_PENDING ─────
        preseed_machine_qa_pass(demo)
        proc = run(
            [str(PYTHON), str(RUNNER), str(demo / "project_config.json"),
             "--skip-qa-scripts"],
            SKILL_DIR,
        )
        status = parse_audit(proc.stdout)
        record(
            "framework_machine_qa_pass",
            status.get("release_decision") == "MACHINE_QA_PASSED_HUMAN_PENDING",
            release_decision=status.get("release_decision"),
            machine_gate_failures=status.get("machine_gate_failures"),
        )

        # ── Test 3: injected machine FAIL is detected ─────────────────────────
        broken = root / "broken"
        shutil.copytree(demo, broken)
        preseed_machine_qa_pass(broken)
        (broken / "03_QA" / "reference_claim_support_QA.md").write_text(
            "Status: FAIL\n\nSynthetic failure.\n", encoding="utf-8"
        )
        proc = run(
            [str(PYTHON), str(RUNNER), str(broken / "project_config.json"),
             "--skip-qa-scripts"],
            SKILL_DIR,
        )
        status = parse_audit(proc.stdout)
        record(
            "framework_machine_qa_fail_detected",
            proc.returncode != 0 and status.get("release_decision") == "MACHINE_QA_FAILED",
            release_decision=status.get("release_decision"),
        )

        # ── Test 4: QA script modules import cleanly ──────────────────────────
        import_results = []
        for module_file in sorted(QA_DIR.glob("run_*.py")):
            spec = importlib.util.spec_from_file_location(module_file.stem, module_file)
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
                import_results.append({"module": module_file.name, "ok": True})
            except Exception as exc:
                import_results.append({"module": module_file.name, "ok": False,
                                        "error": str(exc)})
        record("qa_script_imports", all(r["ok"] for r in import_results),
               modules=import_results)

        # ── Test 5: hallucinated reference -> FAIL ────────────────────────────
        rc_proj = make_project(root, "rc_fail")
        db = rc_proj / "00_project_database"
        db.mkdir(parents=True, exist_ok=True)
        with (db / "references.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "title", "doi", "pmid", "pmcid", "url"])
            w.writerow(["ref001", "Hallucinated Study", "", "", "", ""])
        make_valid_claims_csv(db)
        rc, stdout, _ = run_qa_script("run_reference_claim_qa.py", rc_proj)
        qa_s = read_qa_status(rc_proj / "03_QA" / "reference_claim_support_QA.md")
        record("hallucinated_reference_detected", qa_s == "FAIL",
               qa_status=qa_s, stdout=stdout[:150])

        # ── Test 6: AI-style prose -> FAIL ───────────────────────────────────
        style_proj = make_project(root, "style_fail")
        ai_prose = "\n\n".join([
            "# AI Style Test",
            "Notably, this study examines the treatment. Furthermore, results are important.",
            "It is worth noting that data suggests improvement. Importantly, we observe the following.",
            "Moreover, findings have implications. It should be noted that analysis is exploratory.",
            "In this review, we aim to provide comprehensive overview. Additionally we also consider context.",
            "These results are important and have broad implications. Notably, this is a key finding.",
            "Furthermore, evidence strongly supports the hypothesis. It is worth noting this is novel.",
            "Importantly, these findings challenge assumptions. Moreover, the data confirms prior work.",
            "In summary, we conclude that treatment is effective. Notably, future work is needed.",
            "Of note, these observations have clinical relevance. Interestingly, the pattern repeats.",
        ])
        (style_proj / "01_manuscript" / "manuscript.md").write_text(
            ai_prose, encoding="utf-8"
        )
        rc, stdout, _ = run_qa_script("run_ai_style_qa.py", style_proj)
        qa_s = read_qa_status(style_proj / "03_QA" / "ai_style_human_voice_QA.md")
        record("ai_style_detected", qa_s == "FAIL", qa_status=qa_s, stdout=stdout[:150])

        # ── Test 7: fragmented paragraphs -> FAIL ─────────────────────────────
        para_proj = make_project(root, "para_fail")
        frags = ["# Fragment Test\n"]
        for i in range(20):
            frags.append(f"This is sentence {i + 1}.\n\n")
        (para_proj / "01_manuscript" / "manuscript.md").write_text(
            "".join(frags), encoding="utf-8"
        )
        rc, stdout, _ = run_qa_script("run_paragraph_structure_qa.py", para_proj)
        qa_s = read_qa_status(para_proj / "03_QA" / "paragraph_structure_QA.md")
        record("fragmented_paragraphs_detected", qa_s == "FAIL",
               qa_status=qa_s, stdout=stdout[:150])

        # ── Test 8: figure in manuscript, no figures.csv -> FAIL ──────────────
        fig_proj = make_project(root, "fig_fail")
        (fig_proj / "01_manuscript" / "manuscript.md").write_text(
            "# Figure Test\n\n![Survival curve](figures/fig1.svg)\n\nFigure 1 shows survival.\n",
            encoding="utf-8",
        )
        fcsv = fig_proj / "00_project_database" / "figures.csv"
        if fcsv.exists():
            fcsv.unlink()
        rc, stdout, _ = run_qa_script("run_figure_contract_qa.py", fig_proj)
        qa_s = read_qa_status(fig_proj / "03_QA" / "figure_contract_QA.md")
        record("missing_figure_contract_detected", qa_s == "FAIL",
               qa_status=qa_s, stdout=stdout[:150])

        # ── Test 9: valid references + source_ref schema -> PASS ──────────────
        rc_pass_proj = make_project(root, "rc_pass")
        db = rc_pass_proj / "00_project_database"
        make_valid_references_csv(db)
        # Use source_ref schema (matches the template)
        make_valid_claims_csv(db, ref_col="source_ref")
        rc, stdout, _ = run_qa_script("run_reference_claim_qa.py", rc_pass_proj)
        qa_s = read_qa_status(rc_pass_proj / "03_QA" / "reference_claim_support_QA.md")
        record("valid_references_pass", qa_s == "PASS", qa_status=qa_s, stdout=stdout[:150])

        # ── Test 10: clean prose -> ai_style_qa PASS ──────────────────────────
        style_pass_proj = make_project(root, "style_pass")
        (style_pass_proj / "01_manuscript" / "manuscript.md").write_text(
            CLEAN_PROSE, encoding="utf-8"
        )
        rc, stdout, _ = run_qa_script("run_ai_style_qa.py", style_pass_proj)
        qa_s = read_qa_status(style_pass_proj / "03_QA" / "ai_style_human_voice_QA.md")
        record("clean_prose_passes_ai_style", qa_s == "PASS",
               qa_status=qa_s, stdout=stdout[:150])

        # ── Test 11: structured paragraphs -> paragraph_structure_qa PASS ─────
        para_pass_proj = make_project(root, "para_pass")
        (para_pass_proj / "01_manuscript" / "manuscript.md").write_text(
            STRUCTURED_PARAGRAPHS, encoding="utf-8"
        )
        rc, stdout, _ = run_qa_script("run_paragraph_structure_qa.py", para_pass_proj)
        qa_s = read_qa_status(para_pass_proj / "03_QA" / "paragraph_structure_QA.md")
        record("structured_paragraphs_pass", qa_s == "PASS",
               qa_status=qa_s, stdout=stdout[:150])

        # ── Test 12: Status: pass (lowercase) normalised to PASS ──────────────
        gate_proj = root / "gate_test"
        gate_proj.mkdir()
        qaf = gate_proj / "test_gate.md"
        qaf.write_text("Status: pass\n\nSome notes.\n", encoding="utf-8")
        observed = read_qa_status(qaf)
        record("gate_reader_normalises_lowercase", observed == "PASS",
               observed=observed)

        # ── Test 13: Status: PASS -- trailing comment normalised ───────────────
        qaf.write_text("Status: PASS -- reviewed by author\n\nSome notes.\n",
                       encoding="utf-8")
        observed = read_qa_status(qaf)
        record("gate_reader_strips_trailing_comment", observed == "PASS",
               observed=observed)

        # ── Test 14: validate_basic_skill.py returns 0 + prints PASS ──────────
        vproc = run(
            [str(PYTHON), str(VALIDATOR), str(SKILL_DIR)],
            SKILL_DIR,
        )
        record(
            "validator_passes_on_skill_dir",
            vproc.returncode == 0 and "PASS" in vproc.stdout,
            returncode=vproc.returncode,
            stdout=vproc.stdout.strip(),
        )

    print(json.dumps({"status": overall, "results": results}, indent=2))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
