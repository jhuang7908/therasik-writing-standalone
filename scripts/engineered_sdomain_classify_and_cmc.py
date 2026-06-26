"""
engineered_sdomain_classify_and_cmc.py
=======================================
Step 1 + Step 2 of PROPOSAL 2026-05-08 (EVOLUTION_LOG.md):
- Collect all available engineered single-domain VH sequences
- Classify by A/B/C-hum/D taxonomy
- Compute full 15-parameter CMC panel + CDR3 metrics
- Compute AbNatiV Δ (best-effort, skip-on-failure)
- Output: data/_reconciliation/engineered_sdomain_ref_v1_sources.csv
          data/_reconciliation/engineered_sdomain_ref_v1_cmc_table.csv
"""

from __future__ import annotations
import json, sys, re, math, warnings, traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path('d:/InSynBio-AI-Research/Antibody_Engineer_Suite')
sys.path.insert(0, str(ROOT))

# ── imports ──────────────────────────────────────────────────────────────────
from core.cmc.vhh_cmc_engine import (
    evaluate_single_vhh, load_vhh_ref, compute_vhh_metrics_full,
    compute_flags, compute_adi_vhh, adi_grade
)

# ── taxonomy constants ────────────────────────────────────────────────────────
# A  : Native Murine VH → single domain (mouse FR + mouse CDR, Path C1)
# B  : Humanized Murine VH → VHH (human FR + murine-origin CDR, camelization only)
# Chum: Humanized mAb CDR graft to VHH scaffold (CDR from humanized mAb → VHH)
# D  : Fully Human VH → single domain (human FR + human CDR, directed evo / camelization)

CATEGORY_LABELS = {
    'A':      'Native Murine VH → sdAb',
    'B':      'Humanized Murine VH → VHH',
    'C-hum':  'Humanized mAb CDR Graft to VHH',
    'D':      'Fully Human VH → sdAb',
    'VHH_REF':'Natural VHH Positive Control',
}

# ── sequence registry ─────────────────────────────────────────────────────────

def collect_sequences() -> List[Dict]:
    records = []

    # ── Category D: Atlas-24 (Engineered_Human_VH in atlas_v3.json) ────────────
    atlas_path = ROOT / 'data/vhh_design_atlas_v3.json'
    atlas = json.loads(atlas_path.read_text(encoding='utf-8'))
    for e in atlas:
        if e.get('category') != 'Engineered_Human_VH':
            continue
        seq = e.get('sequence', '')
        if not seq or len(seq) < 90:
            continue
        
        # Refine Atlas-24 subsets based on single_domain_strategy
        strategy = e.get('single_domain_strategy', 'Unknown')
        if 'camelization' in strategy.lower() or 'VHH-like' in strategy:
            atlas_subset = 'Camelized'
        elif 'Muyldermans' in strategy:
            atlas_subset = 'Camelized'
        elif 'Custom' in strategy or 'motif:' in strategy:
            atlas_subset = 'Custom/Directed_Evo'
        else:
            atlas_subset = 'Other'

        records.append({
            'id':            f"atlas24_{e.get('pdb_id','?')}",
            'name':          e.get('name','')[:60],
            'sequence':      seq.strip().upper(),
            'category':      'D',
            'subset':        f"Atlas-24 ({atlas_subset})",
            'source':        f"SAbDab PDB {e.get('pdb_id','')}",
            'exp_validated': 'structure',
            'is_control':    False,
            'pmid':          '',
            'notes':         f"target={e.get('target','')}; germline={e.get('germline','')}; "
                             f"hallmark={e.get('hallmark_motif','')}; strategy={strategy}",
        })

    # ── Category A: SP34 (native murine VH donor)  ────────────────────────────
    # Donor VH from FASTA
    sp34_fasta = ROOT / 'data/reference/SP34_CD3mab_Blinatumomab_CD3_arm_vh_vl_v1.fasta'
    sp34_vh_seq = ''
    if sp34_fasta.exists():
        for line in sp34_fasta.read_text(encoding='utf-8').splitlines():
            if line.startswith('>'):
                if 'VL' in line:
                    break
            else:
                sp34_vh_seq += line.strip().upper()
    if sp34_vh_seq:
        records.append({
            'id':            'sp34_donor_vh',
            'name':          'SP34 CD3mab donor VH (native murine)',
            'sequence':      sp34_vh_seq,
            'category':      'A',
            'subset':        'Control (Paired VH)',
            'source':        'Blinatumomab CD3-arm; SAbDab bispecific_75_atlas',
            'exp_validated': 'therapeutic_approved',
            'is_control':    True,
            'pmid':          '',
            'notes':         'Native murine VH; IGHV3-?; SP34-class anti-CD3ε',
        })

    # SP34 C1 VHH candidates (AI-designed, Path C1 graft)
    sp34_report = ROOT / 'projects/SP34_CD3_VH2VHH_C1/reports/SP34_VHH_C1_design_report_v1.md'
    sp34_seqs = _extract_sequences_from_md(sp34_report) if sp34_report.exists() else []
    for i, (label, seq) in enumerate(sp34_seqs):
        records.append({
            'id':            f'sp34_c1_cand_{i+1}',
            'name':          f'SP34 C1 VHH candidate {i+1} ({label})',
            'sequence':      seq,
            'category':      'A',
            'subset':        'AI-designed Candidate',
            'source':        'AI-designed (InSynBio AbEngineCore Path C1)',
            'exp_validated': 'none',
            'is_control':    False,
            'pmid':          '',
            'notes':         'SP34 CDR on VHH scaffold; murine origin CDR',
        })

    # ── Category B: Humanized Murine VH → VHH ───────────────────────────────
    # 1. Visilizumab candidates
    visi_path = ROOT / 'projects/Visilizumab_CD3_VH2VHH_CMC/output/visilizumab_vh2vhh_cmc_optimization.json'
    if visi_path.exists():
        visi = json.loads(visi_path.read_text(encoding='utf-8'))
        for c in visi['candidates']:
            is_raw = c['id'] == 'raw_vh_reference'
            records.append({
                'id':            f"visi_{c['id']}",
                'name':          f"Visilizumab {c['id']}",
                'sequence':      c['sequence'].strip().upper(),
                'category':      'B',
                'subset':        'Control (Paired VH)' if is_raw else 'AI-designed Candidate',
                'source':        'AI-designed (InSynBio AbEngineCore CMC workflow)',
                'exp_validated': 'none' if not is_raw else 'therapeutic_clinical_humanized',
                'is_control':    is_raw,
                'pmid':          '',
                'notes':         f"Visilizumab anti-CD3; humanized murine IGHV3-7; "
                                 f"candidate={c['id']}; muts={c.get('mutations',[])}",
                'precomputed_cmc': c.get('cmc_summary'),
            })

    # 2. Teplizumab (humanized anti-CD3)
    records.append({
        'id':            'teplizumab_vh',
        'name':          'Teplizumab VH (humanized murine)',
        'sequence':      'QVQLVQSGGGVVQPGRSLRLSCKASGYTFTRYTMHWVRQAPGQGLEWIGYINPSRGYTNYNQKVKDRFTISRDNSKNTAFLQMDSLRPEDTGVYFCARYYDDHYCLDYWGQGTPVTVSS',
        'category':      'B',
        'subset':        'Control (Paired VH)',
        'source':        'Therapeutic (Tzield); humanized murine anti-CD3',
        'exp_validated': 'therapeutic_approved',
        'is_control':    True,
        'pmid':          '',
        'notes':         'Teplizumab anti-CD3; humanized murine; IGHV3-7-like',
    })

    # 3. Otelixizumab (humanized anti-CD3)
    records.append({
        'id':            'otelixizumab_vh',
        'name':          'Otelixizumab VH (humanized murine)',
        'sequence':      'EVQLLESGGGLVQPGGSLRLSCAASGFTFSSFPMAWVRQAPGKGLEWVSTISTSGGRTYYRDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKFRQYSGGFDYWGQGTLVTVSS',
        'category':      'B',
        'subset':        'Control (Paired VH)',
        'source':        'Therapeutic (TRX4); humanized murine anti-CD3',
        'exp_validated': 'therapeutic_clinical',
        'is_control':    True,
        'pmid':          '',
        'notes':         'Otelixizumab anti-CD3; humanized murine; IGHV3-23',
    })

    # 4. Porustobart (Envafolimab) — Transgenic Mouse VHH
    records.append({
        'id':            'porustobart_vhh',
        'name':          'Porustobart / Envafolimab (transgenic mouse VHH)',
        'sequence':      'QVQLVESGGGLVQPGGSLRLSCAASGKMSSRRCMAWFRQAPGKERERVAKLLTTSGSTYLADSVKGRFTISRDNSKNTVYLQMNSLRAEDTAVYYCAADSFEDPTCTLVTSSGAFQYWGQGTLVTVSS',
        'category':      'B', 
        'subset':        'Positive Control (Engineered VH Winner)',
        'source':        'Therapeutic (Envafolimab); transgenic mouse platform (Alphamab)',
        'exp_validated': 'therapeutic_approved',
        'is_control':    False,
        'pmid':          '',
        'notes':         'Porustobart anti-PD-L1; VHH from transgenic mouse; IGHV4-59-like',
    })

    # ── Category: Natural VHH Positive Controls ───────────────────────────────
    # 1. Caplacizumab (Cablivi)
    records.append({
        'id':            'caplacizumab_vhh',
        'name':          'Caplacizumab (Cablivi)',
        'sequence':      'EVQLVESGGGLVQPGGSLRLSCAASGRTFSYNPMGWFRQAPGKGRELVAAISRTGGSTYYPDSVEGRFTISRDNAKRMVYLQMNSLRAEDTAVYYCAAAGVRAEDGRVRTLPSEYTFWGQGTQVTVSS',
        'category':      'VHH_REF',
        'subset':        'Positive Control (Natural VHH)',
        'source':        'Therapeutic (Cablivi); humanized camelid VHH',
        'exp_validated': 'therapeutic_approved',
        'is_control':    False,
        'pmid':          '23461644',
        'notes':         'First approved VHH; anti-vWF; humanized camelid',
    })
    # 2. Ozoralizumab (Nanozora)
    records.append({
        'id':            'ozoralizumab_vhh',
        'name':          'Ozoralizumab (Nanozora)',
        'sequence':      'EVQLVESGGGLVQPGGSLRLSCAASGFTFSDYWMYWVRQAPGKGLEWVSEINTNGLITKYPDSVKGRFTISRDNAKNTLYLQMNSLRPEDTAVYYCARSPSGFNRGQGTLVTVSS',
        'category':      'VHH_REF',
        'subset':        'Positive Control (Natural VHH)',
        'source':        'Therapeutic (Nanozora); humanized camelid VHH',
        'exp_validated': 'therapeutic_approved',
        'is_control':    False,
        'pmid':          '34276766',
        'notes':         'Approved in Japan; anti-TNFα; humanized camelid',
    })

    # ── Category D subset: Foralumab VH candidates (fully human VH → VHH) ────
    fora_path = ROOT / 'projects/Foralumab_CD3_VH2VHH_CMC/output/foralumab_vh2vhh_cmc_optimization.json'
    if fora_path.exists():
        fora = json.loads(fora_path.read_text(encoding='utf-8'))
        for c in fora['candidates']:
            is_raw = c['id'] == 'raw_vh_reference'
            records.append({
                'id':            f"fora_{c['id']}",
                'name':          f"Foralumab {c['id']}",
                'sequence':      c['sequence'].strip().upper(),
                'category':      'D',
                'subset':        'Control (Paired VH)' if is_raw else 'AI-designed Candidate',
                'source':        'AI-designed (InSynBio AbEngineCore CMC workflow)',
                'exp_validated': 'none' if not is_raw else 'therapeutic_clinical',
                'is_control':    is_raw,
                'pmid':          '',
                'notes':         f"Foralumab anti-CD3; fully human IGHV3-23; "
                                 f"candidate={c['id']}",
                'precomputed_cmc': c.get('cmc_summary'),
            })

    # ── Mirzaei placeholders (Category B/C-hum) ─────────────────────────────
    mirzaei_refs = [
        ('mirzaei_pd1_grafted', 'Mirzaei PD-1 grafted VHH (CDR from Tislelizumab)', 'B'),
        ('mirzaei_pd1_y97r',    'Mirzaei PD-1 Y97R mutant',                         'C-hum'),
        ('mirzaei_pd1_y102r',   'Mirzaei PD-1 Y102R mutant',                        'C-hum'),
        ('tislelizumab_vh_donor','Tislelizumab VH (CDR donor, humanized anti-PD-1)', 'B'),
    ]
    for mid, mname, mcat in mirzaei_refs:
        records.append({
            'id':            mid,
            'name':          mname,
            'sequence':      '',  # unknown — pending extraction from paper
            'category':      mcat,
            'subset':        'Validated Single Domain (Experimental)',
            'source':        'Mirzaei et al. Mol.Biotechnol. 67:1843 (2025) DOI:10.1007/s12033-024-01162-1',
            'exp_validated': 'ELISA/WB/Dot_blot',
            'is_control':    False,
            'pmid':          '39085647',
            'notes':         'Sequence unknown — pending extraction from publication',
        })

    return records


def _extract_sequences_from_md(md_path: Path) -> List[tuple]:
    """Pull (label, sequence) pairs from FASTA blocks in a Markdown report."""
    text = md_path.read_text(encoding='utf-8', errors='ignore')
    seqs = []
    # Match code blocks with FASTA content
    for block in re.findall(r'```[^\n]*\n(>.*?)```', text, re.DOTALL):
        label, seq = '', ''
        for line in block.splitlines():
            if line.startswith('>'):
                if seq:
                    seqs.append((label, re.sub(r'[^A-Z]', '', seq.upper())))
                label = line[1:].strip()
                seq = ''
            else:
                seq += line.strip()
        if seq:
            seqs.append((label, re.sub(r'[^A-Z]', '', seq.upper())))
    # Filter: keep only protein sequences (length 90-150, mainly AA chars)
    valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
    result = []
    for label, seq in seqs:
        if 90 <= len(seq) <= 160 and sum(c in valid_aa for c in seq) / len(seq) > 0.95:
            result.append((label, seq))
    return result[:4]  # max 4 candidates


# ── CMC computation ───────────────────────────────────────────────────────────

def compute_cmc_row(rec: Dict, ref_stats: Dict) -> Dict:
    """Compute full 15-param CMC for one record. Use precomputed if available."""
    seq = rec.get('sequence', '')
    row = {
        'id': rec['id'],
        'name': rec['name'],
        'category': rec['category'],
        'category_label': CATEGORY_LABELS.get(rec['category'], rec['category']),
        'subset': rec.get('subset', 'Unknown'),
        'is_control': rec.get('is_control', False),
        'source': rec['source'],
        'exp_validated': rec['exp_validated'],
        'pmid': rec.get('pmid', ''),
        'notes': rec.get('notes', ''),
        'sequence': seq,
        'seq_len': len(seq) if seq else 0,
    }

    if not seq:
        # Placeholder — skip CMC
        for col in CMC_COLS:
            row[col] = 'UNKNOWN'
        row['adi_score'] = 'UNKNOWN'
        row['overall_status'] = 'UNKNOWN'
        return row

    # Use precomputed CMC if available (from project JSONs)
    pre = rec.get('precomputed_cmc')
    if pre and isinstance(pre, dict) and 'metrics' in pre:
        m = pre['metrics']
        for col in CMC_COLS:
            row[col] = m.get(col, 'N/A')
        row['charge_patch_max7'] = m.get('charge_patch_max7', row.get('charge_patch_max7', 'N/A'))
        row['adi_score']       = pre.get('adi_score', 'N/A')
        row['overall_status']  = pre.get('overall_status', 'N/A')
        row['n_warn']          = pre.get('n_warn', 'N/A')
        row['n_fail']          = pre.get('n_fail', 'N/A')
        return row

    # Compute fresh  — signature: evaluate_single_vhh(name, seq, ref_stats)
    try:
        result = evaluate_single_vhh(rec['id'], seq, ref_stats)
        m = result['metrics']
        for col in CMC_COLS:
            row[col] = m.get(col, 'N/A')
        row['adi_score']       = result.get('adi_score', 'N/A')
        row['overall_status']  = result.get('overall_status', 'N/A')
        row['n_warn']          = result.get('n_warn', 'N/A')
        row['n_fail']          = result.get('n_fail', 'N/A')
    except Exception as e:
        warnings.warn(f"CMC failed for {rec['id']}: {e}")
        for col in CMC_COLS:
            row[col] = 'ERROR'
        row['adi_score'] = 'ERROR'
        row['overall_status'] = 'ERROR'

    return row


CMC_COLS = [
    'pI', 'GRAVY', 'instability_index', 'net_charge_pH7',
    'hydro_patch_max9', 'SAP_score', 'charge_patch_max7',
    'glycosylation_sites', 'deamidation_sites', 'isomerization_sites',
    'oxidation_sites', 'free_cys',
]


def compute_cdr3_metrics(seq: str) -> Dict[str, Any]:
    """Quick CDR3 GRAVY and aromatic fraction using linear heuristic (last 13 aa before FR4)."""
    # FR4 starts at WGQG / WGQGTLVTVSS
    fr4_match = re.search(r'W[GQ][QG]', seq)
    if fr4_match:
        cdr3_end = fr4_match.start()
    else:
        cdr3_end = len(seq) - 11  # rough
    cdr3 = seq[max(0, cdr3_end - 13): cdr3_end]

    kd = {  # Kyte-Doolittle
        'I': 4.5, 'V': 4.2, 'L': 3.8, 'F': 2.8, 'C': 2.5, 'M': 1.9, 'A': 1.8,
        'G': -0.4, 'T': -0.7, 'S': -0.8, 'W': -0.9, 'Y': -1.3, 'P': -1.6,
        'H': -3.2, 'E': -3.5, 'Q': -3.5, 'D': -3.5, 'N': -3.5, 'K': -3.9, 'R': -4.5,
    }
    arom = set('FWY')
    if not cdr3:
        return {'cdr3_gravy': None, 'cdr3_arom_frac': None, 'cdr3_len': 0, 'cdr3_seq': ''}
    gravy = sum(kd.get(aa, 0) for aa in cdr3) / len(cdr3)
    arom_frac = sum(1 for aa in cdr3 if aa in arom) / len(cdr3)
    return {
        'cdr3_gravy': round(gravy, 3),
        'cdr3_arom_frac': round(arom_frac, 3),
        'cdr3_len': len(cdr3),
        'cdr3_seq': cdr3,
    }


def try_abnativ(seq: str, rec_id: str) -> Dict[str, Any]:
    """Attempt AbNatiV Δ score. Return dict with delta/tier or error flag."""
    try:
        from core.vh2vhh.abnativ_naturalness_layer import score_naturalness_delta
        r = score_naturalness_delta(seq)
        if r.error:
            return {
                'abnativ_vh2':   None,
                'abnativ_vhh2':  None,
                'abnativ_delta': None,
                'abnativ_tier':  f'ERROR:{r.error}',
            }
        return {
            'abnativ_vh2':   r.vh2_score,
            'abnativ_vhh2':  r.vhh2_score,
            'abnativ_delta': r.delta,
            'abnativ_tier':  r.tier,
        }
    except Exception as e:
        return {
            'abnativ_vh2':   None,
            'abnativ_vhh2':  None,
            'abnativ_delta': None,
            'abnativ_tier':  f'ERROR:{e}',
        }


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    out_dir = ROOT / 'data/_reconciliation'
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading VHH42 reference stats...", file=sys.stderr)
    ref = load_vhh_ref()

    print("Collecting sequences...", file=sys.stderr)
    records = collect_sequences()
    print(f"  Total records: {len(records)}", file=sys.stderr)

    # Count by category
    from collections import Counter
    cat_counts = Counter(r['category'] for r in records)
    for cat, n in sorted(cat_counts.items()):
        print(f"  Cat {cat} ({CATEGORY_LABELS.get(cat,'?')}): {n}", file=sys.stderr)

    # ── sources table (CSV) ───────────────────────────────────────────────────
    sources_path = out_dir / 'engineered_sdomain_ref_v1_sources.csv'
    src_rows = []
    for r in records:
        src_rows.append({
            'id': r['id'],
            'name': r['name'],
            'category': r['category'],
            'category_label': CATEGORY_LABELS.get(r['category'], r['category']),
            'subset': r.get('subset', 'Unknown'),
            'is_control': r.get('is_control', False),
            'sequence': r.get('sequence', ''),
            'seq_len': len(r.get('sequence', '')),
            'source': r['source'],
            'exp_validated': r['exp_validated'],
            'pmid': r.get('pmid', ''),
            'notes': r.get('notes', ''),
        })
    _write_csv(src_rows, sources_path,
               ['id','name','category','category_label','subset','is_control','seq_len','source','exp_validated','pmid','notes','sequence'])
    print(f"Wrote: {sources_path}", file=sys.stderr)

    # ── CMC + AbNatiV table ───────────────────────────────────────────────────
    print("Computing CMC metrics...", file=sys.stderr)
    cmc_rows = []
    for r in records:
        seq = r.get('sequence', '')
        print(f"  {r['id']} (cat={r['category']}, len={len(seq)})...", end='', file=sys.stderr)
        cmc = compute_cmc_row(r, ref)
        if seq:
            cdr3 = compute_cdr3_metrics(seq)
            cmc.update(cdr3)
            abnativ = try_abnativ(seq, r['id'])
            cmc.update(abnativ)
        else:
            cmc.update({'cdr3_gravy': 'UNKNOWN', 'cdr3_arom_frac': 'UNKNOWN',
                        'cdr3_len': 'UNKNOWN', 'cdr3_seq': 'UNKNOWN',
                        'abnativ_vh2': 'UNKNOWN', 'abnativ_vhh2': 'UNKNOWN',
                        'abnativ_delta': 'UNKNOWN', 'abnativ_tier': 'UNKNOWN'})
        cmc_rows.append(cmc)
        print(' OK', file=sys.stderr)

    cmc_path = out_dir / 'engineered_sdomain_ref_v1_cmc_table.csv'
    cmc_cols = (
        ['id','name','category','category_label','subset','is_control','exp_validated','seq_len'] +
        CMC_COLS +
        ['adi_score','overall_status','n_warn','n_fail'] +
        ['cdr3_gravy','cdr3_arom_frac','cdr3_len','cdr3_seq'] +
        ['abnativ_vh2','abnativ_vhh2','abnativ_delta','abnativ_tier'] +
        ['source','pmid','notes']
    )
    _write_csv(cmc_rows, cmc_path, cmc_cols)
    print(f"Wrote: {cmc_path}", file=sys.stderr)

    # ── quick summary ─────────────────────────────────────────────────────────
    print("\n=== SUMMARY ===", file=sys.stderr)
    cats = {}
    for row in cmc_rows:
        c = row['category']
        if c not in cats:
            cats[c] = []
        cats[c].append(row)

    for cat in sorted(cats.keys()):
        rows = cats[cat]
        print(f"\nCategory {cat} — {CATEGORY_LABELS.get(cat,'?')} (n={len(rows)})", file=sys.stderr)
        vals_gravy = [r['GRAVY'] for r in rows if isinstance(r.get('GRAVY'), (int, float))]
        vals_pi    = [r['pI']    for r in rows if isinstance(r.get('pI'), (int, float))]
        vals_adi   = [r['adi_score'] for r in rows if isinstance(r.get('adi_score'), (int, float))]
        if vals_gravy:
            print(f"  GRAVY: min={min(vals_gravy):.3f}  median={_median(vals_gravy):.3f}  max={max(vals_gravy):.3f}", file=sys.stderr)
        if vals_pi:
            print(f"  pI:    min={min(vals_pi):.2f}  median={_median(vals_pi):.2f}  max={max(vals_pi):.2f}", file=sys.stderr)
        if vals_adi:
            print(f"  ADI:   min={min(vals_adi):.1f}  median={_median(vals_adi):.1f}  max={max(vals_adi):.1f}", file=sys.stderr)


def _median(vals):
    s = sorted(vals)
    n = len(s)
    return (s[n//2] + s[(n-1)//2]) / 2


def _write_csv(rows: List[Dict], path: Path, cols: List[str]):
    import csv
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for row in rows:
            w.writerow(row)


if __name__ == '__main__':
    main()
