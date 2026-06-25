from fastapi import FastAPI
from pydantic import BaseModel
from anarci import run_anarci

app = FastAPI


class AnarciRequest(BaseModel):
    seq: str
    scheme: str = "imgt"


@app.post("/imgt_numbering")
def imgt_numbering(req: AnarciRequest):
    seq = req.seq.strip.upper.replace(" ", "").replace("*", "")
    if len(seq) < 50:
        return {
            "success": False,
            "error": "Sequence too short for V-region numbering",
            "length": len(seq),
        }

    try:
        assignments, alignment_details, hit_tables = run_anarci(
            [("query", seq)], scheme=req.scheme
        )
    except Exception as e:
        return {"success": False, "error": f"ANARCI failed: {e}"}

    if not assignments or assignments[0] is None:
        return {"success": False, "error": "No domain assigned by ANARCI"}

    seq_info, domains, scores = assignments[0]
    seq_id, orig_seq, (start, end, chain_type) = seq_info

    if not domains:
        return {"success": False, "error": "No numbered domains returned"}

    numbering = domains[0]  #  V  domain

    numbered_residues = []
    for (pos, ins_code), aa in numbering:
        numbered_residues.append(
            {
                "position": pos,
                "insertion_code": ins_code.strip or None,
                "aa": aa,
            }
        )

    return {
        "success": True,
        "seq_id": seq_id,
        "chain_type": chain_type,
        "v_start": start,
        "v_end": end,
        "length": len(numbering),
        "numbering": numbered_residues,
    }
