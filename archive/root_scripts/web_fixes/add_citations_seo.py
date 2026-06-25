"""
Batch SEO + Citation Enhancement
- Adds citation_* meta tags (Google Scholar indexing)
- Fills missing canonical + Open Graph tags
- Appends "Cite This Work" BibTeX block to case study pages
"""

import os, re

BASE = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source"
BASE_URL = "https://www.insynbio.com"

# ── Page metadata ────────────────────────────────────────────────────────────
PAGES = {
    # --- Case studies ----------------------------------------------------------
    "case_bispecific_vhvl_pairing.html": {
        "og_title":        "Faricimab VPSA Analysis | InSynBio Case Study",
        "description":     "Real VPSA analysis of Faricimab (VEGF-A×ANG-2, Vabysmo®) — InSynBio VH/VL Pairing Stability Assessment reveals arm-specific selectivity in KiH+CrossFab co-expressed bispecifics.",
        "keywords":        "VH/VL pairing, bispecific antibody, Faricimab, VPSA, KiH, CrossFab, mispairing, BSA, packing angle, CCI, InSynBio",
        "citation_title":  "VH/VL Pairing Stability Assessment of Faricimab: A Computational VPSA Analysis of KiH+CrossFab Architecture",
        "citation_date":   "2026/03/25",
        "bibtex_key":      "insynbio2026faricimab_vpsa",
        "bibtex_note":     "VH/VL Pairing Stability Assessment; Faricimab (VEGF-A×ANG-2, Vabysmo\\textsuperscript{\\textregistered}); KiH+CrossFab architecture",
        "is_case_study":   True,
    },
    "case_mumab4d5_humanization_en.html": {
        "og_title":        "MuMAb4D5 Antibody Humanization | InSynBio Case Study",
        "description":     "How InSynBio's AbEngineCore V4.5 pipeline humanized murine MuMAb4D5 antibody via CDR grafting with Vernier-zone optimization and germline back-mutation strategy.",
        "keywords":        "antibody humanization, MuMAb4D5, CDR grafting, murine antibody, germline, VH/VL humanization, AbEngineCore, InSynBio",
        "citation_title":  "VH/VL Murine Antibody Humanization: MuMAb4D5 Case Study Using the AbEngineCore V4.5 Pipeline",
        "citation_date":   "2026/02/01",
        "bibtex_key":      "insynbio2026mumab_human",
        "bibtex_note":     "CDR grafting; Vernier-zone optimization; germline back-mutation",
        "is_case_study":   True,
    },
    "case_mumab4d5_cmc.html": {
        "og_title":        "MuMAb4D5 CMC Developability Assessment | InSynBio",
        "description":     "Full CMC developability report for MuMAb4D5: aggregation propensity, pI, hydrophobic patches, deamidation, oxidation, and CDR post-translational modification risk.",
        "keywords":        "CMC, developability, MuMAb4D5, aggregation, pI, SAP, PSH, deamidation, oxidation, antibody manufacturability, InSynBio",
        "citation_title":  "Computational CMC Developability Assessment of MuMAb4D5: Multi-metric Antibody Manufacturability Analysis",
        "citation_date":   "2026/02/01",
        "bibtex_key":      "insynbio2026mumab_cmc",
        "bibtex_note":     "Aggregation propensity; pI; SAP/PSH patches; PTM risk scoring",
        "is_case_study":   True,
    },
    "case_mumab4d5_vhh_en.html": {
        "og_title":        "MuMAb4D5 VH-to-VHH Conversion | InSynBio Case Study",
        "description":     "Converting murine MuMAb4D5 VH domain to a functional VHH nanobody using InSynBio's Nano-Convert™ camelization pipeline: hallmark residue engineering and VHH CDR adaptation.",
        "keywords":        "VHH, nanobody, VH to VHH, camelization, MuMAb4D5, single-domain antibody, Nano-Convert, CDR adaptation, InSynBio",
        "citation_title":  "VH-to-VHH Camelization of MuMAb4D5 Using the Nano-Convert™ Pipeline",
        "citation_date":   "2026/02/10",
        "bibtex_key":      "insynbio2026mumab_vhh",
        "bibtex_note":     "Hallmark residue substitution; VHH CDR3 loop adaptation; developability QC",
        "is_case_study":   True,
    },
    "case_vgrw_sr_r2_affinity_maturation.html": {
        "og_title":        "VGRw SR-R2 Virtual Affinity Maturation | InSynBio",
        "description":     "Virtual affinity maturation of VGRw SR-R2 antibody using InSynBio's 6-tool ΔΔG consensus pipeline: EvoEF2, PRODIGY, ThermoMPNN, AntiFold, ESM-IF1, and HADDOCK3 refinement.",
        "keywords":        "affinity maturation, ΔΔG, EvoEF2, PRODIGY, ThermoMPNN, AntiFold, ESM-IF1, HADDOCK3, mutation scanning, binding energy, InSynBio",
        "citation_title":  "Virtual Affinity Maturation of SR-R2: Multi-tool ΔΔG Consensus Pipeline for Antibody Optimization",
        "citation_date":   "2026/03/01",
        "bibtex_key":      "insynbio2026sr_r2_affmat",
        "bibtex_note":     "6-tool ΔΔG consensus; EvoEF2; PRODIGY; ThermoMPNN; AntiFold; ESM-IF1",
        "is_case_study":   True,
    },
    "case_bispecific_vhh_expression_optimization.html": {
        "og_title":        "Bispecific VHH Expression Optimization | InSynBio",
        "description":     "Resolving low yeast expression in a dual-coronavirus VHH bispecific through pI engineering and charged-linker design using SmartLink™ and Virtual CMC.",
        "keywords":        "bispecific VHH, nanobody, yeast expression, pI engineering, SmartLink, CMC, coronavirus, linker optimization, InSynBio",
        "citation_title":  "Engineering Expression Recovery of a Dual-Coronavirus Bispecific VHH via pI Optimization and Charged-Linker Design",
        "citation_date":   "2026/01/15",
        "bibtex_key":      "insynbio2026bispecific_vhh_expr",
        "bibtex_note":     "pI-driven ER retention rescue; SmartLink charged-linker; yeast expression optimization",
        "is_case_study":   True,
    },
    "case_malaria_carm_design.html": {
        "og_title":        "Anti-CIDRα1 CAR-Macrophage Design | InSynBio",
        "description":     "Rationally designed CAR-Macrophage targeting PfEMP1 CIDRα1 for cerebral malaria, using ACTES engine and InSynBio Knowledge Engine for domain selection and payload engineering.",
        "keywords":        "CAR-macrophage, CAR-M, malaria, PfEMP1, CIDRα1, cerebral malaria, ACTES, immunotherapy, InSynBio",
        "citation_title":  "Rational Design of an Anti-CIDRα1 CAR-Macrophage for Cerebral Malaria Using the ACTES Engine",
        "citation_date":   "2026/02/20",
        "bibtex_key":      "insynbio2026malaria_carm",
        "bibtex_note":     "CAR-macrophage; PfEMP1 CIDRα1 antigen; cerebral malaria immunotherapy",
        "is_case_study":   True,
    },
    # --- Knowledge / reference pages -------------------------------------------
    "immunogenicity_study.html": {
        "og_title":        "Clinical Antibody Immunogenicity Study | InSynBio",
        "description":     "InSynBio multi-metric immunogenicity assessment: T-cell epitope prediction, germline identity scoring, and ADA risk stratification across 120+ validated clinical records.",
        "keywords":        "immunogenicity, ADA, T-cell epitope, MHC-II, germline identity, CDR composition, antibody immunogenicity, IEDB, InSynBio",
        "citation_title":  "Multi-metric Immunogenicity Risk Assessment for Therapeutic Antibodies: T-cell Epitope Analysis and ADA Prediction",
        "citation_date":   "2026/03/10",
        "bibtex_key":      "insynbio2026immunogenicity",
        "bibtex_note":     "T-cell epitope scoring; IEDB API; germline identity; ADA risk stratification",
        "is_case_study":   False,
    },
    "antibody-guide.html": {
        "og_title":        "Antibody Engineering Reference | InSynBio",
        "description":     "Comprehensive reference covering Fc mutations (ADCC/CDC/FcRn), developability metrics (pI, SAP, PSH, deamidation), and immunogenicity factors with patent and experimental context.",
        "keywords":        "Fc mutations, antibody developability, immunogenicity, ADCC, CDC, FcRn, LALA, LS/YTE, SAP, deamidation, InSynBio",
        "citation_title":  "Antibody Engineering Reference: Fc Mutations, Developability Assessment Metrics, and Immunogenicity Factors",
        "citation_date":   "2026/02/01",
        "bibtex_key":      "insynbio2026abguide",
        "bibtex_note":     "Fc mutation compendium; CMC developability metrics; immunogenicity factors; patent status",
        "is_case_study":   False,
    },
    "ada_database.html": {
        "og_title":        "Clinical ADA Database | InSynBio",
        "description":     "InSynBio's clinical ADA (anti-drug antibody) database: 120+ immunogenicity records from approved and clinical-stage therapeutic antibodies, with incidence rates and risk stratification.",
        "keywords":        "ADA, anti-drug antibody, immunogenicity database, clinical antibody, ADA incidence, therapeutic antibody, InSynBio",
        "citation_title":  "InSynBio Clinical ADA Database: 120+ Validated Immunogenicity Records for Therapeutic Antibodies",
        "citation_date":   "2026/03/01",
        "bibtex_key":      "insynbio2026ada_db",
        "bibtex_note":     "ADA incidence database; 120+ clinical records; risk stratification benchmarks",
        "is_case_study":   False,
    },
    "component-browser.html": {
        "og_title":        "CAR-T Component Browser | InSynBio ACTES",
        "description":     "Interactive browser of InSynBio's 237-component CAR-T engineering library: antigen binders, costimulatory domains, safety switches, linkers, signal peptides, and delivery vectors.",
        "keywords":        "CAR-T components, CAR design, costimulatory domain, safety switch, antigen binder, 4-1BB, CD28, ACTES, InSynBio",
        "citation_title":  "InSynBio ACTES CAR-T Component Library: 237 Annotated Engineering Elements for Chimeric Antigen Receptor Design",
        "citation_date":   "2026/01/01",
        "bibtex_key":      "insynbio2026cart_components",
        "bibtex_note":     "237 CAR-T components; ACTES engine; antigen binders; safety switches; delivery vectors",
        "is_case_study":   False,
    },
}

# Cite-This-Work block template (filled per page)
CITE_BLOCK_TPL = """\
  <!-- Cite This Work -->
  <section style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:28px 0 24px;">
    <div style="max-width:900px;margin:0 auto;padding:0 24px;">
      <details style="border:1px solid #e5e7eb;border-radius:10px;background:#fff;padding:0;">
        <summary style="padding:14px 18px;font-size:13px;font-weight:700;color:#374151;cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          Cite This Work
        </summary>
        <div style="padding:4px 18px 18px;border-top:1px solid #f3f4f6;">
          <p style="font-size:12px;color:#6b7280;margin:12px 0 10px;">If you reference this analysis, please cite as:</p>
          <pre style="background:#f3f4f6;border-radius:8px;padding:14px 16px;font-size:12px;line-height:1.7;overflow-x:auto;color:#111827;margin:0;">@techreport{{BIBTEX_KEY,
  title     = {{{{{CITATION_TITLE}}}}},
  author    = {{InSynBio}},
  year      = {{{YEAR}}},
  month     = {{{MONTH}}},
  institution = {{InSynBio}},
  note      = {{{{{BIBTEX_NOTE}}}}},
  url       = {{{{{URL}}}}}
}}</pre>
          <p style="font-size:11.5px;color:#9ca3af;margin:10px 0 0;">InSynBio computational analyses are for research reference only. Please verify results before clinical application.</p>
        </div>
      </details>
    </div>
  </section>
"""


def build_citation_block(meta, url):
    date_parts = meta["citation_date"].split("/")
    year = date_parts[0]
    month_num = int(date_parts[1]) if len(date_parts) > 1 else 1
    months = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
    month = months[month_num - 1]
    return (CITE_BLOCK_TPL
        .replace("{BIBTEX_KEY",  "{" + meta["bibtex_key"])
        .replace("{CITATION_TITLE}", meta["citation_title"])
        .replace("{YEAR}",  year)
        .replace("{MONTH}", month)
        .replace("{BIBTEX_NOTE}", meta.get("bibtex_note", "InSynBio computational analysis"))
        .replace("{URL}",   url)
    )


def build_og_canonical(filename, meta):
    url = f"{BASE_URL}/{filename}"
    lines = [
        f'  <link rel="canonical" href="{url}">',
        f'  <meta property="og:type" content="article">',
        f'  <meta property="og:url" content="{url}">',
        f'  <meta property="og:title" content="{meta["og_title"]}">',
        f'  <meta property="og:description" content="{meta["description"]}">',
        f'  <meta property="og:image" content="{BASE_URL}/images/hero-bg.svg">',
    ]
    return "\n".join(lines)


def build_citation_meta(filename, meta):
    url = f"{BASE_URL}/{filename}"
    lines = [
        f'  <meta name="citation_title" content="{meta["citation_title"]}">',
        f'  <meta name="citation_author" content="InSynBio">',
        f'  <meta name="citation_publisher" content="InSynBio">',
        f'  <meta name="citation_online_date" content="{meta["citation_date"]}">',
        f'  <meta name="citation_publication_date" content="{meta["citation_date"]}">',
        f'  <meta name="citation_language" content="en">',
        f'  <meta name="citation_abstract_html_url" content="{url}">',
    ]
    return "\n".join(lines)


def process(filename, meta):
    path = os.path.join(BASE, filename)
    if not os.path.exists(path):
        print(f"  SKIP (not found): {filename}")
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    changes = []
    url = f"{BASE_URL}/{filename}"

    # 1. Add canonical + OG if missing
    if 'rel="canonical"' not in content:
        og_block = build_og_canonical(filename, meta)
        # Insert after <meta name="description"...> or after <meta name="viewport"...>
        pattern = r'(<meta name="description"[^>]+>)'
        if re.search(pattern, content):
            content = re.sub(pattern, r'\1\n' + og_block, content, count=1)
        else:
            content = re.sub(r'(<meta name="viewport"[^>]+>)', r'\1\n' + og_block, content, count=1)
        changes.append("canonical+OG added")

    # 2. Add citation_* meta if missing
    if 'citation_title' not in content:
        cite_meta = build_citation_meta(filename, meta)
        # Insert before </head>
        content = content.replace("</head>", cite_meta + "\n</head>", 1)
        changes.append("citation_* meta added")

    # 3. Also ensure keywords meta exists
    if 'name="keywords"' not in content and meta.get("keywords"):
        kw_tag = f'  <meta name="keywords" content="{meta["keywords"]}">\n'
        content = content.replace("</head>", kw_tag + "</head>", 1)
        changes.append("keywords meta added")

    # 4. Add "Cite This Work" block to case studies (before </body>)
    if meta.get("is_case_study") and 'Cite This Work' not in content:
        cite_block = build_citation_block(meta, url)
        # Insert before closing </body> or before last <footer> or before </main>
        if '</footer>' in content:
            # insert before first </footer>
            content = content.replace('</footer>', cite_block + '\n  </footer>', 1)
        elif '</main>' in content:
            idx = content.rfind('</main>')
            content = content[:idx] + cite_block + content[idx:]
        else:
            content = content.replace('</body>', cite_block + '\n</body>', 1)
        changes.append("Cite This Work block added")

    if changes:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  OK  {filename}: {', '.join(changes)}")
        return True
    else:
        print(f"  --  {filename}: no changes needed")
        return False


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  InSynBio SEO + Citation Enhancement")
    print("=" * 60)
    updated = []
    for fname, meta in PAGES.items():
        if process(fname, meta):
            updated.append(fname)
    print(f"\nUpdated {len(updated)}/{len(PAGES)} files:")
    for f in updated:
        print(f"  {f}")
