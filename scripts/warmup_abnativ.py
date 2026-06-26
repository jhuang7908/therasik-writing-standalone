#!/usr/bin/env python3
"""One-shot AbNatiV model warm-up — run at API boot to avoid first-request timeouts."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.toolchain_env import ensure_toolchain_path

ensure_toolchain_path()

VH = (
    "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARDRVTGAFDIWGQGTMVTVSS"
)
VL = (
    "DIQMTQSPSSLSASVGDRVTITCRASQDVSTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSRSGTDFTLTISSLQPEDFATYYCQQYLYHPATFGQGTKVEIK"
)


def main() -> int:
    from core.humanization.p_abnativ_layer import score_paired_humanness

    res = score_paired_humanness(VH, VL, seq_id="warmup")
    if res.error:
        print(f"warmup FAIL: {res.error}", file=sys.stderr)
        return 1
    print(
        f"warmup OK paired={res.paired_humanness} vh={res.vh_humanness} vl={res.vl_humanness}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
