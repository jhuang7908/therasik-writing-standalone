"""
 ANARCI HTTP 
 WSL  FastAPI  IMGT 
"""

import requests

ANARCI_URL = "http://localhost:9000/imgt_numbering"


class AnarciError(RuntimeError):
    pass


def imgt_number(seq: str, scheme: str = "imgt") -> dict:
    """
     WSL  anarci_server， JSON。

    （）：
    {
        "success": True,
        "seq_id": "query",
        "v_start": 1,
        "v_end": 128,
        "length": 128,
        "chain_type": "H",
        "numbering": [
            {"position": 1, "insertion_code": null, "aa": "E"},
            ...
        ]
    }
    """
    seq = (seq or "").strip()
    if not seq:
        raise ValueError("Empty sequence for ANARCI")

    payload = {"seq": seq, "scheme": scheme}

    try:
        resp = requests.post(ANARCI_URL, json=payload, timeout=30)
    except Exception as e:
        raise AnarciError(f"Cannot reach ANARCI server at {ANARCI_URL}: {e}")

    try:
        data = resp.json()
    except Exception as e:
        raise AnarciError(
            f"Invalid JSON from ANARCI server: {e}; text={resp.text[:200]!r}"
        )

    if not data.get("success"):
        # ，
        raise AnarciError(f"ANARCI server error: {data}")

    return data


if __name__ == "__main__":
    # 
    test_seq = (
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVK"
        "GRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
    )
    res = imgt_number(test_seq)
    print("success:", res["success"])
    print("seq_id:", res["seq_id"])
    print("V region:", res["v_start"], "→", res["v_end"], "len =", res["length"])
    print("first 5 residues:")
    for item in res["numbering"][:5]:
        print(item)

