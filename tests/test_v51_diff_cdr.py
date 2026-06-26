"""V5.1.0 unit tests for `_diff_cdr_positions_v51` — the Phase 4.8 hard-gate
CDR diff function.

These tests do NOT invoke the full Phase 1-5 pipeline (no IgFold /
ABodyBuilder2 / structure modeling). They only call ANARCII for sequence
re-numbering, which takes ~3-5 s on first call (model load) and ~50 ms
afterwards. Fast enough to run in CI commit gates.

Background:
  Pre-V5.1 the Phase 4.8 gate consumed a hardcoded `cdr_integrity_check =
  True`. The diff logic now lives in `_diff_cdr_positions_v51` and is
  unit-tested here in isolation. See `docs/EVOLUTION_LOG.md` 2026-05-01
  [EXECUTED] V5.1 P0 Bugfix.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


# R5-307 reference sequences (mus_musculus, real project case).
MOUSE_VH = (
    "DVKLVESGGGLVQPKGSLKLSCAASGIPFNTYAMNWVRQAPGKGLEWVAR"
    "IRTKSNNYVTYYAASVKDRFTISRDDSQSMLYLQMSNLKTEDTAMYYCVS"
    "LGDWAYWGQGTLVTVSS"
)
MOUSE_VL = (
    "DVVMTQSPTTMAASPGEKITITCSATSRIDSNYLHWYQQKPGFSPQLLIY"
    "RTSNLASGVPARFSGSGSGTSYSLTIGTMEAEDVATYYCQQGSTLPLTFG"
    "TGTKLELK"
)
# V5.1.0 humanized counterpart from the regression run cli_00d4c7c00937.
HUM_VH_V51 = (
    "EVQLLESGGGLVQPGGSLRLSCAASGIPFNTYAMSWVRQAPGKGLEWVAR"
    "IRTKSNNYVTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCVS"
    "LGDWAYWGQGTLVTVSS"
)
HUM_VL_V51 = (
    "DIQMTQSPSSLSASVGDRVTITCRATSRIDSNYLNWYQQKPGKAPQLLIY"
    "RTSSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQGSTLPLTFG"
    "GGTKLEIK"
)
# V5.0.0 (legacy) humanized — strict Chothia, paratope-adjacent residues
# silently humanized at IMGT positions 36, 40, 57.
HUM_VH_V50_BROKEN = (
    "EVQLLESGGGLVQPGGSLRLSCAASGIPFSSYAMSWVRQAPGKGLEWVAR"  # pos 30/31 humanized vs mouse
    "IRTKSNNYVTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCVS"
    "LGDWAYWGQGTLVTVSS"
)


class TestV51DiffCdrPositions(unittest.TestCase):
    """Hard-gate diff function — Phase 4.8 truth source."""

    @classmethod
    def setUpClass(cls) -> None:
        # Trigger ANARCII model load once, up-front.
        try:
            from core.humanization.engine import _get_anarcii  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest(f"Cannot import engine ({exc})")

    # ------------------------------------------------------------------
    # 1. Identity ⇒ empty diff
    # ------------------------------------------------------------------
    def test_identical_donor_humanized_returns_empty(self) -> None:
        from core.humanization.engine import _diff_cdr_positions_v51

        diff_vh = _diff_cdr_positions_v51(MOUSE_VH, MOUSE_VH, "H")
        diff_vl = _diff_cdr_positions_v51(MOUSE_VL, MOUSE_VL, "K")
        self.assertEqual(diff_vh, [], "donor=hum should yield no CDR diff for VH.")
        self.assertEqual(diff_vl, [], "donor=hum should yield no CDR diff for VL.")

    # ------------------------------------------------------------------
    # 2. R5-307 V5.1 humanized output ⇒ empty diff (regression case)
    # ------------------------------------------------------------------
    def test_r5_307_v51_humanized_passes_hard_gate(self) -> None:
        from core.humanization.engine import _diff_cdr_positions_v51

        diff_vh = _diff_cdr_positions_v51(MOUSE_VH, HUM_VH_V51, "H")
        diff_vl = _diff_cdr_positions_v51(MOUSE_VL, HUM_VL_V51, "K")
        self.assertEqual(
            diff_vh, [],
            f"R5-307 V5.1 humanized VH should preserve all Union CDR positions; "
            f"got {len(diff_vh)} diff rows: {diff_vh[:3]}",
        )
        self.assertEqual(
            diff_vl, [],
            f"R5-307 V5.1 humanized VL should preserve all Union CDR positions; "
            f"got {len(diff_vl)} diff rows: {diff_vl[:3]}",
        )

    # ------------------------------------------------------------------
    # 3. R5-307 V5.0 humanized output ⇒ non-empty diff (bug regression)
    # ------------------------------------------------------------------
    def test_v50_legacy_output_fails_hard_gate(self) -> None:
        """V5.0 strict Chothia output silently humanized IMGT 36/40/57.

        Under V5.1 Union ruler, those are CDR positions and MUST be flagged.
        If this test ever passes (i.e., V5.0 broken output goes undetected),
        the hard gate has regressed.
        """
        from core.humanization.engine import _diff_cdr_positions_v51

        diff_vh = _diff_cdr_positions_v51(MOUSE_VH, HUM_VH_V50_BROKEN, "H")
        self.assertGreater(
            len(diff_vh), 0,
            "V5.0 broken VH (humanized at IMGT 30/31) MUST be flagged by V5.1 hard gate. "
            "If this test fails, the diff function is no longer catching the original bug.",
        )
        # Sanity: the bad position must be a real CDR-H1 IMGT position.
        cdr_h1_imgt = set(range(27, 39))  # canonical IMGT CDR-H1
        bad_positions = {int(d["pos"].rstrip("ABCDE") or 0) for d in diff_vh if d.get("pos", "").rstrip("ABCDE").isdigit()}
        self.assertTrue(
            bad_positions & cdr_h1_imgt,
            f"V5.0-broken diff should locate at least one IMGT CDR-H1 position (27-38); "
            f"got positions: {sorted(bad_positions)}",
        )

    # ------------------------------------------------------------------
    # 4. Unknown chain code defaults gracefully (no crash)
    # ------------------------------------------------------------------
    def test_unknown_chain_code_does_not_crash(self) -> None:
        from core.humanization.engine import _diff_cdr_positions_v51

        diff = _diff_cdr_positions_v51(MOUSE_VH, MOUSE_VH, "X")
        # Identical donor=hum → still no diff regardless of chain code.
        self.assertEqual(diff, [],
                         "Unknown chain code should not produce spurious diff rows on identical inputs.")

    # ------------------------------------------------------------------
    # 5. Output schema — every diff row carries the required keys
    # ------------------------------------------------------------------
    def test_diff_row_schema(self) -> None:
        from core.humanization.engine import _diff_cdr_positions_v51

        diff_vh = _diff_cdr_positions_v51(MOUSE_VH, HUM_VH_V50_BROKEN, "H")
        self.assertGreater(len(diff_vh), 0, "Need at least one diff row to inspect schema.")
        required = {"chain", "pos", "donor", "humanized"}
        for row in diff_vh:
            with self.subTest(row=row):
                self.assertTrue(required.issubset(row.keys()),
                                f"Diff row missing required keys: {required - row.keys()}")
                self.assertIn(row["chain"], ("VH", "VL"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
