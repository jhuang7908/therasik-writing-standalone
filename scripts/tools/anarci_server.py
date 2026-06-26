from fastapi import FastAPI
from pydantic import BaseModel
from anarci import run_anarci

app = FastAPI()


class AnarciRequest(BaseModel):
    seq: str
    scheme: str = "imgt"


@app.post("/imgt_numbering")
def imgt_numbering(req: AnarciRequest):
    """
     ANARCI， IMGT 。
     run_anarci ：
        res = (seqs, all_numberings, alignment_details, hit_tables)
    """

    # 1. 
    seq = req.seq.strip().upper().replace(" ", "").replace("*", "")
    if len(seq) < 50:
        return {
            "success": False,
            "error": "Sequence too short for V-region numbering",
            "length": len(seq),
        }

    # 2.  ANARCI
    try:
        res = run_anarci([("query", seq)], scheme=req.scheme)
    except Exception as e:
        return {"success": False, "error": f"ANARCI failed: {e}"}

    # 3. 
    # res  4 
    if not isinstance(res, tuple) or len(res) < 2:
        return {
            "success": False,
            "error": f"Unexpected ANARCI return structure: type={type(res)}, len={len(res) if hasattr(res, '__len__') else 'N/A'}",
        }

    seqs = res[0]             # [('query', 'EVQLV....')]
    all_numberings = res[1]   # [[domain0, domain1, ...]]

    if not seqs or not all_numberings:
        return {"success": False, "error": "Empty ANARCI result"}

    # seq_id / （）
    try:
        seq_id, orig_seq = seqs[0]
    except Exception:
        seq_id = "query"
        orig_seq = seq

    # 4.  domain 
    domains = all_numberings[0]
    if not domains:
        return {"success": False, "error": "No domains returned"}

    domain0 = domains[0]

    # ：
    #  A: domain0 = ([((1,' '),'E'), ...], meta...) → 
    #  B: domain0 = [((1,' '),'E'), ...]           → 
    if isinstance(domain0, tuple) and domain0 and isinstance(domain0[0], list):
        numbering_raw = domain0[0]
    else:
        numbering_raw = domain0

    numbered_residues = []
    for item in numbering_raw:
        # ：((1, ' '), 'E')
        try:
            (pos, ins_code), aa = item
        except Exception:
            # ，
            continue

        ins = None
        if isinstance(ins_code, str):
            ins = ins_code.strip() or None

        numbered_residues.append(
            {
                "position": pos,          # IMGT （）
                "insertion_code": ins,    # 'A' / 'B'  None
                "aa": aa,                 # 
            }
        )

    if not numbered_residues:
        return {
            "success": False,
            "error": f"Failed to parse numbering from domain0: {repr(domain0)[:200]}",
        }

    # 5.  V  IMGT （）
    v_start = numbered_residues[0]["position"]
    v_end = numbered_residues[-1]["position"]

    return {
        "success": True,
        "seq_id": seq_id,
        "v_start": v_start,
        "v_end": v_end,
        "length": len(numbered_residues),
        "chain_type": "H",  # ，
        "numbering": numbered_residues,
    }
