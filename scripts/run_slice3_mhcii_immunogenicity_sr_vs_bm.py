import pandas as pd
import numpy as np
import json
import yaml
import os
import sys
import time
import hashlib
import requests
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

# Output Paths
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"
PREDICTIONS_PARQUET = REPORTS_DIR / "slice3_vhh_mhcii_predictions.parquet"
FEATURES_CSV = REPORTS_DIR / "slice3_vhh_immunogenicity_features.csv"
DELTA_TABLE_CSV = REPORTS_DIR / "slice3_vhh_sr_vs_bm_delta_table.csv"
CLUSTER_REPORT_MD = REPORTS_DIR / "slice3_vhh_immunogenicity_cluster_report.md"
AUDIT_MD = OUTPUT_DIR / "iedb_mhcii_audit.md"
CACHE_DIR = OUTPUT_DIR / "iedb_cache"

# Config
DEFAULT_ALLELES = "HLA-DRB1*01:01,HLA-DRB1*03:01,HLA-DRB1*04:01,HLA-DRB1*04:05,HLA-DRB1*07:01,HLA-DRB1*08:02,HLA-DRB1*09:01,HLA-DRB1*11:01,HLA-DRB1*12:01,HLA-DRB1*13:02,HLA-DRB1*15:01"
IEDB_API_URL = "https://tools-cluster-interface.iedb.org/tools_api/mhcii/"

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

class PositionMapper:
    """
    ANARCII-backed mapper: native sequence index <-> IMGT position.

    For set membership we use integer IMGT positions (insertion codes ignored).
    For audit we keep ins_code as well.
    """

    def __init__(self, native_seq: str):
        self.native_seq = native_seq
        numbered = imgt_number_anarcii_indexed(native_seq)
        self.rows = numbered["rows"]
        self.query_start = numbered.get("query_start", 0)
        self.query_end = numbered.get("query_end", len(native_seq) - 1)
        self.idx_to_pos = {int(r["seq_idx"]): int(r["pos"]) for r in self.rows}
        self.idx_to_ins = {int(r["seq_idx"]): str(r.get("ins_code", " ")) for r in self.rows}
        self.mapping_coverage = len(self.idx_to_pos) / max(1, len(native_seq))

    @staticmethod
    def region_for_pos(pos: int) -> str:
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
) -> list[dict]:
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

def get_iedb_prediction(sequence, alleles, method="recommended", length=15, cache_dir=CACHE_DIR):
    os.makedirs(cache_dir, exist_ok=True)
    params_hash = hashlib.sha256(f"{sequence}_{alleles}_{method}_{length}".encode()).hexdigest()[:24]
    cache_file = cache_dir / f"{params_hash}.tsv"
    if cache_file.exists(): return pd.read_csv(cache_file, sep='\t'), True

    payload = {'method': method, 'sequence_text': sequence, 'allele': alleles, 'length': length}
    for attempt in range(3):
        try:
            response = requests.post(IEDB_API_URL, data=payload, timeout=90)
            if response.status_code == 200:
                import io
                df = pd.read_csv(io.StringIO(response.text), sep='\t')
                df.to_csv(cache_file, sep='\t', index=False)
                time.sleep(1.5)
                return df, False
            else: print(f"API Error {response.status_code}: {response.text}")
        except Exception as e: print(f"Request error: {e}")
        time.sleep(2 ** (attempt + 1))
    return None, False

def get_best_available_germline(requested, fw_lib):
    if requested in fw_lib: return requested
    family = requested.split('-')[0] if '-' in requested else requested[:5]
    for g in fw_lib:
        if g.startswith(family): return g
    if "IGHV3" in requested: return "IGHV3-23*01"
    return next(iter(fw_lib.keys()))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--peptide_len", type=int, default=15)
    parser.add_argument("--step", type=int, default=1)
    parser.add_argument("--rank_strong", type=float, default=1.0)
    parser.add_argument("--rank_very_strong", type=float, default=2.0)
    parser.add_argument("--method", default="recommended")
    parser.add_argument("--alleles", default=DEFAULT_ALLELES)
    args = parser.parse_args()

    df_master = pd.read_csv(MASTER_TABLE)
    df_numbering = pd.read_parquet(NUMBERING_PARQUET)
    fw_lib = load_framework_library()
    strict_surface = load_strict_surface()
    anchors, hallmarks, vernier = get_imgt_anchors(), get_vhh_hallmarks(), get_vernier_anchors()
    
    audit = {"start": time.ctime(), "endpoint": IEDB_API_URL, "requests": 0, "hits": 0, "fails": 0}
    all_preds, features = [], []
    mutations_annotated: list[dict] = []
    
    print(f"Processing {len(df_master)} records...")
    for _, row in df_master.iterrows():
        ab_id = row['antibody_id']
        requested_germline = row.get('vh_best_germline_global')
        best_germline = get_best_available_germline(requested_germline, fw_lib)
        
        native_row = df_numbering[df_numbering['antibody_id'] == ab_id]
        if native_row.empty: continue
        native_seq = native_row.iloc[0]['vh_sequence']
        
        mapper = PositionMapper(native_seq)
        h1_cls, h2_cls = str(row.get('h1_north', 'unknown')), str(row.get('h2_north', 'unknown'))
        nd_h1 = get_nd_dependent_v2_lite("H1", h1_cls)
        nd_h2 = get_nd_dependent_v2_lite("H2", h2_cls)
        tier0, tier1 = nd_h1['core'] | nd_h2['core'] | vernier | anchors, nd_h1['candidate'] | nd_h2['candidate'] | hallmarks
        
        # SR: strict surface only; forbid any CDR mutations by default
        sr_seq, sr_muts = mapper.apply_subs_by_imgt_positions(
            target_positions=set(strict_surface),
            human_pos_map=fw_lib[best_germline],
            forbid_regions={"CDR1", "CDR2", "CDR3"},
        )
        fr_pos = set(range(1, 27)) | set(range(39, 56)) | set(range(66, 105))
        bm_targets = fr_pos - tier0 - tier1
        bm_seq, bm_muts = mapper.apply_subs_by_imgt_positions(
            target_positions=bm_targets,
            human_pos_map=fw_lib[best_germline],
            forbid_regions={"CDR1", "CDR2", "CDR3"},
        )

        # Quality gates: SR must not hit restricted; SR/BM must keep CDR3 unchanged (default rule)
        restricted = anchors | vernier | hallmarks | nd_h1['core'] | nd_h2['core'] | nd_h1['candidate'] | nd_h2['candidate']
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
        mutations_annotated.extend(
            annotate_mutations(
                sr_muts,
                variant="sr",
                antibody_id=ab_id,
                strict_surface=strict_surface,
                anchors=anchors,
                vernier=vernier,
                hallmarks=hallmarks,
                nd_core=(nd_h1["core"] | nd_h2["core"]),
                nd_cand=(nd_h1["candidate"] | nd_h2["candidate"]),
            )
        )
        mutations_annotated.extend(
            annotate_mutations(
                bm_muts,
                variant="bm",
                antibody_id=ab_id,
                strict_surface=strict_surface,
                anchors=anchors,
                vernier=vernier,
                hallmarks=hallmarks,
                nd_core=(nd_h1["core"] | nd_h2["core"]),
                nd_cand=(nd_h1["candidate"] | nd_h2["candidate"]),
            )
        )
        
        variants = {"native": native_seq, "sr": sr_seq, "bm": bm_seq}
        mut_lists = {
            "sr": ";".join([f"{m['from']}{m['imgt_pos']}{m['to']}" for m in sr_muts]),
            "bm": ";".join([f"{m['from']}{m['imgt_pos']}{m['to']}" for m in bm_muts]),
        }

        for vname, vseq in variants.items():
            res, cached = get_iedb_prediction(vseq, args.alleles, method=args.method, length=args.peptide_len)
            if res is not None:
                audit["requests"] += 1
                if cached: audit["hits"] += 1
                res['antibody_id'], res['variant'] = ab_id, vname
                res.columns = [c.lower().replace(' ', '_') for c in res.columns]
                rank_col = 'percentile_rank' if 'percentile_rank' in res.columns else 'rank'
                if rank_col not in res.columns:
                    possible = [c for c in res.columns if 'rank' in c]
                    if possible: rank_col = possible[0]
                all_preds.append(res)
                s_hits = res[res[rank_col] <= args.rank_strong]
                m_hits = res[res[rank_col] <= args.rank_very_strong]
                features.append({
                    "antibody_id": ab_id, "variant": vname, "B_total_1pct": len(s_hits), "B_total_2pct": len(m_hits),
                    "B_breadth_1pct": s_hits['allele'].nunique() if 'allele' in s_hits.columns else 0,
                    "B_breadth_2pct": m_hits['allele'].nunique() if 'allele' in m_hits.columns else 0,
                    "min_rank": res[rank_col].min(), "mutations": mut_lists.get(vname, ""),
                    "h1_north": h1_cls, "h2_north": h2_cls, "cdr3_len": row.get('cdr3_len_check', 0),
                    "gp_frac": row.get('cdr3_gp_frac', 0), "hydrophobic": row.get('cdr3_hydrophobic_frac', 0),
                    "aromatic": row.get('cdr3_aromatic_frac', 0), "ngly_sites": row.get('cdr3_ngly_motifs', 0)
                })
            else: audit["fails"] += 1

    if all_preds:
        full_df = pd.concat(all_preds)
        full_df.columns = [c.lower().replace(' ', '_') for c in full_df.columns]
        rank_col = 'percentile_rank' if 'percentile_rank' in full_df.columns else 'rank'
        if rank_col not in full_df.columns:
            possible = [c for c in full_df.columns if 'rank' in c]
            if possible: rank_col = possible[0]
        full_df.to_parquet(PREDICTIONS_PARQUET, index=False)
        feat_df = pd.DataFrame(features)
        
        enriched = []
        for ab_id, group in feat_df.groupby('antibody_id'):
            native_peps = set(full_df[(full_df['antibody_id'] == ab_id) & (full_df['variant'] == 'native') & (full_df[rank_col] <= args.rank_strong)]['peptide'].tolist())
            cdr3_seq = df_master[df_master['antibody_id'] == ab_id]['cdr3'].iloc[0] if not df_master[df_master['antibody_id'] == ab_id].empty else ""
            for _, r in group.iterrows():
                var_peps = set(full_df[(full_df['antibody_id'] == ab_id) & (full_df['variant'] == r['variant']) & (full_df[rank_col] <= args.rank_strong)]['peptide'].tolist())
                added, removed = var_peps - native_peps, native_peps - var_peps
                r['Added_1pct'], r['Removed_1pct'] = len(added), len(removed)
                r['Added_in_CDR3_1pct'] = sum(1 for p in added if cdr3_seq and p in cdr3_seq)
                enriched.append(r)
        
        feat_df = pd.DataFrame(enriched)
        feat_df.to_csv(FEATURES_CSV, index=False)
        
        deltas = []
        for ab_id, g in feat_df.groupby('antibody_id'):
            sr, bm = g[g['variant'] == 'sr'], g[g['variant'] == 'bm']
            if sr.empty or bm.empty: continue
            sr, bm = sr.iloc[0], bm.iloc[0]
            d_novel = (sr['Added_1pct'] - 0.5 * sr['Removed_1pct']) - (bm['Added_1pct'] - 0.5 * bm['Removed_1pct'])
            rec = "tie"
            if d_novel < -0.5: rec = "SR immuno-favored"
            elif d_novel > 0.5: rec = "BM immuno-favored"
            elif (sr['B_breadth_1pct'] - bm['B_breadth_1pct']) < 0: rec = "SR immuno-favored"
            elif (sr['B_breadth_1pct'] - bm['B_breadth_1pct']) > 0: rec = "BM immuno-favored"
            deltas.append({"antibody_id": ab_id, "delta_novel_1pct": d_novel, "delta_added_cdr3_1pct": sr['Added_in_CDR3_1pct'] - bm['Added_in_CDR3_1pct'], "delta_breadth_1pct": sr['B_breadth_1pct'] - bm['B_breadth_1pct'], "recommendation": rec})
        
        delta_df = pd.DataFrame(deltas)
        delta_df.to_csv(DELTA_TABLE_CSV, index=False)
        
        # Clustering
        X = delta_df[['delta_novel_1pct', 'delta_added_cdr3_1pct', 'delta_breadth_1pct']].values
        Z = linkage(X, 'ward')
        clusters = fcluster(Z, t=4, criterion='maxclust')
        delta_df['cluster'] = clusters

        with open(CLUSTER_REPORT_MD, 'w', encoding='utf-8') as f:
            f.write("# VHH Immunogenicity Cluster Report (SR vs BM)\n\n")
            f.write("## 4-Quadrant Stratification\n")
            q1 = delta_df[(delta_df['delta_novel_1pct'] > 0) & (delta_df['delta_added_cdr3_1pct'] > 0)]
            q2 = delta_df[(delta_df['delta_novel_1pct'] <= 0) & (delta_df['delta_added_cdr3_1pct'] > 0)]
            q3 = delta_df[(delta_df['delta_novel_1pct'] <= 0) & (delta_df['delta_added_cdr3_1pct'] <= 0)]
            q4 = delta_df[(delta_df['delta_novel_1pct'] > 0) & (delta_df['delta_added_cdr3_1pct'] <= 0)]
            f.write(f"- Q1 (High Risk BM, High Risk CDR3): {len(q1)}\n")
            f.write(f"- Q2 (Low Risk BM, High Risk CDR3): {len(q2)}\n")
            f.write(f"- Q3 (Low Risk BM, Low Risk CDR3): {len(q3)}\n")
            f.write(f"- Q4 (High Risk BM, Low Risk CDR3): {len(q4)}\n\n")
            
            f.write("## Cluster Summary\n")
            f.write(delta_df.groupby('cluster')[['delta_novel_1pct', 'delta_added_cdr3_1pct']].mean().to_markdown() + "\n\n")
            
            f.write("## Strategy Recommendations\n" + delta_df['recommendation'].value_counts().to_markdown() + "\n\n")
            f.write("## Top 5 SR-better\n" + delta_df.sort_values('delta_novel_1pct').head(5).to_markdown(index=False) + "\n\n")
            f.write("## Top 5 BM-better\n" + delta_df.sort_values('delta_novel_1pct', ascending=False).head(5).to_markdown(index=False) + "\n\n")

    audit["end"] = time.ctime()
    with open(AUDIT_MD, 'w') as f:
        f.write("# IEDB Audit Log\n\n")
        for k, v in audit.items(): f.write(f"- {k}: {v}\n")
        f.write("- IMGT numbering: ANARCII (core.numbering.imgt_anarcii.imgt_number_anarcii)\n")
    print(f"Done. Reports in {REPORTS_DIR}")

    # Write annotated mutation JSONL for downstream functional analyses
    mut_path = OUTPUT_DIR / "slice3_vhh_variant_mutations_immuno.jsonl"
    with open(mut_path, "w", encoding="utf-8") as f:
        for m in mutations_annotated:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"Wrote mutation audit: {mut_path}")

if __name__ == "__main__": main()
