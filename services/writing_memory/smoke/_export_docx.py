"""
Build the /export_docx POST body from the figdraft JSON and call the API.
Outputs: huNSG_QUAD_manuscript.docx  (next to this script)
"""
import base64, json, re, urllib.request, urllib.error
from pathlib import Path

SRC = Path(__file__).parent / "huNSG_QUAD_revised.json"
OUT = Path(__file__).parent / "huNSG_QUAD_revised_manuscript.docx"
BASE = "https://write.insynbio.com"
AUTH = "Admin:Rocky123"

d = json.loads(SRC.read_text(encoding="utf-8"))
secs = {s["key"]: s for s in d["sections"]}
refs = d.get("merged_reference_list") or []
plan = d.get("plan") or {}

TITLE = (
    plan.get("suggested_title")
    or "Development of human innate immune responses in a humanized mouse model "
       "expressing four human myelopoiesis transgenes"
)

# Figure legends extracted from expert article descriptions
FIG_LEGENDS = [
    {
        "figure_number": 1,
        "title": "Human myeloid cell engraftment in NSG-QUAD mice",
        "rendered_full": (
            "(A) Experimental timeline. NSG-QUAD mice were sublethally irradiated and "
            "reconstituted with human CD34+ HSPCs at week 0. Peripheral blood was assessed at "
            "week 5; inflammatory challenge experiments were performed at week 6. "
            "(B-C) Flow cytometric analysis of human CD45+ immune cell subsets in peripheral blood "
            "at weeks 5 (B) and 6 (C). Data show monocytes (~18%), dendritic cells (~12%), "
            "granulocytes (~9%), and T/B cells. "
            "(D-E) Myeloid cell engraftment in spleen (D) and liver (E) at week 6. "
            "(F) Peripheral blood monocyte subsets: classical (CD14++CD16-, ~47%), "
            "intermediate (CD14++CD16+, ~20%), and non-classical (CD14+CD16++, ~10%). "
            "n = 6–9 per group. Data are mean ± SEM."
        ),
    },
    {
        "figure_number": 2,
        "title": "NF-κB and type I interferon responses to LPS in huNSG-QUAD mice",
        "rendered_full": (
            "(A) Serum NF-κB-dependent cytokines after IP LPS (15 μg/mouse): "
            "hTNF ~50 ng/ml (***), hIL-6 ~8 ng/ml (***), hIL-8 ~10 ng/ml (***). "
            "(B) Liver cytokines after IP LPS. "
            "(C) Lung cytokines after intranasal LPS (6 mg/kg). "
            "(D-E) Serum and liver type I IFN markers (hIFNα2, hCXCL10) after IP LPS. "
            "(F) Lung hIFNα2 and hCXCL10 after intranasal LPS. "
            "Statistics: two-way ANOVA with Sidak's correction. ***p<0.001; ns, not significant. "
            "n = 6–7 per group. Data are mean ± SEM."
        ),
    },
    {
        "figure_number": 3,
        "title": "NLRP3 inflammasome activation in huNSG-QUAD mice",
        "rendered_full": (
            "(A) Serum hIL-1β (~12-fold induction, ***), hIL-18 (ns), and NF-κB cytokines "
            "after IP LPS. "
            "(B) BAL fluid hIL-1β (~125-fold induction, ***) and hIL-18 (ns) after intranasal LPS. "
            "(C) Splenic human granulocyte (***), monocyte, and DC counts after IP LPS. "
            "(D) Liver cytokines including hIL-1β (~14-fold, ***) and hIL-18 (ns) after IP LPS. "
            "Statistics: two-way ANOVA with Sidak's correction. ***p<0.001; ns, not significant. "
            "n = 6–7 per group. Data are mean ± SEM."
        ),
    },
    {
        "figure_number": 4,
        "title": "MCC950 selectively inhibits inflammasome cytokines without cytotoxicity",
        "rendered_full": (
            "(A-D) Pre-treatment verification of comparable engraftment across PBS, LPS, "
            "and LPS+MCC950 groups (all ns). "
            "(E-F) MCC950 (50 mg/kg, 1 h pre-LPS) reduced serum hIL-1β (~50 pg/ml vs ~180 pg/ml "
            "LPS alone, ***) and hIL-18 (~10 pg/ml vs ~35 pg/ml, *). "
            "(G-H) hTNF and hIL-6 unaffected by MCC950 (ns vs LPS). "
            "(I-J) Monocyte frequency and absolute counts reduced by LPS but not rescued by MCC950. "
            "(K-L) Dead monocyte percentages and absolute counts. "
            "Statistics: two-way ANOVA with Sidak's correction. ***p<0.001; **p<0.01; *p<0.05; "
            "ns, not significant. n = 6–9 per group. Data are mean ± SEM."
        ),
    },
]

# Load figure images as base64
FIG_IMAGES = []
for i in range(1, 5):
    p = Path(rf"C:\Temp\fig{i}.webp")
    if p.exists():
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        FIG_IMAGES.append({
            "figure_number": i,
            "image_b64": b64,
            "media_type": "image/webp",
            "width_cm": 14.0,
        })

body = {
    "title": TITLE,
    "target_journal": "elife",
    "article_type": "research",
    "authors": "[FILL: Author names, affiliations]",
    "abstract_text": secs["abstract"]["text"],
    "sections": [
        {"key": k, "title": k.title(), "text": secs[k]["text"]}
        for k in ("introduction", "methods", "results", "discussion")
    ],
    "reference_list": refs,
    "figure_legends": FIG_LEGENDS,
    "figure_images": FIG_IMAGES,
    "declarations": {
        "data_availability": "[FILL: Data availability statement — accession numbers or repository]",
        "competing_interests": "The authors declare no competing interests.",
        "ethics_statement": (
            "Animal experiments were approved by the Institutional Animal Ethics Committee "
            "(protocol EC2022-003, VIB-UGent). Human cord blood use was approved under "
            "protocol BC-06143 (Medical Ethical Committee, Ghent University Hospital). "
            "All procedures complied with national and European regulations."
        ),
        "funding_statement": "[FILL: Funding sources and grant numbers]",
        "author_contributions": [],
        "author_contributions_text": "[FILL: CRediT author contribution statement]",
    },
}

auth_token = base64.b64encode(AUTH.encode()).decode()
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {auth_token}",
}
payload = json.dumps(body).encode()
req = urllib.request.Request(f"{BASE}/export_docx", data=payload, headers=headers, method="POST")

print(f"Sending request ({len(payload)//1024} KB) …")
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        docx_bytes = resp.read()
except urllib.error.HTTPError as e:
    err = e.read().decode(errors="replace")[:500]
    print(f"HTTP {e.code}: {err}")
    raise

OUT.write_bytes(docx_bytes)
print(f"Saved {len(docx_bytes)//1024} KB → {OUT}")
