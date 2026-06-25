"""
normalize_hero_css.py  ── 2026-04-07
Ensure ALL 5 KB pages have identical .page-header CSS:
  h1: 38px, #0d4a43, Cormorant Garamond
  p:  15px, #2d6a61, max-width 720px, line-height 1.65
  mobile h1: 26px
Remove legacy duplicate rules on ADC and Vaccine pages.
"""
import re

# ── Canonical rules to enforce ────────────────────────────────────────────────
CANONICAL_H1  = "font-family: 'Cormorant Garamond', serif; font-size: 38px; font-weight: 700; margin: 0 0 10px; letter-spacing: -0.02em; color: #0d4a43;"
CANONICAL_P   = "color: #2d6a61; font-size: 15px; max-width: 720px; line-height: 1.65; margin: 0 0 16px;"
CANONICAL_MOB_H1 = "font-size: 26px;"   # mobile breakpoint h1

# ── Patterns that must be removed (old conflicting rules) ─────────────────────
# These were left over from before the upgrade_page_headers.py injection
OLD_H1_RULES = [
    r"\.page-header h1\s*\{\s*font-family:'Cormorant Garamond',serif;\s*font-size:36px;[^}]*\}\s*\n?",
    r"\.page-header p\s*\{\s*font-size:15px;\s*color:var\(--text-muted\);\s*margin:0;\s*max-width:750px;\s*line-height:1\.7;\s*\}\s*\n?",
    r"\.page-header p\s*\{\s*font-size:15px;\s*color:var\(--text-muted\);\s*margin:0;\s*\}\s*\n?",
]

# ── Per-page overrides to fix ─────────────────────────────────────────────────
# These exist on Guide and CAR – wrong font-size and color for p
WRONG_P_RULES = [
    # Guide / CAR style (17px, var(--text-muted), various max-width)
    (
        r"(\.page-header p\s*\{)[^}]*(color:var\(--text-muted\);font-size:17px;[^}]*)\}",
        lambda m: f".page-header p {{ {CANONICAL_P} }}"
    ),
    # Any remaining .page-header p with wrong color/size
    (
        r"(\.page-header p\s*\{\s*)color:var\(--text-muted\);(\s*font-size:\d+px;[^}]*)\}",
        None  # handled separately below
    ),
]

FILES = [
    "docs/Therasik_ADA_Database.html",
    "docs/Therasik_ADC_Database.html",
    "docs/Therasik_Antibody_Guide.html",
    "docs/Therasik_Component_Browser.html",
    "docs/Therasik_Vaccine_KB.html",
]

for path in FILES:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    orig = content

    # 1. Remove legacy duplicate old rules (ADC/Vaccine leftover)
    for pat in OLD_H1_RULES:
        content = re.sub(pat, '', content)

    # 2. Fix wrong .page-header p rules (17px / var(--text-muted))
    #    Pattern: .page-header p { ...any values... } where color is NOT #2d6a61
    def fix_p_rule(m):
        inner = m.group(1)
        # Only fix if it doesn't already have the canonical values
        if '#2d6a61' in inner and '15px' in inner:
            return m.group(0)  # already correct, skip
        return f".page-header p {{ {CANONICAL_P} }}"

    content = re.sub(
        r'\.page-header p\s*\{([^}]+)\}',
        fix_p_rule,
        content
    )

    # 3. Ensure .page-header h1 is canonical (fix any remaining wrong h1 color/size)
    def fix_h1_rule(m):
        inner = m.group(1)
        if '#0d4a43' in inner and '38px' in inner:
            return m.group(0)  # already correct
        return f".page-header h1 {{ {CANONICAL_H1} }}"

    content = re.sub(
        r'\.page-header h1\s*\{([^}]+)\}',
        fix_h1_rule,
        content
    )

    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Fixed: {path}")
    else:
        print(f"– Unchanged: {path}")

print("\nDone. Re-auditing…")
