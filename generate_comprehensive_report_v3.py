import json
import sys
from pathlib import Path
from datetime import datetime

suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys, is_in_cdr
from anarci import anarci

# 1. Sequences with Corrected Dog FR4
# VH FR4: WGQGTLVTVSS
# VL Kappa FR4: FGQGTKVELK
# VL Lambda FR4: FGGGTHLTVL

tanezumab_vh = "QVQLQESGPGLVRPSQTLSLTCTVSGFSLIGYDLNWVRQPPGRGLEWIGIIWGDGTTDYNSAVKSRVTMLKDTSKNQFSLRLSSVTAADTAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
tanezumab_vl = "DIQMTQSPSSLSASVGDRVTITCRASQSISNNLNWYQQKPGKAPKLLIYYTSRFHSGVPSRFSGSGSGTDFTFTISSLQPEDIATYYCQQEHTLPYTFGQGTKLEIK"

bedin_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFTFSSHGMHWVRQSPGKGLQWVAVINSGGSSTYYTDAVKGRFTISRDNAKNTVYLQMNSLRAEDTAMYYCAKESVGGWEQLVGPHFDYWGQGTLVIVSS"
bedin_vl = "QSVLTQPTSVSGSLGQRVTISCSGSTNNIGILGASWYQLFPGKAPKLLVYGNGNRPSGVPDRFSGADSGDSVTLTITGLQAEDEADYYCQSFDTTLGAHVFGGGTHLTVL"

v3b_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWVAIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
v3b_vl = "EIVLTQSPASLSLSQEEKVTITCRASQSISNNLNWYQQKPGQAPKLLIYYTSRFHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQEHTLPYTFGQGTKVELK"

v3c_vh = v3b_vh # V3c (ex-V5b)
v3c_vl = v3b_vl

v4_vh = "EVQLVESGGDLVKPAGSLRLSCVASGFSLIGYDLNWVRQAPEKGLQLVAIIWGDGTTDYNSAVKSRFTISKDFAKNTVYLQMRAEDTAMYYCAKGGYWYATSYYFDYWGQGTLVTVSS"
v4_vl = "QSVLTQPTSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVYYTSRFHSGVPDRFSGSNSGNSATLTITGLQAEDEADYYCQQEHTLPYTFGGGTHLTVL"

v4b_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWVAIIWGDGTTDYNSAVKSRFTISKDNAKNTFYLQMNSLRAEDTAVYYCAKGGYWYATSYYFDYWGQGTLVTVSS"
v4b_vl = "QSVLTQPASSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVDYTSRFHSGVPDRFSGSGSGTSATLTISGLQAEDEADYYQQEHTLPYTFGGGTHLTVL"

# 2. Components
hc_sig = "MGWSCIILFLVATATGVHS" 
lc_sig = "METDTLLLWVLLLWVPGSTG"
dog_iggb_const = "ASTTAPSVFPLAPSCGSTSGSTVALACLVSGYFPEPVTVSWNSGSLTSGVHTFPSVLQSSGLYSLSSMVTVPSSRWPSETFTCNVAHPASKTKVDKPVPKRENGRVPRPPDCPKCPAPEMLGGPSVFIFPPKPKDTLLIARTPEVTCVVVDLDPEDPEVQISWFVDGKQMQTAKTQPREEQFNGTYRVVSVLPIGHQDWLKGKQFTCKVNNKALPSPIERTISKARGQAHQPSVYVLPPSREELSKNTVSLTCLIKDFFPPDIDVEWQSNGQQEPESKYRTTPPQLDEDGSYFLYSKLSVDKSRWQRGDTFICAVMHEALHNHYTQKSLSHSPGK"
dog_kappa_const = "RNDAQPAVYLFQPSPDQLHTGSASVVCLLNSFYPKDINVKWKVDGVIQDTGIQESVTEQDKDSTYSLSSTLTMSSTEYLSHELYSCEITHKSLPSTLIKSFQRSECQRVD"
dog_lambda_const = "GQPKSSPLVTLFPPSSEELGANKATLVCLISDFYPSGLKVAWKADGSTIIQGVETTKPSKQSNNKYTASSYLSLTPDKWKSHSSFSCLVTHQGSTVEKKVAPAECS"

dog_opt_table = {
    'A': 'GCC', 'C': 'TGC', 'D': 'GAC', 'E': 'GAG', 'F': 'TTC', 'G': 'GGC', 'H': 'CAC', 'I': 'ATC', 'K': 'AAG', 'L': 'CTG',
    'M': 'ATG', 'N': 'AAC', 'P': 'CCC', 'Q': 'CAG', 'R': 'CGC', 'S': 'TCC', 'T': 'ACC', 'V': 'GTC', 'W': 'TGG', 'Y': 'TAC',
    '*': 'TGA'
}

def optimize_cdna(protein_seq):
    return "".join(dog_opt_table.get(aa, "NNN") for aa in protein_seq)

def get_segments(seq, chain):
    results = anarci([("seq", seq)], scheme="kabat")
    if results[0] and results[0][0]:
        numbering = results[0][0][0][0]
        kd = {}
        for (pos, ins), aa in numbering:
            kd[(pos, ins.strip())] = aa
        
        regions = {"FR1": "", "CDR1": "", "FR2": "", "CDR2": "", "FR3": "", "CDR3": "", "FR4": ""}
        if chain == "VH":
            r_map = {"FR1": (1, 25), "CDR1": (26, 35), "FR2": (36, 49), "CDR2": (50, 65), "FR3": (66, 94), "CDR3": (95, 102), "FR4": (103, 113)}
        else:
            r_map = {"FR1": (1, 23), "CDR1": (24, 34), "FR2": (35, 49), "CDR2": (50, 56), "FR3": (57, 88), "CDR3": (89, 97), "FR4": (98, 107)}
        
        for r_name, (lo, hi) in r_map.items():
            regions[r_name] = "".join(kd[k] for k in sorted_keys(kd) if lo <= k[0] <= hi)
        return regions, kd
    return None, None

def calculate_similarity(kd1, kd2, chain, region_type):
    matches = 0
    total = 0
    all_pos = sorted(set(kd1.keys()) | set(kd2.keys()))
    for k in all_pos:
        pos, ins = k
        in_cdr = is_in_cdr(pos, chain)
        if region_type == 'CDR' and in_cdr:
            total += 1
            if kd1.get(k) == kd2.get(k): matches += 1
        elif region_type == 'FR' and not in_cdr:
            if (chain == "VH" and pos <= 94) or (chain == "VL" and pos <= 88):
                total += 1
                if kd1.get(k) == kd2.get(k): matches += 1
    return (matches / total * 100) if total > 0 else 0

# 5. Process Data
variants = {
    "Tanezumab": (tanezumab_vh, tanezumab_vl, "kappa"),
    "Bedinvetmab": (bedin_vh, bedin_vl, "lambda"),
    "V3b": (v3b_vh, v3b_vl, "kappa"),
    "V3c": (v3c_vh, v3c_vl, "kappa"),
    "V4": (v4_vh, v4_vl, "lambda"),
    "V4b": (v4b_vh, v4b_vl, "lambda")
}

report_data = {}
bedin_vh_seg, bedin_vh_kd = get_segments(bedin_vh, "VH")
bedin_vl_seg, bedin_vl_kd = get_segments(bedin_vl, "VL")

for name, (vh, vl, lc_type) in variants.items():
    vh_seg, vh_kd = get_segments(vh, "VH")
    vl_seg, vl_kd = get_segments(vl, "VL")
    
    vh_fr_sim = calculate_similarity(vh_kd, bedin_vh_kd, "VH", "FR")
    vh_cdr_sim = calculate_similarity(vh_kd, bedin_vh_kd, "VH", "CDR")
    vl_fr_sim = calculate_similarity(vl_kd, bedin_vl_kd, "VL", "FR")
    vl_cdr_sim = calculate_similarity(vl_kd, bedin_vl_kd, "VL", "CDR")
    
    vh_full = hc_sig + vh + dog_iggb_const
    cl_const = dog_kappa_const if lc_type == "kappa" else dog_lambda_const
    vl_full = lc_sig + vl + cl_const
    
    report_data[name] = {
        "vh_segments": vh_seg,
        "vl_segments": vl_seg,
        "vh_full": vh,
        "vl_full": vl,
        "sim_vs_bedin": {
            "vh_fr": vh_fr_sim,
            "vh_cdr": vh_cdr_sim,
            "vl_fr": vl_fr_sim,
            "vl_cdr": vl_cdr_sim
        },
        "protein": {"HC": vh_full, "LC": vl_full},
        "cdna": {"HC": optimize_cdna(vh_full), "LC": optimize_cdna(vl_full)}
    }

# 6. Generate HTML
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Tanezumab Caninization — Comprehensive Engineering Report | InSynBio</title>
<style>
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f8fafc;color:#1e293b;font-size:13px;line-height:1.5;padding:20px;}}
.wrap{{max-width:1200px;margin:0 auto;background:#fff;padding:30px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.1);}}
.hdr{{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:25px;border-radius:8px 8px 0 0;margin:-30px -30px 20px -30px;}}
h1{{font-size:22px;margin:0;}}
h2{{font-size:16px;color:#1e3a5f;border-left:4px solid #2563eb;padding-left:10px;margin:25px 0 15px 0;}}
table{{width:100%;border-collapse:collapse;margin-bottom:20px;}}
th{{background:#f1f5f9;text-align:left;padding:8px;border-bottom:2px solid #e2e8f0;font-weight:bold;}}
td{{padding:8px;border-bottom:1px solid #f1f5f9;}}
.seq-box{{font-family:Consolas,monospace;font-size:11px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:4px;padding:10px;word-break:break-all;margin-top:5px;white-space:pre-wrap;}}
.cdr{{color:#2563eb;font-weight:bold;}}
.fr{{color:#64748b;}}
.sim-high{{color:#166534;font-weight:bold;}}
.sim-low{{color:#991b1b;font-weight:bold;}}
</style>
</head>
<body>
<div class="wrap">
<div class="hdr">
    <h1>Tanezumab Caninization — Comprehensive Engineering Report</h1>
    <p>Final Variants: V3c (ex-V5b), V4b (ex-V5) vs Tanezumab & Bedinvetmab</p>
</div>

<h2>§1 Similarity Matrix vs Bedinvetmab (Dog Reference)</h2>
<p style="color:#64748b;margin-bottom:10px;">V3c (Kappa-based) and V4b (Lambda-based) represent the final optimized candidates.</p>
<table>
    <tr>
        <th>Variant</th>
        <th>VH Framework Similarity</th>
        <th>VH CDR Similarity</th>
        <th>VL Framework Similarity</th>
        <th>VL CDR Similarity</th>
        <th>Overall Verdict</th>
    </tr>
"""

for name in ["Tanezumab", "V3b", "V3c", "V4", "V4b"]:
    s = report_data[name]["sim_vs_bedin"]
    html += f"""
    <tr>
        <td>{name}</td>
        <td class="{'sim-high' if s['vh_fr']>80 else ''}">{s['vh_fr']:.1f}%</td>
        <td class="{'sim-low' if s['vh_cdr']<50 else ''}">{s['vh_cdr']:.1f}%</td>
        <td class="{'sim-high' if s['vl_fr']>80 else ''}">{s['vl_fr']:.1f}%</td>
        <td class="{'sim-low' if s['vl_cdr']<50 else ''}">{s['vl_cdr']:.1f}%</td>
        <td>{"FTO Safe (Low CDR Sim)" if s['vh_cdr']<50 else "Review Needed"}</td>
    </tr>
    """

html += """
</table>

<h2>§2 Local Segmentation Comparison (Kabat)</h2>
<h3>Heavy Chain (VH)</h3>
<table>
    <tr><th>Variant</th><th>FR1</th><th>CDR1</th><th>FR2</th><th>CDR2</th><th>FR3</th><th>CDR3</th><th>FR4</th></tr>
"""
for name in ["Tanezumab", "Bedinvetmab", "V3b", "V3c", "V4", "V4b"]:
    r = report_data[name]["vh_segments"]
    html += f"<tr><td>{name}</td><td class='fr'>{r['FR1']}</td><td class='cdr'>{r['CDR1']}</td><td class='fr'>{r['FR2']}</td><td class='cdr'>{r['CDR2']}</td><td class='fr'>{r['FR3']}</td><td class='cdr'>{r['CDR3']}</td><td class='fr'>{r['FR4']}</td></tr>"

html += """
</table>
<h3>Light Chain (VL)</h3>
<table>
    <tr><th>Variant</th><th>FR1</th><th>CDR1</th><th>FR2</th><th>CDR2</th><th>FR3</th><th>CDR3</th><th>FR4</th></tr>
"""
for name in ["Tanezumab", "Bedinvetmab", "V3b", "V3c", "V4", "V4b"]:
    r = report_data[name]["vl_segments"]
    html += f"<tr><td>{name}</td><td class='fr'>{r['FR1']}</td><td class='cdr'>{r['CDR1']}</td><td class='fr'>{r['FR2']}</td><td class='cdr'>{r['CDR2']}</td><td class='fr'>{r['FR3']}</td><td class='cdr'>{r['CDR3']}</td><td class='fr'>{r['FR4']}</td></tr>"

html += """
</table>

<h2>§3 Final Deliverables (V3c & V4b)</h2>
<div style="margin-top:15px; border:1px solid #2563eb; padding:15px; border-radius:8px; background:#f0f7ff; margin-bottom:20px;">
    <h3 style="color:#1e3a5f;margin-top:0;">Variant: V3c (DeepFR-CTX on V3b/Kappa Scaffold)</h3>
    <strong>Heavy Chain Protein</strong>
    <div class="seq-box">{report_data['V3c']['protein']['HC']}</div>
    <strong>Light Chain Protein (Dog Kappa)</strong>
    <div class="seq-box">{report_data['V3c']['protein']['LC']}</div>
    <strong>HC cDNA (Dog Optimized)</strong>
    <div class="seq-box">{report_data['V3c']['cdna']['HC']}</div>
    <strong>LC cDNA (Dog Optimized)</strong>
    <div class="seq-box">{report_data['V3c']['cdna']['LC']}</div>
</div>

<div style="margin-top:15px; border:1px solid #166534; padding:15px; border-radius:8px; background:#f0fdf4;">
    <h3 style="color:#166534;margin-top:0;">Variant: V4b (DeepFR-CTX on V4/Lambda Scaffold)</h3>
    <strong>Heavy Chain Protein</strong>
    <div class="seq-box">{report_data['V4b']['protein']['HC']}</div>
    <strong>Light Chain Protein (Dog Lambda)</strong>
    <div class="seq-box">{report_data['V4b']['protein']['LC']}</div>
    <strong>HC cDNA (Dog Optimized)</strong>
    <div class="seq-box">{report_data['V4b']['cdna']['HC']}</div>
    <strong>LC cDNA (Dog Optimized)</strong>
    <div class="seq-box">{report_data['V4b']['cdna']['LC']}</div>
</div>

</div>
</body>
</html>
"""

Path("projects/Tanezumab_Caninization/Tanezumab_Comprehensive_Engineering_Report_V3_Final.html").write_text(html, encoding="utf-8")
print("Comprehensive report V3 (Final Naming) generated.")
