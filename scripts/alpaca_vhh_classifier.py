#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
alpaca_vhh_classifier.py

FR2 hallmark（37/44/45/47）IGHVVHH/VH
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Tuple, Optional

# abnumber（）
try:
    from abnumber import Chain as AbChain
    HAS_ABNUMBER = True
except ImportError:
    HAS_ABNUMBER = False

# ANARCI/anarcii
HAS_ANARCI = False
HAS_ANARCII = False
try:
    from anarci import run_anarci
    HAS_ANARCI = True
except ImportError:
    try:
        from anarci import anarci as run_anarci
        HAS_ANARCI = True
    except ImportError:
        # anarcii（i）- API
        try:
            from anarcii import Anarcii
            HAS_ANARCII = True
        except ImportError:
            HAS_ANARCII = False

# （）
HAS_ADAPTER = False
try:
    import sys
    adapter_path = Path(__file__).parent
    if str(adapter_path) not in sys.path:
        sys.path.insert(0, str(adapter_path))
    from anarci_abnumber_adapter import annotate_chain
    HAS_ADAPTER = True
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALPACA_DIR = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa"
FASTA_FILE = ALPACA_DIR / "IGHV_aa.fasta"
OUTPUT_TSV = ALPACA_DIR / "alpaca_ighv_vhh_label.tsv"


def read_fasta(fp: Path):
    """FASTA，(header, sequence)"""
    name = None
    seq = []
    
    if not fp.exists():
        raise FileNotFoundError(f"FASTA file not found: {fp}")
    
    with open(fp, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(seq)
                name = line[1:]
                seq = []
            else:
                seq.append(line)
        if name is not None:
            yield name, "".join(seq)


def get_imgt_map(seq_id: str, seq: str) -> Dict[int, str]:
    """
    IMGTfallback，: {position_number -> amino_acid}
    
    Args:
        seq_id: ID
        seq: 
    
    Returns:
        ， {37: 'F', 44: 'E', 45: 'R', 47: 'G'}
    """
    # （）
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parents[1]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map
        
        rows = imgt_number_anarcii(seq)
        pos_map = build_pos_to_aa_map(rows)
        
        if pos_map:
            return pos_map
    except ImportError:
        # ，
        pass
    except Exception:
        # ，
        pass
    
    pos_map = {}
    
    # Fallback: abnumber（、）
    # ：abnumberanarci，anarcii
    if HAS_ABNUMBER:
        try:
            ab_chain = AbChain(seq, scheme="imgt", chain_type="H")
            regions = ab_chain.regions  # dict: region -> {Position: aa}
            
            for region_name, pos_dict in regions.items():
                for pos_obj, aa in pos_dict.items():
                    pos_num = pos_obj.number
                    if isinstance(pos_num, int):
                        pos_map[pos_num] = aa
            
            if pos_map:  # ，
                return pos_map
        except Exception:
            # abnumber（anarci），
            pass
    
    # anarcii（abnumber）
    if HAS_ANARCII:
        try:
            from anarcii import Anarcii
            anarcii_obj = Anarcii()
            result = anarcii_obj.number(seq)
            
            # anarcii: {'Sequence': {'numbering': [((pos, ins), aa), ...], ...}}
            if isinstance(result, dict) and "Sequence" in result:
                seq_info = result["Sequence"]
                numbering = seq_info.get("numbering", [])
                
                for item in numbering:
                    if isinstance(item, tuple) and len(item) >= 2:
                        pos_info, aa = item[0], item[1]
                        if pos_info and isinstance(pos_info, tuple) and len(pos_info) >= 1:
                            pos_num = pos_info[0]
                            if isinstance(pos_num, int) and aa != "-":  # gap
                                pos_map[pos_num] = aa
            
            if pos_map:
                return pos_map
        except Exception:
            # ，
            pass
    
    # （abnumberANARCI fallback）
    if HAS_ADAPTER:
        try:
            annotation = annotate_chain(seq, scheme="imgt", chain_type_hint="H")
            for pos_record in annotation.positions:
                # ， "H37", "H44A"
                pos_str = pos_record.pos
                if pos_str and pos_str.startswith("H"):
                    try:
                        # （H）
                        pos_num_str = pos_str[1:].rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                        pos_num = int(pos_num_str)
                        pos_map[pos_num] = pos_record.aa
                    except (ValueError, IndexError):
                        continue
            if pos_map:  # ，
                return pos_map
        except Exception:
            # ，ANARCI
            pass
    
    # ANARCI（i，anarcii）
    if HAS_ANARCI:
        try:
            # run_anarci（API）
            try:
                res = run_anarci([(seq_id, seq)], scheme="imgt")
                
                # run_anarci: (seqs, all_numberings, alignment_details, hit_tables)
                if isinstance(res, tuple) and len(res) >= 2:
                    all_numberings = res[1]
                    if all_numberings and len(all_numberings) > 0:
                        domains = all_numberings[0]
                        if domains and len(domains) > 0:
                            numbering = domains[0]
                            
                            # numbering
                            if isinstance(numbering, list):
                                for item in numbering:
                                    if isinstance(item, tuple) and len(item) >= 2:
                                        pos_info, aa = item[0], item[1]
                                        if pos_info and isinstance(pos_info, tuple) and len(pos_info) >= 2:
                                            pos_num = pos_info[0]
                                            if isinstance(pos_num, int):
                                                pos_map[pos_num] = aa
                            elif isinstance(numbering, tuple):
                                # ((pos, ins), aa)
                                for item in numbering:
                                    if isinstance(item, tuple) and len(item) >= 2:
                                        pos_info, aa = item[0], item[1]
                                        if pos_info and isinstance(pos_info, tuple) and len(pos_info) >= 1:
                                            pos_num = pos_info[0]
                                            if isinstance(pos_num, int):
                                                pos_map[pos_num] = aa
            except Exception:
                # anarci（API）
                try:
                    from anarci import anarci
                    res = anarci([(seq_id, seq)], scheme="imgt")
                    
                    # anarci: (assignments, alignment_details, hit_tables)
                    if isinstance(res, tuple) and len(res) >= 1:
                        assignments = res[0]
                        if assignments and len(assignments) > 0:
                            assignment = assignments[0]
                            if assignment and len(assignment) >= 1:
                                numbering = assignment[0]
                                
                                # numbering: [(aa, (pos, ins_code), region), ...]
                                if isinstance(numbering, list):
                                    for item in numbering:
                                        if isinstance(item, tuple) and len(item) >= 2:
                                            aa = item[0]
                                            pos_info = item[1]
                                            if pos_info and isinstance(pos_info, tuple) and len(pos_info) >= 1:
                                                pos_num = pos_info[0]
                                                if isinstance(pos_num, int):
                                                    pos_map[pos_num] = aa
                except Exception:
                    pass
        except Exception:
            pass
    
    return pos_map


def classify_vhh_from_fr2(pos_map: Dict[int, str]) -> Tuple[str, float, str, str, str, str]:
    """
    IMGT37/44/45/47，VHH
    
    VHHFR2 hallmark：
    - 44: QE（）
    - 45: R（）
    - 47: GL（）
    - 37: （Y, S, N, T, H, Q）
    
    Args:
        pos_map: IMGT
    
    Returns:
        (label, score, aa37, aa44, aa45, aa47)
    """
    aa37 = pos_map.get(37, "-")
    aa44 = pos_map.get(44, "-")
    aa45 = pos_map.get(45, "-")
    aa47 = pos_map.get(47, "-")
    
    score = 0.0
    
    # 44: Q/EVHH
    if aa44 in ("Q", "E"):
        score += 1.0
    
    # 45: RVHH
    if aa45 == "R":
        score += 1.0
    
    # 47: G/LVHH
    if aa47 in ("G", "L"):
        score += 1.0
    
    # 37: /
    if aa37 in ("Y", "S", "N", "T", "H", "Q"):
        score += 0.5
    
    # ：score >= 2 VHH
    label = "VHH" if score >= 2.0 else "VH"
    
    return label, score, aa37, aa44, aa45, aa47


def main():
    print("=" * 80)
    print("IGHVVHH/VH")
    print("=" * 80)
    
    if not FASTA_FILE.exists():
        print(f"[ERROR] FASTA: {FASTA_FILE}")
        return 1
    
    if not HAS_ABNUMBER and not HAS_ANARCI and not HAS_ANARCII and not HAS_ADAPTER:
        print("[ERROR] IMGT")
        print("\n：")
        print("  pip install abnumber  ()")
        print("  ")
        print("  pip install anarci")
        print("  ")
        print("  pip install anarcii")
        return 1
    
    # 
    tool_name = ""
    if HAS_ABNUMBER:
        tool_name = "abnumber"
    elif HAS_ADAPTER:
        tool_name = " (abnumber/ANARCI)"
    elif HAS_ANARCII:
        tool_name = "anarcii"
    elif HAS_ANARCI:
        tool_name = "ANARCI"
    
    print(f"\n[INFO] : {tool_name}")
    
    rows = []
    total = 0
    success = 0
    failed = 0
    
    print(f"\n[1] FASTA: {FASTA_FILE}")
    print("-" * 80)
    
    for name, seq in read_fasta(FASTA_FILE):
        total += 1
        if total % 10 == 0:
            print(f"  : {total}...", end="\r")
        
        # IMGT
        pos_map = get_imgt_map(name, seq)
        
        if not pos_map:
            print(f"\n[WARN] IMGT: {name[:50]}")
            failed += 1
            # ，
            rows.append({
                "id": name,
                "length": len(seq),
                "label": "UNKNOWN",
                "vhh_score": 0.0,
                "aa37": "-",
                "aa44": "-",
                "aa45": "-",
                "aa47": "-",
            })
            continue
        
        # 
        label, score, aa37, aa44, aa45, aa47 = classify_vhh_from_fr2(pos_map)
        
        rows.append({
            "id": name,
            "length": len(seq),
            "label": label,
            "vhh_score": score,
            "aa37": aa37,
            "aa44": aa44,
            "aa45": aa45,
            "aa47": aa47,
        })
        success += 1
    
    print(f"\n  : {total}，{success}，{failed}")
    
    # 
    vhh_count = sum(1 for r in rows if r["label"] == "VHH")
    vh_count = sum(1 for r in rows if r["label"] == "VH")
    unknown_count = sum(1 for r in rows if r["label"] == "UNKNOWN")
    
    print(f"\n[2] ")
    print("-" * 80)
    print(f"  VHH: {vhh_count}")
    print(f"  VH:  {vh_count}")
    if unknown_count > 0:
        print(f"  UNKNOWN: {unknown_count}")
    
    # TSV
    print(f"\n[3] : {OUTPUT_TSV}")
    print("-" * 80)
    
    with open(OUTPUT_TSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "length", "label", "vhh_score", "aa37", "aa44", "aa45", "aa47"],
            delimiter="\t"
        )
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"  [OK]  {len(rows)} ")
    
    # VHH
    vhh_examples = [r for r in rows if r["label"] == "VHH"][:5]
    if vhh_examples:
        print(f"\n[4] VHH（5）")
        print("-" * 80)
        for r in vhh_examples:
            print(f"  {r['id'][:60]}")
            print(f"    : 37={r['aa37']}, 44={r['aa44']}, 45={r['aa45']}, 47={r['aa47']} (score={r['vhh_score']})")
    
    print(f"\n{'='*80}")
    print("！")
    print(f"{'='*80}")
    print(f"\n: {OUTPUT_TSV}")
    
    return 0


if __name__ == "__main__":
    exit(main())
