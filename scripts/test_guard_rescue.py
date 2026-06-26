#!/usr/bin/env python3
"""
Generate the finalized DeepFR-CTX rat Campath variant.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))

from core.humanization.ctx_guard import apply_deepfr_ctx

PROJ = SUITE / "projects" / "rat_campath_console_humanization"


def main():
    data = json.loads((PROJ / "humanized_sequences.json").read_text(encoding="utf-8"))

    rat_vh = data["rat_parent"]["vh"]
    rat_vl = data["rat_parent"]["vl"]
    deepfr_vh = data["DEEP_FR"]["vh"]
    deepfr_vl = data["DEEP_FR"]["vl"]

    print("=== Applying DeepFR-CTX to VH ===")
    vh_rescued, vh_rollbacks, vh_rescues = apply_deepfr_ctx(
        deepfr_vh, rat_vh, chain="VH", germline=""
    )
    print(f"VH final rollbacks: {len(vh_rollbacks)}, rescued (kept DEEP-FR): {len(vh_rescues)}")
    for rb in vh_rollbacks:
        print(f"  ROLLBACK {rb['segment']} pos{rb['pos']}: {rb['humanized_aa']} -> {rb['donor_aa']} "
              f"({rb.get('reason','')})")
    for rs in vh_rescues:
        print(f"  RESCUE   {rs['segment']} pos{rs['pos']}: keep DEEP-FR '{rs['deepfr_aa']}' "
              f"(OAS windows={rs['oas_support_windows']})")

    print("\n=== Applying DeepFR-CTX to VL ===")
    vl_rescued, vl_rollbacks, vl_rescues = apply_deepfr_ctx(
        deepfr_vl, rat_vl, chain="VK", germline=""
    )
    print(f"VL final rollbacks: {len(vl_rollbacks)}, rescued (kept DEEP-FR): {len(vl_rescues)}")
    for rb in vl_rollbacks:
        print(f"  ROLLBACK {rb['segment']} pos{rb['pos']}: {rb['humanized_aa']} -> {rb['donor_aa']} "
              f"({rb.get('reason','')})")
    for rs in vl_rescues:
        print(f"  RESCUE   {rs['segment']} pos{rs['pos']}: keep DEEP-FR '{rs['deepfr_aa']}' "
              f"(OAS windows={rs['oas_support_windows']})")

    data["DEEP_FR_9AA_Guard_Rescue"] = {
        "vh": vh_rescued,
        "vl": vl_rescued,
        "vh_rollbacks": vh_rollbacks,
        "vl_rollbacks": vl_rollbacks,
        "vh_rescues": vh_rescues,
        "vl_rescues": vl_rescues,
    }
    data["DeepFR_CTX"] = data["DEEP_FR_9AA_Guard_Rescue"]
    (PROJ / "humanized_sequences.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    print("\nUpdated humanized_sequences.json with DeepFR_CTX")


if __name__ == "__main__":
    main()
