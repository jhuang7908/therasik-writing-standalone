"""V5.1.0 drift sentinel — assert the three sources of truth for the
Union CDR ruler stay synchronized:

  1. core/humanization/engine.py::_CDR_POS_V51            (IMGT runtime)
  2. config/vh_vl_humanization_v490.json::cdr_definitions  (IMGT runtime + Kabat intent)
  3. core/humanization/kabat_utils.py::CDR_RANGES_VH/VL    (Kabat intent)

Background:
  V5.0 had this exact drift bug — the engine grafted with strict Chothia
  (26-32 / 52-56), `kabat_utils` declared Kabat Union (26-35 / 50-65),
  and the SSOT JSON declared yet a third value, all unchecked. This test
  catches any future drift before it reaches production.

Trigger: R5-307 / Wemol cross-comparison (2026-05-01); see
`docs/EVOLUTION_LOG.md` 2026-05-01 [EXECUTED] entries.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


class TestV51CDRDrift(unittest.TestCase):
    """Three-way alignment check for V5.1 CDR Union ruler."""

    @classmethod
    def setUpClass(cls) -> None:
        # Load the SSOT JSON
        cfg_path = REPO / "config" / "vh_vl_humanization_v490.json"
        with open(cfg_path, encoding="utf-8") as f:
            cls.cfg = json.load(f)

    # ------------------------------------------------------------------
    # 1. SSOT JSON internal consistency
    # ------------------------------------------------------------------
    def test_ssot_meta_version_is_v51(self) -> None:
        """Config must declare V5.1.0 to be active."""
        self.assertEqual(
            self.cfg["_meta"]["version"], "5.1.0",
            "SSOT JSON _meta.version must be 5.1.0 for V5.1 Union grafting to apply.",
        )

    def test_ssot_scheme_is_union(self) -> None:
        """cdr_definitions.scheme must declare Union/IMGT runtime."""
        scheme = self.cfg["cdr_definitions"]["scheme"]
        self.assertEqual(
            scheme, "union_kabat_chothia_imgt",
            f"Expected Union/IMGT scheme, got {scheme!r}.",
        )

    def test_ssot_regions_match_imgt_runtime_view(self) -> None:
        """`regions` (the values consumed at runtime) must equal `regions_imgt_runtime`."""
        cd = self.cfg["cdr_definitions"]
        self.assertEqual(
            cd["regions"], cd["regions_imgt_runtime"],
            "cdr_definitions.regions must mirror regions_imgt_runtime exactly.",
        )

    def test_ssot_imgt_runtime_ranges_are_v51_union(self) -> None:
        """Spot-check the headline V5.1 widening: VH H1=26-38, H2=50-65, H3=105-117."""
        regions = self.cfg["cdr_definitions"]["regions_imgt_runtime"]
        self.assertEqual(regions["VH"]["H1"], [26, 38])
        self.assertEqual(regions["VH"]["H2"], [50, 65])
        self.assertEqual(regions["VH"]["H3"], [105, 117])
        self.assertEqual(regions["VL"]["L1"], [26, 38])
        self.assertEqual(regions["VL"]["L2"], [50, 65])
        self.assertEqual(regions["VL"]["L3"], [105, 117])

    # ------------------------------------------------------------------
    # 2. engine._CDR_POS_V51 ↔ SSOT JSON regions_imgt_runtime
    # ------------------------------------------------------------------
    def test_engine_cdr_pos_matches_ssot_imgt_runtime(self) -> None:
        """engine._CDR_POS_V51 must enumerate exactly the IMGT-runtime ranges in JSON."""
        from core.humanization.engine import _CDR_POS_V51

        regions = self.cfg["cdr_definitions"]["regions_imgt_runtime"]

        def expand(rng_pairs: list) -> set:
            out: set = set()
            for lo, hi in rng_pairs:
                # JSON ranges are inclusive on both ends
                for i in range(lo, hi + 1):
                    out.add(i)
            return out

        vh_expected = expand([
            regions["VH"]["H1"], regions["VH"]["H2"], regions["VH"]["H3"],
        ])
        vl_expected = expand([
            regions["VL"]["L1"], regions["VL"]["L2"], regions["VL"]["L3"],
        ])

        self.assertEqual(set(_CDR_POS_V51["H"]), vh_expected,
                         "engine._CDR_POS_V51['H'] drifted from SSOT regions_imgt_runtime.VH.")
        self.assertEqual(set(_CDR_POS_V51["K"]), vl_expected,
                         "engine._CDR_POS_V51['K'] drifted from SSOT regions_imgt_runtime.VL.")
        self.assertEqual(set(_CDR_POS_V51["L"]), vl_expected,
                         "engine._CDR_POS_V51['L'] drifted from SSOT regions_imgt_runtime.VL.")

    # ------------------------------------------------------------------
    # 3. kabat_utils.CDR_RANGES_* ↔ SSOT JSON regions_kabat_intent
    # ------------------------------------------------------------------
    def test_kabat_utils_matches_ssot_kabat_intent(self) -> None:
        """kabat_utils.CDR_RANGES_VH/VL is the Kabat-intent view; must match SSOT."""
        from core.humanization.kabat_utils import CDR_RANGES_VH, CDR_RANGES_VL

        regions = self.cfg["cdr_definitions"]["regions_kabat_intent"]
        vh_expected = [
            tuple(regions["VH"]["H1"]),
            tuple(regions["VH"]["H2"]),
            tuple(regions["VH"]["H3"]),
        ]
        vl_expected = [
            tuple(regions["VL"]["L1"]),
            tuple(regions["VL"]["L2"]),
            tuple(regions["VL"]["L3"]),
        ]
        self.assertEqual(CDR_RANGES_VH, vh_expected,
                         "kabat_utils.CDR_RANGES_VH drifted from SSOT regions_kabat_intent.VH.")
        self.assertEqual(CDR_RANGES_VL, vl_expected,
                         "kabat_utils.CDR_RANGES_VL drifted from SSOT regions_kabat_intent.VL.")

    # ------------------------------------------------------------------
    # 4. B1 single-ruler invariant: _fr_identity_from_numbered must use
    #    the same ruler as Phase 4 grafting.
    # ------------------------------------------------------------------
    def test_fr_identity_uses_v51_union_ruler(self) -> None:
        """_fr_identity_from_numbered must mask CDR using _CDR_POS_V51 (B1).

        Pre-V5.1 used a strict Chothia narrow mask (26-32/52-56) hardcoded
        in `_is_cdr_pi`. Fed mock numbered dicts where the only mismatch is
        at IMGT position 33 (CDR-H1 under V5.1 Union, but FR under V5.0
        narrow Chothia). FR identity must be 100% under V5.1 (mismatch is
        masked as CDR), not <100%.
        """
        from core.humanization.engine import HumanizationEngine

        # 3 positions: 33 = mismatch in V5.1-CDR; 40 = match in FR2; 80 = match in FR3
        m_dict = {
            (33, ""): "T",  # V5.1 CDR-H1 → masked
            (40, ""): "Q",  # FR2 → counted (match)
            (80, ""): "K",  # FR3 → counted (match)
        }
        g_dict = {
            (33, ""): "S",  # mismatch — but V5.1 masks this as CDR
            (40, ""): "Q",
            (80, ""): "K",
        }
        fr_pct = HumanizationEngine._fr_identity_from_numbered(m_dict, g_dict, "H")
        self.assertEqual(
            fr_pct, 100.0,
            f"_fr_identity_from_numbered should mask IMGT pos 33 as CDR under V5.1 Union, "
            f"giving 100% (2/2 FR positions match). Got {fr_pct}% — likely indicates the "
            f"function still uses the V5.0 narrow Chothia mask (B1 single-ruler violation).",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
