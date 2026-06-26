#!/usr/bin/env python3
"""
validate_website.py  v1.1
─────────────────────────
Therasik / InSynBio  + 

:
  python scripts/validate_website.py --file "therasik-web-source/Therasik_ADC_Database.html"
  python scripts/validate_website.py --site therasik
  python scripts/validate_website.py --site insynbio
  python scripts/validate_website.py --site both
  python scripts/validate_website.py --site therasik --deploy -m "feat: ..."
  python scripts/validate_website.py --site both --deploy -m "update: "
  python scripts/validate_website.py --site therasik --kb          #  KB 9 

:
  FATAL  — ，
  WARN   — ，
  OK     — 

7 :
  R1  （ </body></html>，）
  R2  <script>  </script> 
  R3  toggleCard、tab 、filter 
  R4   images/ 
  R5  data-search 
  R6  <div> （ ≤ 10）
  R7  
  Nav ：

KB 9 （--kb ， _KB / _Database）:
  K1  noindex meta 
  K2  copyright meta 
  K3   CSS（user-select:none）
  K4   JS（contextmenu / copy ）
  K5  （@media print ）
  K6   honeypot 
  K7  Tab （tab-btn + ）
  K8  （filter  + data-search ）
  K9  
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# ──  ──────────────────────────────────────────────────────────────────
try:
    import colorama
    colorama.init()
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
except ImportError:
    RED = GREEN = YELLOW = CYAN = BOLD = RESET = ""

def ok(msg):    print(f"  {GREEN}✓{RESET} {msg}")
def warn(msg):  print(f"  {YELLOW}⚠{RESET} {msg}")
def fail(msg):  print(f"  {RED}✗{RESET} {msg}")
def info(msg):  print(f"  {CYAN}·{RESET} {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")

# ──  ──────────────────────────────────────────────────────────────────
SUITE_ROOT = Path(__file__).resolve().parents[1]

SITES = {
    "therasik": {
        "dir":     SUITE_ROOT / "therasik-web-source",
        "deploy":  SUITE_ROOT / "deploy_therasik.ps1",
        "branch":  "main",
        "url":     "https://www.therasik.com",
        "label":   "Therasik ()",
    },
    "insynbio": {
        "dir":     SUITE_ROOT / "insynbio-web-source",
        "deploy":  SUITE_ROOT / "deploy_insynbio.ps1",
        "branch":  "master",
        "url":     "https://www.insynbio.com",
        "label":   "InSynBio ()",
    },
}

# ── KB （ KB 9 ）────────────────────────────────────
KB_PAGE_PATTERNS = re.compile(
    r"(_KB|_Database|_ADA_|_ADC_|_CAR_|_Vaccine_KB)", re.IGNORECASE
)

# ── ：/ ────────────────────────────
PAGE_RULES = {
    # pattern → list of (required_pattern, description)
    r"toggleCard\(this\)": [
        (r"function toggleCard", "toggleCard "),
    ],
    r'class="tab-btn"': [
        (r"addEventListener.*click|\.tab-btn.*click|tab-btn.*listen",
         "tab-btn "),
    ],
    r'class="tab-panel"': [
        (r"panel.*classList|classList.*panel|active.*panel|panel.*active",
         "tab-panel "),
    ],
    r"filterGrid\(|filterPrograms\(|filterAntigens\(": [
        (r"function filter", "filter "),
    ],
}

# ──  ────────────────────────────────────────────────────────────────

def validate_file(path: Path, verbose: bool = True) -> dict:
    """
     HTML 。
     {"path": path, "fatals": [...], "warnings": [...], "passed": bool}
    """
    rel = path.name
    fatals = []
    warnings = []

    if not path.exists():
        return {"path": path, "fatals": [f": {path}"], "warnings": [], "passed": False}

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"path": path, "fatals": [f": {e}"], "warnings": [], "passed": False}

    lines = content.splitlines()
    total_lines = len(lines)

    # ── R1:  ─────────────────────────────────────────────────
    tail = content.rstrip()
    if not tail.endswith("</html>"):
        fatals.append(f" </html>（: {tail[-60:]!r}）")
    elif "</body>" not in content[-500:]:
        fatals.append(" </body>")
    else:
        if verbose: ok(f"[R1]  ({total_lines} )")

    # ── R2: <script> / </script>  ─────────────────────────────────────
    open_scripts  = len(re.findall(r"<script[\s>]", content, re.IGNORECASE))
    close_scripts = len(re.findall(r"</script>", content, re.IGNORECASE))
    if open_scripts != close_scripts:
        fatals.append(f"<script> ({open_scripts})  </script> ({close_scripts}) ")
    else:
        if verbose: ok(f"[R2] script  ({open_scripts} )")

    # ── R3:  ───────────────────────────────────────────────────
    for trigger_pat, requirements in PAGE_RULES.items():
        if re.search(trigger_pat, content):
            for req_pat, desc in requirements:
                if not re.search(req_pat, content, re.IGNORECASE | re.DOTALL):
                    fatals.append(f" {trigger_pat!r}， {desc}")
                else:
                    if verbose: ok(f"[R3] {desc} ")

    # ── R4:  ─────────────────────────────────────────────
    img_refs = re.findall(r'(?:src|href)=["\'](?!http)(images/[^"\'?#\s]+)', content)
    img_dir  = path.parent / "images"
    missing_imgs = []
    for img in set(img_refs):
        img_path = path.parent / img
        if not img_path.exists():
            missing_imgs.append(img)
    if missing_imgs:
        for img in missing_imgs[:5]:
            warnings.append(f": {img}")
        if len(missing_imgs) > 5:
            warnings.append(f"...  {len(missing_imgs)-5} ")
    elif img_refs and verbose:
        ok(f"[R4] {len(set(img_refs))} ")

    # ── R5: data-search  ────────────────────────────────────────
    empty_search = len(re.findall(r'data-search=["\']\s*["\']', content))
    if empty_search > 0:
        warnings.append(f"{empty_search}  data-search （）")
    elif re.search(r'data-search=', content) and verbose:
        ok(f"[R5] data-search ")

    # ── R6:  HTML  ────────────────────────────────────────────
    unclosed_divs = content.count("<div") - content.count("</div>")
    if abs(unclosed_divs) > 10:
        warnings.append(f"<div>  </div>  ({unclosed_divs:+d})，")
    elif verbose:
        ok(f"[R6] div  (={unclosed_divs:+d})")

    # ── R7: （ http ）────────────────────────────
    abs_paths = re.findall(r'(?:src|href)=["\'](?:C:|D:|/Users/|/home/)[^"\']*["\']', content)
    if abs_paths:
        warnings.append(f" {len(abs_paths)} （）")

    # ──  ───────────────────────────────────────────────────────────────
    passed = len(fatals) == 0
    return {
        "path":     path,
        "fatals":   fatals,
        "warnings": warnings,
        "passed":   passed,
        "lines":    total_lines,
    }


# ── KB 9  ────────────────────────────────────────────────────────────

def validate_kb_page(path: Path, verbose: bool = True) -> dict:
    """
     K1–K9 。
     {"fatals": [...], "warnings": [...], "passed": bool}
    """
    fatals = []
    warnings = []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"fatals": [f": {e}"], "warnings": [], "passed": False}

    if verbose:
        header(f"  ── KB 9 : {path.name} ──")

    # K1 — noindex meta
    if re.search(r'<meta[^>]+robots[^>]+noindex', content, re.IGNORECASE):
        if verbose: ok("[K1] noindex meta ")
    else:
        fatals.append("K1:  <meta name=\"robots\" content=\"noindex\">（）")

    # K2 — copyright meta
    if re.search(r'<meta[^>]+copyright', content, re.IGNORECASE):
        if verbose: ok("[K2] copyright meta ")
    else:
        warnings.append("K2:  <meta name=\"copyright\"> ")

    # K3 —  CSS
    if re.search(r'user-select\s*:\s*none', content, re.IGNORECASE):
        if verbose: ok("[K3]  CSS（user-select:none）")
    else:
        warnings.append("K3:  user-select:none  CSS")

    # K4 —  JS（contextmenu  copy ）
    has_contextmenu = re.search(r"contextmenu", content, re.IGNORECASE)
    has_copy_block  = re.search(r"addEventListener.*['\"]copy['\"]|on[Cc]opy\s*=", content, re.DOTALL)
    if has_contextmenu and has_copy_block:
        if verbose: ok("[K4]  JS（contextmenu + copy ）")
    elif has_contextmenu:
        warnings.append("K4:  contextmenu， copy ")
    else:
        warnings.append("K4:  JS（contextmenu/copy ）")

    # K5 — 
    if re.search(r'@media\s+print', content, re.IGNORECASE):
        if verbose: ok("[K5] （@media print）")
    else:
        warnings.append("K5:  @media print ")

    # K6 —  honeypot（）
    honeypot = re.search(
        r'display\s*:\s*none[^}]*href|href=["\'][^"\']+["\'][^>]*style=["\'][^"\']*display\s*:\s*none',
        content, re.IGNORECASE | re.DOTALL
    )
    #  aria-hidden + link  class  honeypot 
    honeypot2 = re.search(r'honeypot|aria-hidden=["\']true["\'][^>]*href|href[^>]*aria-hidden', content, re.IGNORECASE)
    if honeypot or honeypot2:
        if verbose: ok("[K6]  honeypot ")
    else:
        warnings.append("K6:  honeypot ")

    # K7 — Tab （tab-btn + ）
    has_tab_btn = re.search(r'tab-btn', content, re.IGNORECASE)
    has_tab_evt = re.search(r'addEventListener.*click|\.tab-btn.*click|click.*tab', content, re.IGNORECASE | re.DOTALL)
    if has_tab_btn and has_tab_evt:
        if verbose: ok("[K7] Tab （tab-btn + ）")
    elif has_tab_btn:
        warnings.append("K7:  tab-btn ，")
    else:
        #  tab 
        if verbose: info("[K7]  tab ，")

    # K8 — （filter  + data-search ）
    has_filter = re.search(r'function filter|filterGrid|filterPrograms|filterAntigens|filterCards', content, re.IGNORECASE)
    has_data_search = re.search(r'data-search=', content, re.IGNORECASE)
    empty_search = len(re.findall(r'data-search=["\']\s*["\']', content))
    if has_filter and has_data_search:
        if empty_search > 0:
            warnings.append(f"K8: filter ， {empty_search}  data-search （）")
        else:
            if verbose: ok("[K8] （filter  + data-search ）")
    elif has_data_search and not has_filter:
        warnings.append("K8:  data-search ， filter ")
    else:
        if verbose: info("[K8] ，")

    # K9 — 
    import datetime
    current_year = str(datetime.datetime.now().year)
    has_year = current_year in content
    has_copyright_text = re.search(
        r'(|unauthorized.*reproduction|All rights reserved|)',
        content, re.IGNORECASE
    )
    if has_year and has_copyright_text:
        if verbose: ok(f"[K9]  {current_year} ")
    elif not has_year:
        warnings.append(f"K9:  {current_year}")
    else:
        warnings.append("K9: ")

    passed = len(fatals) == 0
    return {"fatals": fatals, "warnings": warnings, "passed": passed}


# ──  ────────────────────────────────────────────────────────────────

def validate_site(site_key: str, verbose: bool = True, run_kb: bool = False) -> bool:
    """ HTML 。 True 。"""
    cfg = SITES[site_key]
    header(f"══  {cfg['label']} ({cfg['dir'].name}/) ══")

    html_files = sorted(cfg["dir"].glob("*.html"))
    if not html_files:
        fail(f" {cfg['dir']}  HTML ")
        return False

    info(f" {len(html_files)}  HTML " + (" + KB 9 " if run_kb else ""))

    all_passed = True
    fatal_files = []
    warn_files  = []

    for fpath in html_files:
        result = validate_file(fpath, verbose=False)  # 

        #  KB/Database  KB 
        is_kb = bool(KB_PAGE_PATTERNS.search(fpath.name))
        if run_kb and is_kb:
            kb_result = validate_kb_page(fpath, verbose=False)
            result["fatals"].extend(kb_result["fatals"])
            result["warnings"].extend(kb_result["warnings"])
            if not kb_result["passed"]:
                result["passed"] = False

        status_icon = f"{GREEN}✓{RESET}" if result["passed"] else f"{RED}✗{RESET}"
        warn_icon   = f" {YELLOW}⚠{RESET}" if result["warnings"] else ""
        kb_icon     = f" {CYAN}[KB]{RESET}" if (run_kb and is_kb) else ""
        print(f"  {status_icon}{warn_icon}{kb_icon} {fpath.name} ({result.get('lines', '?')} )")

        if result["fatals"]:
            all_passed = False
            fatal_files.append(result)
            for msg in result["fatals"]:
                fail(f"    FATAL: {msg}")

        if result["warnings"]:
            warn_files.append(result)
            if verbose:
                for msg in result["warnings"]:
                    warn(f"    WARN:  {msg}")

    # 
    _check_nav_consistency(cfg["dir"], html_files)

    print()
    if all_passed:
        ok(f" ({len(html_files)} ，{len(warn_files)} )")
    else:
        fail(f"：{len(fatal_files)}  FATAL ")

    return all_passed


def _check_nav_consistency(site_dir: Path, html_files: list):
    """ HTML 。"""
    nav_blocks = {}
    for fpath in html_files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        m = re.search(r'<nav class="top-header-nav">(.*?)</nav>', content,
                      re.DOTALL | re.IGNORECASE)
        if m:
            # 
            nav_normalized = re.sub(r'\s+', ' ', m.group(1)).strip()
            nav_blocks[fpath.name] = nav_normalized

    if len(nav_blocks) < 2:
        return

    # 
    from collections import Counter
    counts = Counter(nav_blocks.values())
    most_common_nav, most_common_count = counts.most_common(1)[0]

    inconsistent = [name for name, nav in nav_blocks.items() if nav != most_common_nav]
    if inconsistent:
        warn(f"[] {len(inconsistent)} :")
        for name in inconsistent[:5]:
            warn(f"    ↳ {name}")
        if len(inconsistent) > 5:
            warn(f"    ↳ ...  {len(inconsistent)-5} ")
    else:
        ok(f"[]  {len(nav_blocks)} ")


# ──  ──────────────────────────────────────────────────────────────────────

def deploy_site(site_key: str, message: str) -> bool:
    """ PowerShell 。"""
    cfg = SITES[site_key]
    header(f"══  {cfg['label']} ══")

    deploy_script = cfg["deploy"]
    if not deploy_script.exists():
        fail(f": {deploy_script}")
        return False

    cmd = [
        "powershell", "-ExecutionPolicy", "Bypass",
        "-File", str(deploy_script),
        "-Message", message,
    ]

    info(f": {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(SUITE_ROOT))
    if result.returncode == 0:
        ok(f" → {cfg['url']}")
        ok(f" 1 ，: {cfg['url']}?v={_timestamp()}")
        return True
    else:
        fail(f" (exit code {result.returncode})")
        return False


def _timestamp():
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d%H%M")


# ──  ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Therasik/InSynBio  + ",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--site", choices=["therasik", "insynbio", "both"], default="both",
        help="/ (: both)",
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help=" HTML （ Antibody_Engineer_Suite ）",
    )
    parser.add_argument(
        "--deploy", action="store_true",
        help="",
    )
    parser.add_argument(
        "--message", "-m", type=str,
        default=f"site update: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        help="Git commit message",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="",
    )
    parser.add_argument(
        "--kb", action="store_true",
        help="/ K1–K9 ",
    )
    parser.add_argument(
        "--force-deploy", action="store_true",
        help="，（）",
    )
    args = parser.parse_args()

    print(f"\n{BOLD}{'═'*55}{RESET}")
    print(f"{BOLD}  Therasik / InSynBio  v1.1{RESET}")
    print(f"{BOLD}{'═'*55}{RESET}")

    # ──  ─────────────────────────────────────────────────────────
    if args.file:
        fpath = SUITE_ROOT / args.file
        header(f"══ : {fpath.name} ══")
        result = validate_file(fpath, verbose=True)

        #  KB  KB （ --kb ）
        is_kb = bool(KB_PAGE_PATTERNS.search(fpath.name))
        if args.kb or is_kb:
            print()
            kb_result = validate_kb_page(fpath, verbose=True)
            result["fatals"].extend(kb_result["fatals"])
            result["warnings"].extend(kb_result["warnings"])
            if not kb_result["passed"]:
                result["passed"] = False

        print()
        if result["fatals"]:
            for msg in result["fatals"]:
                fail(f"FATAL: {msg}")
        if result["warnings"]:
            for msg in result["warnings"]:
                warn(f"WARN: {msg}")
        if result["passed"]:
            ok(f" ({result.get('lines','?')} )")
        else:
            fail("")
            sys.exit(1)
        return

    # ──  ───────────────────────────────────────────────────────────
    sites_to_process = (
        ["therasik", "insynbio"] if args.site == "both" else [args.site]
    )

    validation_results = {}
    for site in sites_to_process:
        passed = validate_site(site, verbose=args.verbose, run_kb=args.kb)
        validation_results[site] = passed

    # ──  ───────────────────────────────────────────────────────
    print()
    header("══  ══")
    all_passed = all(validation_results.values())
    for site, passed in validation_results.items():
        cfg = SITES[site]
        if passed:
            ok(f"{cfg['label']}: ")
        else:
            fail(f"{cfg['label']}: ")

    # ──  ───────────────────────────────────────────────────────────
    if not args.deploy:
        print()
        if all_passed:
            info("。， --deploy 。")
            info(f": python scripts/validate_website.py --site {args.site} --deploy -m \"feat: \"")
        else:
            fail("，。")
            sys.exit(1)
        return

    if not all_passed and not args.force_deploy:
        print()
        fail("，。 --force-deploy （）。")
        sys.exit(1)

    if not all_passed and args.force_deploy:
        warn("：（）")

    # ──  ───────────────────────────────────────────────────────────
    print()
    header("══  ══")
    deploy_results = {}
    for site in sites_to_process:
        success = deploy_site(site, args.message)
        deploy_results[site] = success

    # ──  ───────────────────────────────────────────────────────
    print()
    header("══  ══")
    all_deployed = all(deploy_results.values())
    for site, success in deploy_results.items():
        cfg = SITES[site]
        if success:
            ok(f"{cfg['label']}:  → {cfg['url']}")
        else:
            fail(f"{cfg['label']}: ")

    if all_deployed:
        print()
        ok(f"！ 1 。")
        for site in sites_to_process:
            ts = _timestamp()
            info(f"  {SITES[site]['url']}?v={ts}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
