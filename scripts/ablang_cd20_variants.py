"""One-off: AbLang2 paired PLL for mouse_cd20 humanization variant table."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))

OUT = SUITE / "projects/mouse_cd20_humanization"
seqs_main = json.loads((OUT / "humanized_sequences.json").read_text())
seqs_graft = json.loads((OUT / "graft_surface_compare.json").read_text())["variants"]

VH_RITUX = (
    "QVQLQQPGAELVKPGASVKMSCKASGYTFTSYAMSWVKQTPGQGLEWMGAINPSGGSTYFQKFKGKATLTADESSSTAYMQLSSLTSEDSAVYYCARNYYGSSTYYWGAGTTVTVSS"
)
VL_RITUX = (
    "QIVLSQSPAILSASPGEKVTMTCRASSSVSYIHWFQQKPGSSPKPWIYATSNLASGVPARFSGSGSGTDFTLTISSVQAEDIADYYCQQWTSNPPTFGGGTKLEIK"
)

variants: dict[str, tuple[str, str]] = {
    "Murine_Parent": (seqs_main["murine"]["vh"], seqs_main["murine"]["vl"]),
    "DEEP-FR": (seqs_main["deepfr"]["vh"], seqs_main["deepfr"]["vl"]),
    "9AA-CTX": (seqs_main["9aa_ctx"]["vh"], seqs_main["9aa_ctx"]["vl"]),
    "9AA-CTX-Aggressive": (
        seqs_main.get("9aa_ctx_aggressive", seqs_main["9aa_ctx"])["vh"],
        seqs_main.get("9aa_ctx_aggressive", seqs_main["9aa_ctx"])["vl"],
    ),
    "Graft_Pure": (seqs_graft["cdr_graft_pure"]["vh"], seqs_graft["cdr_graft_pure"]["vl"]),
    "Graft_Vernier": (
        seqs_graft["cdr_graft_vernier_bm"]["vh"],
        seqs_graft["cdr_graft_vernier_bm"]["vl"],
    ),
    "Surface_Reshape": (seqs_graft["surface_reshaping"]["vh"], seqs_graft["surface_reshaping"]["vl"]),
    "Clinical_Ritux": (VH_RITUX, VL_RITUX),
}


def main() -> None:
    import ablang2  # noqa: PLC0415

    model = ablang2.pretrained("ablang2-paired")
    rows: list[tuple[str, float]] = []
    for name, (vh, vl) in variants.items():
        pll = model([(vh.upper(), vl.upper())], mode="pseudo_log_likelihood")
        v = round(float(np.squeeze(pll)), 3)
        rows.append((name, v))

    print("metric: AbLang2 paired pseudo_log_likelihood (ablang2-paired); higher ≈ more repertoire-like")
    print("| Variant | AbLang2 PLL |")
    print("|---|---|")
    for name, v in rows:
        print(f"| {name} | {v} |")

    payload = [
        {"variant": name, "ablang2_paired_pll": v, "method": "ablang2-paired pseudo_log_likelihood"}
        for name, v in rows
    ]
    (OUT / "ablang2_comparison.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT / 'ablang2_comparison.json'}")


if __name__ == "__main__":
    main()
