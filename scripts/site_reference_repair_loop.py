#!/usr/bin/env python3
"""
Iterative site reference repair: audit PubMed links → PubMed re-search → surgical replace → re-audit.

Goals (user workflow):
  1. Run full-site PMID audit (links + context).
  2. For failing rows, build PubMed esearch queries from local context / anchor text.
  3. Rank candidates via the same efetch + relevance heuristic as audit.
  4. Replace only the targeted link (HTML: offset-near hit; JSON: json path).
  5. Repeat until no failing rows or --max-rounds / no progress.

Outputs:
  reports/site_ref_repair_log.md   (append each round)
  reports/site_pmid_audit.*        (refreshed by audit step)

Env:
  NCBI_API_KEY           recommended
  NCBI_CONTACT_EMAIL     optional

Scope (automatic replacement):
  - ADA: `ada_db_data.json` rows with PubMed `citation_url` (canonical `docs/ada_db_data.json`, then synced to
    `therasik-web-source/` and `insynbio-web-source/`).
  - Antibody / other HTML: `source_file` entries whose audit `field_path` ends with `@offset<N>` (PubMed URL
    near that offset). Each site HTML file is repaired independently (e.g. `docs/antibody-guide.html` vs
    `Therasik_Antibody_Guide.html`).

Not yet auto-repaired (still appear in audit CSV; fix manually or extend this script):
  - Vaccine KB / component library / nested JSON `ref` strings without the patterns above.
  - Non-PubMed citation links (FDA PDFs, etc.).

Iterating until clean:
  Run `python scripts/site_reference_repair_loop.py --apply --max-rounds 20` repeatedly, or use a shell loop,
  until `site_pmid_audit.md` shows no review rows (or only unmigrated JSON types).

Usage:
  python scripts/site_reference_repair_loop.py --row-limit 20
  python scripts/site_reference_repair_loop.py --dry-run
  python scripts/site_reference_repair_loop.py --apply --max-rounds 15
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "reports"
AUDIT_CSV = REPORTS / "site_pmid_audit.csv"
AUDIT_SCRIPT = REPO / "scripts" / "audit_site_pmids.py"

EMAIL = os.environ.get("NCBI_CONTACT_EMAIL", "kb-audit@therasik.com")
DELAY = float(os.environ.get("NCBI_REPAIR_DELAY", "0.35"))
USER_AGENT = "Therasik-SiteRefRepair/1.0"

# Load verify module for efetch + scoring
_VKB_PATH = Path(__file__).resolve().parent / "verify_vaccine_kb_pmids.py"
_spec = importlib.util.spec_from_file_location("verify_vaccine_kb_pmids", _VKB_PATH)
assert _spec and _spec.loader
_vkb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vkb)

efetch_batch = _vkb.efetch_batch
_score_relevance = _vkb._score_relevance
_terms_from_ctx = _vkb._terms_from_ctx
RE_PUBMED_URL = _vkb.RE_PUBMED_URL
NCI_META_PMIDS = _vkb.NCI_META_PMIDS

# Match audit_site_pmids augmentation (import if possible)
_AUDIT_PATH = Path(__file__).resolve().parent / "audit_site_pmids.py"
_aspec = importlib.util.spec_from_file_location("audit_site_pmids", _AUDIT_PATH)
assert _aspec and _aspec.loader
_audit_mod = importlib.util.module_from_spec(_aspec)
_aspec.loader.exec_module(_audit_mod)
_augment_ctx_for_terms = _audit_mod._augment_ctx_for_terms
_terms_for_audit_row = _audit_mod._terms_for_audit_row
_extract_html_chunk_context = _audit_mod._extract_html_chunk_context
_anchor_text_for_pubmed_match = _audit_mod._anchor_text_for_pubmed_match

ADA_REL = "ada_db_data.json"
ADA_ROOTS = ("docs", "therasik-web-source", "insynbio-web-source")


def _sleep() -> None:
    time.sleep(DELAY)


def esearch_pmids(term: str, retmax: int = 40, api_key: str | None = None) -> list[str]:
    term = term.strip()
    if not term or len(term) > 3500:
        return []
    params: dict[str, str] = {
        "db": "pubmed",
        "term": term,
        "retmax": str(retmax),
        "retmode": "json",
        "sort": "relevance",
        "email": EMAIL,
    }
    if api_key:
        params["api_key"] = api_key
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
        params
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read())
    _sleep()
    res = data.get("esearchresult") or {}
    return list(res.get("idlist") or [])


def json_path_segments(path: str) -> list[str | int]:
    segs: list[str | int] = []
    for m in re.finditer(r"\[(\d+)\]|([A-Za-z_][A-Za-z0-9_]*)", path):
        if m.group(1) is not None:
            segs.append(int(m.group(1)))
        else:
            segs.append(m.group(2))
    return segs


def navigate_json(obj: Any, segs: list[str | int]) -> Any:
    cur = obj
    for s in segs:
        if isinstance(s, int):
            cur = cur[s]
        else:
            cur = cur[s]
    return cur


def replace_pubmed_url_near_offset(
    html: str, offset: int, old_pmid: str, new_pmid: str, max_dist: int = 8000
) -> tuple[str, bool]:
    pat = re.compile(
        rf"https?://(?:www\.)?pubmed\.ncbi\.nlm\.nih\.gov/{re.escape(old_pmid)}/?",
        re.I,
    )
    best_m: re.Match[str] | None = None
    best_d = max_dist + 1
    for m in pat.finditer(html):
        if m.start() <= offset <= m.end():
            d = 0
        else:
            d = min(abs(m.start() - offset), abs(m.end() - offset))
        if d < best_d:
            best_d = d
            best_m = m
    if best_m is None or best_d > max_dist:
        return html, False
    new_url = best_m.group(0).replace(old_pmid, new_pmid, 1)
    return html[: best_m.start()] + new_url + html[best_m.end() :], True


def parse_offset_field_path(field_path: str) -> tuple[str, int] | None:
    m = re.search(r"@offset(\d+)$", field_path)
    if not m:
        return None
    off = int(m.group(1))
    base = field_path[: m.start()]
    return base, off


def load_audit_problems(
    csv_path: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with csv_path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            verdict = r.get("verdict", "")
            if verdict in ("ok", "ok_shared_ranking_source"):
                continue
            if r.get("pmid", "") in NCI_META_PMIDS and "nci_meta" in r.get("link_kind", ""):
                continue
            rows.append(r)
    return rows


def build_queries_for_html(
    html: str, offset: int, old_pmid: str, card_name: str
) -> list[str]:
    qs: list[str] = []
    chunk = html[max(0, offset - 5000) : offset]
    ctx = _extract_html_chunk_context(chunk)
    pm_m: re.Match[str] | None = None
    for m in RE_PUBMED_URL.finditer(html):
        if m.group(1) != old_pmid:
            continue
        d = 0 if m.start() <= offset <= m.end() else min(
            abs(m.start() - offset), abs(m.end() - offset)
        )
        if d < 6000:
            pm_m = m
            break
    anchor = ""
    if pm_m:
        anchor = _anchor_text_for_pubmed_match(html, pm_m)
    mech = str(ctx.get("mechanism") or "")[:400]
    name = str(ctx.get("name") or card_name or "")[:200]

    year_m = re.search(r"\b(19|20)\d{2}\b", anchor)
    year = year_m.group(0) if year_m else ""

    auth_m = re.match(r"^([A-Za-z][A-Za-z'\-]+)", anchor.strip())
    first_surname = auth_m.group(1) if auth_m else ""

    if "J Biol Chem" in anchor or "JBC" in anchor.upper():
        if first_surname and year:
            qs.append(f'{first_surname}[Author] AND "journal of biological chemistry"[Journal] AND {year}[PDAT]')
        if first_surname and year and "fc" in (mech + name).lower():
            qs.append(f'{first_surname}[Author] AND FcRn AND {year}[PDAT]')
    if "Immunol" in anchor or "J Immunol" in anchor:
        if first_surname and year:
            qs.append(
                f'{first_surname}[Author] AND (Immunol[Journal] OR "Int Immunol"[Journal]) AND {year}[PDAT]'
            )
        if first_surname and year:
            qs.append(f'{first_surname}[Author] AND (complement OR C1q OR hinge) AND {year}[PDAT]')
    if first_surname and year:
        qs.append(f'{first_surname}[Author] AND {year}[PDAT]')
    if name and mech:
        toks = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", mech)][:6]
        if toks:
            qs.append(f'{name}[Title/Abstract] AND ({" OR ".join(toks[:4])})')
    if name:
        qs.append(f'{name}[Title/Abstract] AND (antibody OR immunoglobulin OR Fc)')
    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for q in qs:
        k = q.lower()
        if k not in seen and len(q) > 5:
            seen.add(k)
            out.append(q)
    return out[:12]


def build_queries_for_ada(drug: dict[str, Any]) -> list[str]:
    name = str(drug.get("name") or "").strip()
    targets = str(drug.get("targets") or "")
    t0 = targets.split("|")[0].strip() if targets else ""
    ind = str(drug.get("indication") or "")[:120]
    qs: list[str] = []
    if name:
        qs.append(
            f'({name}[Title/Abstract]) AND (immunogenicity[Title/Abstract] OR "anti-drug antibody"[Title/Abstract] OR ADA[Title/Abstract])'
        )
        qs.append(f'({name}[Title/Abstract]) AND (efficacy[Title/Abstract] OR pharmacokinetics[Title/Abstract])')
    if name and t0 and t0.lower() != name.lower():
        qs.append(f'({name}[Title/Abstract]) AND ({t0}[Title/Abstract])')
    if name and ind:
        ind_toks = [w for w in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", ind)][:3]
        if ind_toks:
            qs.append(f'({name}[Title/Abstract]) AND ({" OR ".join(ind_toks)})')
    seen: set[str] = set()
    out: list[str] = []
    for q in qs:
        k = q.lower()
        if k not in seen:
            seen.add(k)
            out.append(q)
    return out[:8]


def pick_replacement_pmid(
    queries: list[str],
    ctx_terms_base: list[str],
    old_pmid: str,
    api_key: str | None,
) -> tuple[str | None, str]:
    """Return (new_pmid, debug_note)."""
    tried: set[str] = set()
    candidates: list[str] = []
    for q in queries:
        if not q or q in tried:
            continue
        tried.add(q)
        ids = esearch_pmids(q, retmax=35, api_key=api_key)
        for pid in ids:
            if pid != old_pmid and pid not in candidates:
                candidates.append(pid)
        if len(candidates) >= 25:
            break
    if not candidates:
        return None, "esearch returned no candidates"

    recs: dict[str, dict[str, str]] = {}
    batch = 60
    for i in range(0, len(candidates), batch):
        recs.update(efetch_batch(candidates[i : i + batch], api_key))

    best_id: str | None = None
    best_merit = -1.0
    best_status = ""
    for pid in candidates:
        rec = recs.get(pid, {})
        title = rec.get("title", "")
        abstract = (rec.get("abstract", "") + " " + rec.get("authors", "")).strip()
        st, sc, hits = _score_relevance(ctx_terms_base, title, abstract)
        if st in ("weak_or_unrelated", "no_pubmed_text", "no_local_terms"):
            continue
        if st == "review" and not hits:
            continue
        merit = float(sc) + 0.02 * len(hits)
        if merit > best_merit:
            best_merit = merit
            best_id = pid
            best_status = st
    if best_id is None:
        return None, "no candidate passed relevance threshold"
    return best_id, f"picked {best_id} status={best_status} merit={best_merit:.3f}"


def repair_json_citation_url(
    data: list[Any] | dict[str, Any],
    path_str: str,
    old_pmid: str,
    new_pmid: str,
) -> bool:
    segs = json_path_segments(path_str)
    if len(segs) < 2:
        return False
    parent = navigate_json(data, segs[:-1])
    key = segs[-1]
    val = parent[key]
    if not isinstance(val, str) or old_pmid not in val:
        return False
    new_val = val.replace(f"/{old_pmid}/", f"/{new_pmid}/", 1)
    new_val = new_val.replace(f"/{old_pmid}", f"/{new_pmid}", 1)
    if new_val == val:
        return False
    parent[key] = new_val
    return True


def write_ada_all_roots(obj: list[Any]) -> None:
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    for root in ADA_ROOTS:
        p = REPO / root / ADA_REL
        if p.is_dir():
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def run_audit_subprocess(roots: list[str]) -> None:
    cmd = [sys.executable, str(AUDIT_SCRIPT), "--roots", *roots]
    subprocess.run(cmd, cwd=str(REPO), check=True)


def round_repair(
    roots: list[str],
    apply: bool,
    api_key: str | None,
    row_limit: int | None,
) -> tuple[int, int, int, list[str]]:
    """Returns (attempted, applied_or_proposed, written, log_lines)."""
    if not AUDIT_CSV.is_file():
        return 0, 0, 0, ["audit CSV missing; run audit first"]

    problems = load_audit_problems(AUDIT_CSV)
    log_lines: list[str] = []
    attempted = 0
    proposed = 0
    written = 0

    by_file: dict[str, list[dict[str, str]]] = {}
    ada_keyed: dict[tuple[str, str], dict[str, str]] = {}
    for r in problems:
        fp = r.get("source_file", "")
        if not fp:
            continue
        if fp.endswith(ADA_REL):
            ada_keyed[(r.get("field_path", ""), r.get("pmid", ""))] = r
        else:
            by_file.setdefault(fp, []).append(r)

    ada_loaded: list[Any] | None = None
    ada_path = REPO / "docs" / ADA_REL
    if ada_keyed:
        if ada_path.is_file():
            ada_loaded = json.loads(ada_path.read_text(encoding="utf-8"))
        else:
            log_lines.append("- ADA canonical `docs/ada_db_data.json` missing")

    ada_rows = list(ada_keyed.values())
    ada_rows.sort(key=lambda x: (x.get("field_path", ""), x.get("pmid", "")))

    def process_ada_row(row: dict[str, str]) -> None:
        nonlocal attempted, proposed, written, ada_loaded
        if row_limit is not None and attempted >= row_limit:
            return
        if not isinstance(ada_loaded, list):
            return
        pmid = row.get("pmid", "").strip()
        field_path = row.get("field_path", "")
        if not pmid.isdigit():
            return
        idx_m = re.match(r"\[(\d+)\]\.citation_url", field_path)
        if not idx_m:
            return
        idx = int(idx_m.group(1))
        attempted += 1
        drug = ada_loaded[idx]
        ctx = {k: drug.get(k) for k in ("name", "targets", "indication", "disease_class")}
        ctx_terms = _terms_for_audit_row(ctx)
        queries = build_queries_for_ada(drug)
        new_pmid, note = pick_replacement_pmid(queries, ctx_terms, pmid, api_key=api_key)
        if new_pmid and apply:
            ok = repair_json_citation_url(ada_loaded, field_path, pmid, new_pmid)
            if ok:
                write_ada_all_roots(ada_loaded)
                written += 1
                proposed += 1
                log_lines.append(
                    f"- OK ADA `{drug.get('name')}` [{idx}] {pmid}→{new_pmid} ({note})"
                )
            else:
                log_lines.append(f"- FAIL ADA replace `{drug.get('name')}` [{idx}] {pmid}")
        elif new_pmid:
            proposed += 1
            log_lines.append(
                f"- DRY ADA `{drug.get('name')}` [{idx}] {pmid}→{new_pmid} ({note})"
            )
        else:
            log_lines.append(
                f"- NO_CANDIDATE ADA `{drug.get('name')}` [{idx}] pmid={pmid} ({note})"
            )

    for row in ada_rows:
        if row_limit is not None and attempted >= row_limit:
            break
        process_ada_row(row)

    for rel in sorted(by_file.keys()):
        if row_limit is not None and attempted >= row_limit:
            break
        path = REPO / rel.replace("/", os.sep)
        if not path.is_file():
            log_lines.append(f"- skip missing file `{rel}`")
            continue
        text_cache: str | None = None
        for row in by_file[rel]:
            if row_limit is not None and attempted >= row_limit:
                break
            pmid = row.get("pmid", "").strip()
            field_path = row.get("field_path", "")
            summary = row.get("local_context_summary", "")
            if not pmid.isdigit():
                continue
            off_parsed = parse_offset_field_path(field_path)
            if not (off_parsed and rel.lower().endswith(".html")):
                continue
            _, offset = off_parsed
            attempted += 1
            if text_cache is None:
                text_cache = path.read_text(encoding="utf-8")
            html = text_cache
            pm_m = None
            best_d = 10**9
            for m in RE_PUBMED_URL.finditer(html):
                if m.group(1) != pmid:
                    continue
                d = 0 if m.start() <= offset <= m.end() else min(
                    abs(m.start() - offset), abs(m.end() - offset)
                )
                if d < best_d:
                    best_d = d
                    pm_m = m
            anchor = _anchor_text_for_pubmed_match(html, pm_m) if pm_m else ""
            chunk = html[max(0, offset - 5000) : offset]
            ctx = _extract_html_chunk_context(chunk)
            if anchor:
                ctx = dict(ctx)
                ctx["citation_anchor"] = anchor
            ctx_terms = _terms_for_audit_row(ctx)
            queries = build_queries_for_html(html, offset, pmid, summary)
            new_pmid, note = pick_replacement_pmid(queries, ctx_terms, pmid, api_key=api_key)
            if new_pmid and apply:
                html2, ok = replace_pubmed_url_near_offset(html, int(offset), pmid, new_pmid)
                if ok:
                    html = html2
                    text_cache = html
                    path.write_text(html, encoding="utf-8")
                    written += 1
                    proposed += 1
                    log_lines.append(
                        f"- OK `{rel}` offset~{offset} {pmid}→{new_pmid} ({note}) anchor={anchor[:60]!r}"
                    )
                else:
                    log_lines.append(f"- FAIL replace `{rel}` {pmid} @ {offset}")
            elif new_pmid:
                proposed += 1
                log_lines.append(
                    f"- DRY `{rel}` offset~{offset} {pmid}→{new_pmid} ({note}) anchor={anchor[:60]!r}"
                )
            else:
                log_lines.append(f"- NO_CANDIDATE `{rel}` pmid={pmid} ({note}) q={queries[:1]}")

    return attempted, proposed, written, log_lines


def main() -> None:
    ap = argparse.ArgumentParser(description="Repair PubMed references; re-audit in a loop.")
    ap.add_argument("--apply", action="store_true", help="Write file changes (default: dry-run / propose only)")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Same as default: audit + propose replacements without writing files",
    )
    ap.add_argument("--max-rounds", type=int, default=10)
    ap.add_argument(
        "--roots",
        nargs="*",
        default=["therasik-web-source", "insynbio-web-source", "docs"],
        help="Roots passed to audit_site_pmids.py each round",
    )
    ap.add_argument("--row-limit", type=int, default=None, help="Max repair attempts per round (debug)")
    args = ap.parse_args()
    if args.dry_run and args.apply:
        ap.error("Use only one of --apply or --dry-run")
    api_key = os.environ.get("NCBI_API_KEY")

    REPORTS.mkdir(parents=True, exist_ok=True)
    log_path = REPORTS / "site_ref_repair_log.md"

    max_rounds = 1 if not args.apply else args.max_rounds

    for rnd in range(1, max_rounds + 1):
        run_audit_subprocess(args.roots)
        probs = load_audit_problems(AUDIT_CSV)
        n_prob = len(probs)
        header = f"\n## Round {rnd} — problems={n_prob} apply={args.apply}\n\n"
        if n_prob == 0:
            with log_path.open("a", encoding="utf-8") as lf:
                lf.write(header + "_Clean — no failing rows._\n")
            print(f"Round {rnd}: clean (0 problems).")
            return

        att, prop, written, lines = round_repair(
            args.roots, apply=args.apply, api_key=api_key, row_limit=args.row_limit
        )
        with log_path.open("a", encoding="utf-8") as lf:
            lf.write(header)
            lf.write(f"- attempted={att} proposed={prop} files_written={written}\n")
            for line in lines[:500]:
                lf.write(line + "\n")
            if len(lines) > 500:
                lf.write(f"\n_…{len(lines) - 500} more lines omitted…_\n")

        print(
            f"Round {rnd}: audit_problems={n_prob} repair_attempted={att} proposed={prop} written={written}"
        )

        if not args.apply:
            if prop == 0:
                print("Dry-run: no replacement PMID proposed for handled rows; see log.")
                sys.exit(3)
            print("Dry-run only (no files changed). Re-run with --apply to write fixes.")
            return

        run_audit_subprocess(args.roots)
        probs2 = load_audit_problems(AUDIT_CSV)
        print(f"  Re-audit problems: {len(probs2)}")
        if len(probs2) == 0:
            print("All clear after repair.")
            return
        if len(probs2) >= n_prob and written == 0:
            print("No progress this round; stopping (remaining rows need manual curation or new heuristics).")
            sys.exit(2)
        if rnd >= max_rounds and len(probs2) > 0:
            print(
                f"Stopping after {max_rounds} apply round(s); "
                f"{len(probs2)} audit rows still flagged. Re-run with --apply (or increase --max-rounds) to continue."
            )
            return

    return


if __name__ == "__main__":
    main()
