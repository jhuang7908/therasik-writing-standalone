import sys, json, pathlib
sys.path.insert(0, '.')

OUT = pathlib.Path('projects/mouse_cd20_humanization')

# Clinical Rituximab (from CART_LIBRARY_V3.json / Reff ME et al. 1994)
# VH-G4S3-VL format in scFv entry
VH_RITUX = "QVQLQQPGAELVKPGASVKMSCKASGYTFTSYAMSWVKQTPGQGLEWMGAINPSGGSTYFQKFKGKATLTADESSSTAYMQLSSLTSEDSAVYYCARNYYGSSTYYWGAGTTVTVSS"
VL_RITUX = "QIVLSQSPAILSASPGEKVTMTCRASSSVSYIHWFQQKPGSSPKPWIYATSNLASGVPARFSGSGSGTDFTLTISSVQAEDIADYYCQQWTSNPPTFGGGTKLEIK"

# Load existing variants
scores_path = OUT / 'all_scores.json'
if scores_path.exists():
    all_scores = json.loads(scores_path.read_text())
else:
    all_scores = {}

from core.cmc.cmc_metrics import CMCMetricEngine
from core.cmc.adi_score import compute_adi, compute_adi_percentile
from core.cmc.t20_biophi import compute_t20_biophi

ABREF_STATS = pathlib.Path('data/reference/AbRef458_stats_v1.json')
ABREF_ADI_DIST = pathlib.Path('data/reference/AbRef458_27m_ADI_distribution_v1.json')

def score_one(name, vh, vl):
    m = CMCMetricEngine.compute_metrics(vh, vl)
    ref_m = json.loads(ABREF_STATS.read_text())['metrics']
    adi = round(compute_adi(m, ref_metrics=ref_m), 2)
    pct = compute_adi_percentile(adi, adi_dist_path=ABREF_ADI_DIST)
    
    # T20/OASIS
    t20_res = compute_t20_biophi(vh, vl)
    t20 = t20_res.get('t20_score')
    oasis = t20_res.get('oasis_percentile')
    
    return {
        **m,
        'ADI': adi,
        'ADI_pct': round(float(pct), 1) if pct is not None else None,
        'T20': t20,
        'OASIS': oasis,
        'vh_len': len(vh),
        'vl_len': len(vl)
    }

print(f"Scoring Clinical Rituximab...")
ritux_scores = score_one('Clinical Rituximab', VH_RITUX, VL_RITUX)
all_scores['Clinical Rituximab'] = ritux_scores

# Save updated scores
scores_path.write_text(json.dumps(all_scores, indent=2, default=str))

# Update CLINICAL_BENCHMARK.md
benchmark_md = OUT / 'CLINICAL_BENCHMARK.md'
if benchmark_md.exists():
    lines = benchmark_md.read_text().splitlines()
    # Find the table and add the new row
    table_start = -1
    for i, line in enumerate(lines):
        if '| Variant | ADI |' in line:
            table_start = i
            break
    
    if table_start != -1:
        new_row = f"| Clinical Rituximab | {ritux_scores['ADI']} | {ritux_scores['ADI_pct']} | {ritux_scores['pI']} | {ritux_scores['GRAVY']} | {ritux_scores['instability_index']} | {ritux_scores['agg_motifs']} |"
        lines.append(new_row)
        benchmark_md.write_text('\n'.join(lines))

print(f"Updated scores and benchmark MD.")
