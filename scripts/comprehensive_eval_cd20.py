"""
Comprehensive evaluation of mouse anti-CD20 humanization variants.
1. Generate PDBs (ABodyBuilder2)
2. Humanness (AbNatiV, HPR Index)
3. Structural Conservatism (RMSD vs Murine)
4. Mini CMC (AbEngineCore metrics)
"""
import sys, json, pathlib, os
sys.path.insert(0, '.')

# Environment setup for structure prediction
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from ImmuneBuilder import ABodyBuilder2
from core.cmc.cmc_metrics import CMCMetricEngine
from core.humanization.hpr_index import compute_hpr_index
from core.cmc.igg_hpr_ablang import compute_igg_cmc_hpr_ablang
from abnativ.model.scoring_functions import abnativ_scoring
from Bio.PDB import PDBParser, Superimposer
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

OUT = pathlib.Path('projects/mouse_cd20_humanization')
OUT.mkdir(parents=True, exist_ok=True)
PDB_DIR = OUT / 'pdbs'
PDB_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    print(msg)
    sys.stdout.flush()

# ── Variants and Sequences ──────────────────────────────────────────────────
VH_RITUX = "QVQLQQPGAELVKPGASVKMSCKASGYTFTSYAMSWVKQTPGQGLEWMGAINPSGGSTYFQKFKGKATLTADESSSTAYMQLSSLTSEDSAVYYCARNYYGSSTYYWGAGTTVTVSS"
VL_RITUX = "QIVLSQSPAILSASPGEKVTMTCRASSSVSYIHWFQQKPGSSPKPWIYATSNLASGVPARFSGSGSGTDFTLTISSVQAEDIADYYCQQWTSNPPTFGGGTKLEIK"

# Load existing variants
seqs_main = json.loads((OUT / 'humanized_sequences.json').read_text())
seqs_graft = json.loads((OUT / 'graft_surface_compare.json').read_text())['variants']

variants = {
    'Murine_Parent': (seqs_main['murine']['vh'], seqs_main['murine']['vl']),
    'DEEP-FR':       (seqs_main['deepfr']['vh'], seqs_main['deepfr']['vl']),
    '9AA-CTX':       (seqs_main['9aa_ctx']['vh'], seqs_main['9aa_ctx']['vl']),
    '9AA-CTX-Aggressive': (
        seqs_main.get('9aa_ctx_aggressive', seqs_main['9aa_ctx'])['vh'],
        seqs_main.get('9aa_ctx_aggressive', seqs_main['9aa_ctx'])['vl'],
    ),
    'Graft_Pure':    (seqs_graft['cdr_graft_pure']['vh'], seqs_graft['cdr_graft_pure']['vl']),
    'Graft_Vernier': (seqs_graft['cdr_graft_vernier_bm']['vh'], seqs_graft['cdr_graft_vernier_bm']['vl']),
    'Surface_Reshape': (seqs_graft['surface_reshaping']['vh'], seqs_graft['surface_reshaping']['vl']),
    'Clinical_Ritux': (VH_RITUX, VL_RITUX),
}

# ── Step 1: Structure Prediction ─────────────────────────────────────────────
predictor = ABodyBuilder2()
pdb_paths = {}

log("Step 1: Generating PDB structures...")
for name, (vh, vl) in variants.items():
    path = PDB_DIR / f"{name}.pdb"
    if not path.is_file():
        log(f"  Predicting {name}...")
        try:
            ab = predictor.predict({'H': vh, 'L': vl})
            ab.save(str(path))
        except Exception as e:
            log(f"  Error predicting {name}: {e}")
            continue
    pdb_paths[name] = path

# ── Step 2: Humanness (AbNatiV, HPR) ─────────────────────────────────────────
log("Step 2: Assessing humanness...")

humanness_results = {}
for name, (vh, vl) in variants.items():
    log(f"  Scoring {name}...")
    
    # AbNatiV (VH and VL separately)
    try:
        # VH
        recs_h = [SeqRecord(Seq(vh), id=f"{name}_VH")]
        df_h, _ = abnativ_scoring(model_type="VH", seq_records=recs_h, verbose=False)
        # Column name is 'AbNatiV VH Score'
        score_h = df_h.filter(like='Score').iloc[0, 0]
        
        # VL (Kappa)
        recs_l = [SeqRecord(Seq(vl), id=f"{name}_VL")]
        df_l, _ = abnativ_scoring(model_type="VKappa", seq_records=recs_l, verbose=False)
        # Column name is 'AbNatiV VKappa Score'
        score_l = df_l.filter(like='Score').iloc[0, 0]
    except Exception as e:
        log(f"  AbNatiV error for {name}: {e}")
        score_h = score_l = None
    
    # HPR and AbLang (OASis-like + PLL)
    try:
        res = compute_igg_cmc_hpr_ablang(vh, vl)
        hpr_val = res.get('hpr_index', {}).get('score')
        ablang_val = res.get('ablang_score')
    except Exception as e:
        log(f"  HPR/AbLang error for {name}: {e}")
        hpr_val = None
        ablang_val = None
        
    humanness_results[name] = {
        'AbNatiV_VH': round(float(score_h), 3) if score_h is not None else None,
        'AbNatiV_VL': round(float(score_l), 3) if score_l is not None else None,
        'HPR_Index': round(float(hpr_val), 3) if hpr_val is not None else None,
        'AbLang_Score': ablang_val
    }

# ── Step 3: Structural Conservatism (RMSD) ───────────────────────────────────
log("Step 3: Calculating RMSD vs Murine Parent...")
rmsd_results = {}
parser = PDBParser(QUIET=True)
ref_name = 'Murine_Parent'

if ref_name in pdb_paths:
    ref_struct = parser.get_structure(ref_name, str(pdb_paths[ref_name]))
    ref_atoms = [atom for atom in ref_struct.get_atoms() if atom.get_name() == 'CA']
    
    for name, path in pdb_paths.items():
        if name == ref_name:
            rmsd_results[name] = 0.0
            continue
        
        target_struct = parser.get_structure(name, str(path))
        target_atoms = [atom for atom in target_struct.get_atoms() if atom.get_name() == 'CA']
        
        # Superimpose
        super_imposer = Superimposer()
        # Ensure atom counts match (should for Fv regions of same length)
        n = min(len(ref_atoms), len(target_atoms))
        super_imposer.set_atoms(ref_atoms[:n], target_atoms[:n])
        rmsd_results[name] = round(super_imposer.rms, 3)
else:
    log(f"  Warning: {ref_name} PDB missing, skipping RMSD.")

# ── Step 4: Mini CMC ─────────────────────────────────────────────────────────
log("Step 4: Running Mini CMC assessment...")
cmc_results = {}
for name, (vh, vl) in variants.items():
    m = CMCMetricEngine.compute_metrics(vh, vl)
    cmc_results[name] = {
        'pI': m.get('pI'),
        'GRAVY': m.get('GRAVY'),
        'Instability': m.get('instability_index'),
        'Agg_Motifs': m.get('agg_motifs'),
        'Liabilities': len(m.get('chemical_liabilities', {})) if isinstance(m.get('chemical_liabilities'), dict) else 0
    }

# ── Step 5: Aggregate and Save ───────────────────────────────────────────────
final_report = []
for name in variants.keys():
    row = {
        'Variant': name,
        **humanness_results.get(name, {}),
        'RMSD_vs_Murine': rmsd_results.get(name),
        **cmc_results.get(name, {})
    }
    final_report.append(row)

(OUT / 'comprehensive_comparison.json').write_text(json.dumps(final_report, indent=2))

# Markdown Table
header = "| Variant | AbNatiV (H/L) | HPR Index | AbLang | RMSD | pI | GRAVY | Instab | Agg |"
sep = "|---|---|---|---|---|---|---|---|---| "
lines = [header, sep]
for r in final_report:
    abnativ_str = f"{r['AbNatiV_VH']}/{r['AbNatiV_VL']}"
    line = f"| {r['Variant']} | {abnativ_str} | {r['HPR_Index']} | {r['AbLang_Score']} | {r['RMSD_vs_Murine']} | {r['pI']} | {r['GRAVY']} | {r['Instability']} | {r['Agg_Motifs']} |"
    lines.append(line)

(OUT / 'COMPREHENSIVE_EVALUATION.md').write_text("\n".join(lines))
log(f"\nDone. Report saved to {OUT / 'COMPREHENSIVE_EVALUATION.md'}")
