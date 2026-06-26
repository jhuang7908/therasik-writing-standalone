import pandas as pd
import numpy as np
import json
import yaml
import os
import sys
import time
import hashlib
import re
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.position_sets.load_imgt_position_sets import (
    get_imgt_anchors,
    get_vhh_hallmarks,
    get_vernier_anchors,
    get_nd_dependent_v2_lite,
    get_surface_plasticity_v1
)
from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed

# Paths
MASTER_TABLE = PROJECT_ROOT / "data" / "slice3_vhh_paper_grade_master_table_plus_cdr3_features.csv"
NUMBERING_PARQUET = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "anarcii_numbering_slice_3_vhh_design.parquet"
FRAMEWORK_LIB_YAML = PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.with_cdr12.canonical_input.yaml"
STRICT_SURFACE_YAML = PROJECT_ROOT / "output" / "surface_plasticity_positions_v1_strict.yaml"
IMGT_YAML_PATH = PROJECT_ROOT / "core" / "data" / "position_sets" / "imgt_position_sets.yaml"

# Output Paths
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"
FEATURES_CSV = REPORTS_DIR / "slice3_vhh_developability_features_native_sr_bm.csv"
DELTA_CSV = REPORTS_DIR / "slice3_vhh_sr_vs_bm_developability_delta.csv"
CLUSTER_REPORT_MD = REPORTS_DIR / "slice3_vhh_developability_cluster_report.md"
AUDIT_MD = OUTPUT_DIR / "developability_audit.md"
MUTATIONS_JSONL = OUTPUT_DIR / "slice3_vhh_variant_mutations.jsonl"

# Constants
HYDROPHOBIC_RESIDUES = set("AVILMFWY")
AROMATIC_RESIDUES = set("FWY")

def load_framework_library():
    if not FRAMEWORK_LIB_YAML.exists(): return {}
    with open(FRAMEWORK_LIB_YAML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    lib = {}
    for fw in data.get('frameworks', []):
        germline = fw.get('germline')
        positions = fw.get('numbering_evidence', {}).get('positions', {})
        lib[germline] = {int(k): v for k, v in positions.items()}
    return lib

def load_strict_surface():
    if not STRICT_SURFACE_YAML.exists(): return get_surface_plasticity_v1()
    with open(STRICT_SURFACE_YAML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return set(data.get('surface_plasticity_positions_v1_strict', []))

def get_yaml_sha256(path):
    if not path.exists(): return "not_found"
    with open(path, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()

class PositionMapper:
    """
    ANARCII-backed mapper: native sequence index <-> IMGT position.

    Note: this mapper is IMGT-only and intentionally ignores insertion codes
    for set membership (position sets are int-based). For mutation annotation
    we still record the insertion code from ANARCII output.
    """

    def __init__(self, native_seq: str):
        self.native_seq = native_seq
        numbered = imgt_number_anarcii_indexed(native_seq)
        self.rows = numbered["rows"]
        self.query_start = numbered.get("query_start", 0)
        self.query_end = numbered.get("query_end", len(native_seq) - 1)
        # Map ORIGINAL sequence indices -> IMGT position / insertion code
        self.idx_to_pos = {int(r["seq_idx"]): int(r["pos"]) for r in self.rows}
        self.idx_to_ins = {int(r["seq_idx"]): str(r.get("ins_code", " ")) for r in self.rows}
        self.mapping_coverage = len(self.idx_to_pos) / max(1, len(native_seq))

    @staticmethod
    def region_for_pos(pos: int) -> str:
        # IMGT heavy-chain variable domain canonical ranges
        if 1 <= pos <= 26:
            return "FR1"
        if 27 <= pos <= 38:
            return "CDR1"
        if 39 <= pos <= 55:
            return "FR2"
        if 56 <= pos <= 65:
            return "CDR2"
        if 66 <= pos <= 104:
            return "FR3"
        if 105 <= pos <= 117:
            return "CDR3"
        if 118 <= pos <= 128:
            return "FR4"
        return "OTHER"

    def apply_subs_by_imgt_positions(
        self,
        target_positions: set[int],
        human_pos_map: dict[int, str],
        forbid_regions: set[str] | None = None,
    ) -> tuple[str, list[dict]]:
        res = list(self.native_seq)
        muts: list[dict] = []
        forbid_regions = forbid_regions or set()
        for idx, pos in self.idx_to_pos.items():
            if pos not in target_positions:
                continue
            region = self.region_for_pos(pos)
            if region in forbid_regions:
                continue
            to_aa = human_pos_map.get(pos, "-")
            if not to_aa or to_aa == "-":
                continue
            if res[idx] == to_aa:
                continue
            muts.append(
                {
                    "imgt_pos": int(pos),
                    "ins_code": self.idx_to_ins.get(idx, " "),
                    "from": res[idx],
                    "to": to_aa,
                    "region": region,
                }
            )
            res[idx] = to_aa
        return "".join(res), sorted(muts, key=lambda x: (x["imgt_pos"], x["ins_code"]))

    def extract_cdr3_by_imgt(self, seq: str) -> str:
        chars = []
        for i, aa in enumerate(seq):
            pos = self.idx_to_pos.get(i)
            if pos is None:
                continue
            if 105 <= pos <= 117:
                chars.append(aa)
        return "".join(chars)

def compute_net_charge(seq):
    charge = 0
    for aa in seq:
        if aa in "KR": charge += 1
        elif aa == "H": charge += 0.1
        elif aa in "DE": charge -= 1
    return charge

def find_motifs(seq, motif_regex):
    return [(m.start() + 1, m.group()) for m in re.finditer(motif_regex, seq)]

def get_sliding_window_metrics(seq, window_size, metric_func):
    if len(seq) < window_size: return 0, [0]
    values = [metric_func(seq[i:i+window_size]) for i in range(len(seq) - window_size + 1)]
    return max(values), values

def get_best_available_germline(requested, fw_lib):
    if requested in fw_lib: return requested
    family = requested.split('-')[0] if '-' in requested else requested[:5]
    for g in fw_lib:
        if g.startswith(family): return g
    if "IGHV3" in requested: return "IGHV3-23*01"
    return next(iter(fw_lib.keys()))

def compute_developability(seq, cdr3_seq, mapper):
    ngly = find_motifs(seq, r'N[^P][ST]')
    ngly_c3 = [m for m in ngly if cdr3_seq and m[1] in cdr3_seq]
    deamid = find_motifs(seq, r'N[GSNQ]|Q[GS]')
    deamid_c3 = [m for m in deamid if cdr3_seq and m[1] in cdr3_seq]
    iso = find_motifs(seq, r'D[GS]')
    ox_m, ox_w = seq.count('M'), seq.count('W')
    cys_count = seq.count('C')
    extra_cys = cys_count > 2
    
    t_len, c3_len = len(seq), len(cdr3_seq) if cdr3_seq else 0
    net_charge = compute_net_charge(seq)
    h_global = sum(1 for aa in seq if aa in HYDROPHOBIC_RESIDUES) / t_len
    h_c3 = sum(1 for aa in cdr3_seq if aa in HYDROPHOBIC_RESIDUES) / c3_len if c3_len > 0 else 0
    a_global = sum(1 for aa in seq if aa in AROMATIC_RESIDUES) / t_len
    a_c3 = sum(1 for aa in cdr3_seq if aa in AROMATIC_RESIDUES) / c3_len if c3_len > 0 else 0
    gp_c3 = sum(1 for aa in cdr3_seq if aa in "GP") / c3_len if c3_len > 0 else 0
    
    hp_max9, _ = get_sliding_window_metrics(seq, 9, lambda s: sum(1 for aa in s if aa in HYDROPHOBIC_RESIDUES) / len(s))
    cp_max7, _ = get_sliding_window_metrics(seq, 7, lambda s: abs(compute_net_charge(s)))
    
    score, p = 100, {}
    p['ngly'] = (len(ngly) - len(ngly_c3)) * 8 + len(ngly_c3) * 12
    if extra_cys: p['extra_cys'] = 15
    p['deamid'] = (len(deamid) - len(deamid_c3)) * 2 + len(deamid_c3) * 3
    p['iso'] = len(iso) * 3
    if hp_max9 >= 0.7: p['hp'] = 10
    elif hp_max9 >= 0.6: p['hp'] = 6
    if cp_max7 >= 7: p['cp'] = 10
    elif cp_max7 >= 5: p['cp'] = 6
    if h_c3 >= 0.45: p['h_c3'] = 8
    
    total_p = sum(p.values())
    score = max(0, 100 - total_p)
    risk = "Low" if score >= 80 else "Medium" if score >= 60 else "High"
    
    return {
        "score": score, "risk_tier": risk, "penalty_breakdown": json.dumps(p),
        "ngly_count": len(ngly), "deamid_count": len(deamid), "iso_count": len(iso),
        "ox_m_count": ox_m, "ox_w_count": ox_w, "cysteine_count": cys_count, "extra_cys_flag": int(extra_cys),
        "net_charge": net_charge, "net_charge_norm": net_charge / t_len, "hydrophobic_frac_global": h_global,
        "hydrophobic_frac_cdr3": h_c3, "aromatic_frac_global": a_global, "aromatic_frac_cdr3": a_c3,
        "gp_frac_cdr3": gp_c3, "hp_max9": hp_max9, "cp_max7": cp_max7, "total_len": t_len, "cdr3_len": c3_len
    }


def annotate_mutations(
    muts: list[dict],
    *,
    variant: str,
    antibody_id: str,
    strict_surface: set[int],
    anchors: set[int],
    vernier: set[int],
    hallmarks: set[int],
    nd_core: set[int],
    nd_cand: set[int],
):
    out = []
    restricted = anchors | vernier | hallmarks | nd_core | nd_cand
    for m in muts:
        pos = int(m["imgt_pos"])
        flags = {
            "in_surface_strict": int(pos in strict_surface),
            "in_anchor": int(pos in anchors),
            "in_vernier": int(pos in vernier),
            "in_hallmark": int(pos in hallmarks),
            "in_nd_core": int(pos in nd_core),
            "in_nd_candidate": int(pos in nd_cand),
            "in_restricted": int(pos in restricted),
        }
        if variant == "sr":
            tier = "SR_surface_strict"
            reason = "surface_resurfacing_strict"
        elif variant == "bm":
            tier = "BM_tier2_surface_strict" if pos in strict_surface else "BM_tier3_other_fr"
            reason = "bm_framework_humanize_excluding_tier0_tier1"
        else:
            tier = "native"
            reason = "native"
        out.append(
            {
                "antibody_id": antibody_id,
                "variant": variant,
                "imgt_pos": pos,
                "ins_code": m.get("ins_code", " "),
                "from": m.get("from"),
                "to": m.get("to"),
                "region": m.get("region", "OTHER"),
                "tier": tier,
                "reason": reason,
                **flags,
            }
        )
    return out

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True); os.makedirs(REPORTS_DIR, exist_ok=True)
    df_m, df_n = pd.read_csv(MASTER_TABLE), pd.read_parquet(NUMBERING_PARQUET)
    fw_lib, strict_surface = load_framework_library(), load_strict_surface()
    anchors, hallmarks, vernier = get_imgt_anchors(), get_vhh_hallmarks(), get_vernier_anchors()
    
    records, deltas, mutations = [], [], []
    print(f"Processing {len(df_m)} records...")
    
    for _, row in df_m.iterrows():
        ab_id = row['antibody_id']
        native_row = df_n[df_n['antibody_id'] == ab_id]
        if native_row.empty: continue
        native_seq = native_row.iloc[0]['vh_sequence']
        best_germline = get_best_available_germline(row.get('vh_best_germline_global'), fw_lib)
        mapper = PositionMapper(native_seq)
        
        h1_cls, h2_cls = str(row.get('h1_north', 'unknown')), str(row.get('h2_north', 'unknown'))
        nd_h1, nd_h2 = get_nd_dependent_v2_lite("H1", h1_cls), get_nd_dependent_v2_lite("H2", h2_cls)
        nd_core, nd_cand = nd_h1['core'] | nd_h2['core'], nd_h1['candidate'] | nd_h2['candidate']
        
        # SR: strict surface only; forbid any CDR mutations by default
        sr_targets = set(strict_surface)
        sr_seq, sr_muts = mapper.apply_subs_by_imgt_positions(
            target_positions=sr_targets,
            human_pos_map=fw_lib[best_germline],
            forbid_regions={"CDR1", "CDR2", "CDR3"},
        )
        tier0, tier1 = anchors | vernier | nd_core, hallmarks | nd_cand
        fr_pos = set(range(1, 27)) | set(range(39, 56)) | set(range(66, 105))
        bm_seq, bm_muts = mapper.apply_subs_by_imgt_positions(
            target_positions=(fr_pos - tier0 - tier1),
            human_pos_map=fw_lib[best_germline],
            forbid_regions={"CDR1", "CDR2", "CDR3"},
        )

        # Quality gates: SR must not hit restricted; SR/BM must keep CDR3 unchanged (default rule)
        restricted = anchors | vernier | hallmarks | nd_core | nd_cand
        bad_sr = [m for m in sr_muts if int(m["imgt_pos"]) in restricted]
        if bad_sr:
            raise RuntimeError(f"[{ab_id}] SR violated restricted positions: {bad_sr}")
        cdr3_native = mapper.extract_cdr3_by_imgt(native_seq)
        cdr3_sr = mapper.extract_cdr3_by_imgt(sr_seq)
        cdr3_bm = mapper.extract_cdr3_by_imgt(bm_seq)
        if cdr3_native != cdr3_sr:
            raise RuntimeError(f"[{ab_id}] SR changed CDR3 (ANARCII-defined).")
        if cdr3_native != cdr3_bm:
            raise RuntimeError(f"[{ab_id}] BM changed CDR3 (ANARCII-defined).")
        
        # Functional mutation list (annotated)
        mutations.extend(
            annotate_mutations(
                sr_muts,
                variant="sr",
                antibody_id=ab_id,
                strict_surface=strict_surface,
                anchors=anchors,
                vernier=vernier,
                hallmarks=hallmarks,
                nd_core=nd_core,
                nd_cand=nd_cand,
            )
        )
        mutations.extend(
            annotate_mutations(
                bm_muts,
                variant="bm",
                antibody_id=ab_id,
                strict_surface=strict_surface,
                anchors=anchors,
                vernier=vernier,
                hallmarks=hallmarks,
                nd_core=nd_core,
                nd_cand=nd_cand,
            )
        )
        variants = {"native": (native_seq, []), "sr": (sr_seq, sr_muts), "bm": (bm_seq, bm_muts)}
        
        v_res = {}
        for vname, (vseq, vmuts) in variants.items():
            # CDR3 should be defined from ANARCII numbering for consistent attribution
            cdr3_seq = mapper.extract_cdr3_by_imgt(vseq)
            res = compute_developability(vseq, cdr3_seq, mapper)
            res.update({"antibody_id": ab_id, "variant": vname, "mut_total": len(vmuts),
                "mut_in_surface_strict": sum(1 for m in vmuts if int(m['imgt_pos']) in strict_surface),
                "mut_in_anchor": sum(1 for m in vmuts if int(m['imgt_pos']) in anchors),
                "mut_in_vernier": sum(1 for m in vmuts if int(m['imgt_pos']) in vernier),
                "mut_in_hallmark": sum(1 for m in vmuts if int(m['imgt_pos']) in hallmarks),
                "mut_in_nd_core": sum(1 for m in vmuts if int(m['imgt_pos']) in nd_core),
                "mut_in_nd_candidate": sum(1 for m in vmuts if int(m['imgt_pos']) in nd_cand)})
            res["bm_tier0_count"] = res["mut_in_anchor"] + res["mut_in_vernier"] + res["mut_in_nd_core"]
            res["bm_tier1_count"] = res["mut_in_hallmark"] + res["mut_in_nd_candidate"]
            res["bm_tier2_count"] = res["mut_in_surface_strict"]
            records.append(res); v_res[vname] = res

        n, s, b = v_res['native'], v_res['sr'], v_res['bm']
        d_sr, d_bm = s['score'] - n['score'], b['score'] - n['score']
        deltas.append({"antibody_id": ab_id, "h2_north": h2_cls, "cdr3_len": n['cdr3_len'],
            "gp_frac_cdr3": n['gp_frac_cdr3'], "dev_score_native": n['score'], "dev_score_sr": s['score'],
            "dev_score_bm": b['score'], "d_score_sr": d_sr, "d_score_bm": d_bm, "dd_score": d_sr - d_bm,
            "pref": "SR-favored" if (d_sr - d_bm) > 3 else "BM-favored" if (d_sr - d_bm) < -3 else "tie",
            "dd_ngly": (s['ngly_count'] - n['ngly_count']) - (b['ngly_count'] - n['ngly_count']),
            "dd_hp_max9": (s['hp_max9'] - n['hp_max9']) - (b['hp_max9'] - n['hp_max9']),
            "dd_cp_max7": (s['cp_max7'] - n['cp_max7']) - (b['cp_max7'] - n['cp_max7']),
            "dd_hydro_cdr3": (s['hydrophobic_frac_cdr3'] - n['hydrophobic_frac_cdr3']) - (b['hydrophobic_frac_cdr3'] - n['hydrophobic_frac_cdr3']),
            "dd_gp_cdr3": (s['gp_frac_cdr3'] - n['gp_frac_cdr3']) - (b['gp_frac_cdr3'] - n['gp_frac_cdr3'])})

    pd.DataFrame(records).to_csv(FEATURES_CSV, index=False)
    delta_df = pd.DataFrame(deltas); delta_df.to_csv(DELTA_CSV, index=False)
    with open(MUTATIONS_JSONL, 'w') as f:
        for m in mutations:
            f.write(json.dumps(m, ensure_ascii=False) + '\n')
    
    with open(AUDIT_MD, 'w') as f:
        f.write("# Developability Audit Log\n\n")
        f.write(f"- YAML Hash: {get_yaml_sha256(IMGT_YAML_PATH)}\n")
        f.write("- IMGT numbering: ANARCII (core.numbering.imgt_anarcii.imgt_number_anarcii)\n")
        f.write("- Thresholds: N-gly (8/12), Extra Cys (15), Deamid (2/3), Iso (3), HP Max9 >=0.7 (10), CP Max7 >=7 (10)\n")
        f.write("- Disclaimer: in silico developability proxies; experimental validation required\n")

    if not delta_df.empty:
        c_cols = ['dd_score', 'dd_ngly', 'dd_hp_max9', 'dd_cp_max7', 'dd_hydro_cdr3', 'dd_gp_cdr3']
        X = delta_df[c_cols].values
        X_std = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)
        delta_df['cluster'] = fcluster(linkage(X_std, 'ward'), t=3, criterion='maxclust')
        with open(CLUSTER_REPORT_MD, 'w') as f:
            f.write("# VHH Developability Cluster Report\n\n## Summary\n")
            f.write(delta_df['pref'].value_counts().to_markdown() + "\n\n")
            f.write("## Enrichment by H2 Class\n" + pd.crosstab(delta_df['h2_north'], delta_df['pref']).to_markdown() + "\n\n")
            f.write("## Top 5 SR-favored\n" + delta_df.sort_values('dd_score', ascending=False).head(5).to_markdown(index=False) + "\n\n")
            f.write("## Top 5 BM-favored\n" + delta_df.sort_values('dd_score').head(5).to_markdown(index=False) + "\n\n")
    print(f"Done. Reports in {REPORTS_DIR}")

if __name__ == "__main__": main()
