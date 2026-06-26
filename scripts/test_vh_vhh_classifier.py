from anarci_client import imgt_number
from vh_vhh_classifier import classify_vh_vhh

#  VH （ CDR3）
seq_vh = (
    "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVK"
    "GRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
)

#  VHH （CDR3 ，FR2/FR4  VHH ）
seq_vhh = (
    "QVQLVESGGGLVQAGGSLRLSCAASGRTFSSYAMGWFRQAPGKEREGVAAISWSGGSTYYADSVK"
    "GRFTISRDNAKNTVYLQMNSLKPEDTAVYYCAAGGYGSSHWYFDVWGQGTQVTVSS"
)


def run_one(label: str, seq: str):
    res = imgt_number(seq)
    numbering = res["numbering"]
    cls = classify_vh_vhh(numbering)

    print(f"\n=== {label}  ===")
    print("seq length:", len(seq))
    print("is_vhh_like:", cls["is_vhh_like"])
    print("score:", cls["score"])
    print("features:", cls["features"])


if __name__ == "__main__":
    run_one("VH", seq_vh)
    run_one("VHH", seq_vhh)
