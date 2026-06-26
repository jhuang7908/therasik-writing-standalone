import json
import argparse
from pathlib import Path
from typing import Dict, List


HALLMARK_POS = {37, 44, 45, 47}
VERNIER_POS = {27, 29, 30, 48, 49, 71, 73, 78, 94}


def build_residue_table(
    segmentation: Dict,
    best_human_germline_seq: str,
    best_human_germline_id: str,
) -> Dict:
    """
    :
      segmentation:  IMGT 
      best_human_germline_seq:  human germline V  AA 
    :
      residue_table: { "rows": [ ... ] }
    """
    v_seq = segmentation["v_sequence"]
    imgt_positions = segmentation["imgt_positions"]
    regions = segmentation["regions"]

    if len(best_human_germline_seq) < len(v_seq):
        # ，
        raise ValueError("germline  VHH ， IMGT 。")

    rows = []
    for i, (pos, reg, aa_v) in enumerate(zip(imgt_positions, regions, v_seq)):
        aa_gl = best_human_germline_seq[i]

        row = {
            "imgt_pos": int(pos),
            "region": reg,
            "aa_vhh": aa_v,
            "aa_human_gl": aa_gl,
            "germline_id": best_human_germline_id,
            "is_hallmark": int(pos) in HALLMARK_POS,
            "is_vernier": int(pos) in VERNIER_POS,
            "is_match": aa_v == aa_gl,
            "mutation_suggested": False,  #  12 
            "notes": "",
        }

        # ， Back-mutation / CMC / 
        if row["is_hallmark"] and aa_v != aa_gl:
            row["notes"] = "VHH hallmark ， VHH ，"
        elif row["is_vernier"] and aa_v != aa_gl:
            row["notes"] = "Vernier ，/"
        rows.append(row)

    return {
        "vhh_id": segmentation.get("id", "unknown_vhh"),
        "human_germline_id": best_human_germline_id,
        "rows": rows,
    }


def run_vhh_alignment_step11(
    segmentation_path: Path,
    distance_matrix_path: Path,
    human_germline_fasta_path: Path,
    output_path: Path,
) -> None:
    seg = json.loads(segmentation_path.read_text())
    dist = json.loads(distance_matrix_path.read_text())

    #  total_score  type=human  germline
    best = None
    for row in dist["rows"]:
        if row["type"] != "human":
            continue
        if best is None or row["total_score"] < best["total_score"]:
            best = row

    if best is None:
        raise RuntimeError("distance matrix  human germline 。")

    best_id = best["germline_id"]

    #  FASTA， human germline 
    gl_seq = None
    hdr = None
    buf = []
    with human_germline_fasta_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if hdr is not None and best_id in hdr:
                    gl_seq = "".join(buf)
                    break
                hdr = line[1:]
                buf = []
            else:
                buf.append(line)

        if gl_seq is None and hdr is not None and best_id in hdr:
            gl_seq = "".join(buf)

    if gl_seq is None:
        raise ValueError(f" FASTA ({human_germline_fasta_path})  {best_id}")

    residue_table = build_residue_table(seg, gl_seq, best_id)
    output_path.write_text(json.dumps(residue_table, indent=2, ensure_ascii=False))
    print(f"[VHH] residue_table written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Build VHH to human germline residue table (Step 11)"
    )
    parser.add_argument(
        "--segmentation",
        required=True,
        type=Path,
        help="Path to segmentation JSON file"
    )
    parser.add_argument(
        "--distance-matrix",
        required=True,
        type=Path,
        help="Path to distance matrix JSON file (from step 10)"
    )
    parser.add_argument(
        "--human-germline-fasta",
        required=True,
        type=Path,
        help="Path to human VHH-compatible germline FASTA file"
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to output residue table JSON file"
    )
    
    args = parser.parse_args()
    
    run_vhh_alignment_step11(
        segmentation_path=args.segmentation,
        distance_matrix_path=args.distance_matrix,
        human_germline_fasta_path=args.human_germline_fasta,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()




















