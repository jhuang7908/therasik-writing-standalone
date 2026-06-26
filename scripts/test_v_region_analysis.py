from imgt_helper import analyze_v_region

seq_vh = (
    "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVK"
    "GRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
)

seq_vhh = (
    "QVQLVESGGGLVQAGGSLRLSCAASGRTFSSYAMGWFRQAPGKEREGVAAISWSGGSTYYADSVK"
    "GRFTISRDNAKNTVYLQMNSLKPEDTAVYYCAAGGYGSSHWYFDVWGQGTQVTVSS"
)


def run_one(label: str, seq: str):
    res = analyze_v_region(seq)
    print(f"\n====== {label} ======")
    print("success:", res["success"])
    if not res["success"]:
        print("reason:", res.get("reason"))
        return

    print("v_length:", res["v_length"])
    print("v_sequence:", res["v_sequence"])
    print("is_vhh_like:", res["vh_vhh"]["is_vhh_like"])
    print("vh_vhh_score:", res["vh_vhh"]["score"])
    print("vh_vhh_features:", res["vh_vhh"]["features"])

    seg = res["segments"]
    print("\nsegments length:")
    for name, s in seg.items():
        print(f"  {name}: {len(s):3d}")


if __name__ == "__main__":
    run_one("VH", seq_vh)
    run_one("VHH", seq_vhh)
