#!/usr/bin/env python3
"""
core/humanization/contextual_substitution_engine.py
=====================================================
Three-Layer Contextual Substitution Engine for VH/VL Framework Humanization.

This is a NEW module (not modifying any LOCKED files). It implements the
context-aware FR amino acid replacement logic discussed and verified using:

    Layer 1: Protection filter (CDR / Vernier / Hallmark / glyc / cys)
    Layer 2: 9AA peptide-context voting (clinical_842_9mer_db.json)
    Layer 3: CC-FR family/position frequency backoff (cc_fr_table_vhvl_v1.json)
    Layer 4: CMC veto (N-glyc creation, free Cys introduction, charge flip)

All four layers come pre-indexed for O(1) lookup. Total runtime per V-region
is sub-millisecond.

⚠️ This engine is for VH/VL only — VHH must use its own protection rule set.
   Mixing VHH and VH/VL data violates workspace governance.

Usage:
    from core.humanization.contextual_substitution_engine import (
        ContextualSubstitutionEngine
    )

    engine = ContextualSubstitutionEngine()
    result = engine.humanize_fr(
        vh_seq="EVQLVESGGG...",
        vh_germline="IGHV3-23",
    )
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SUITE_ROOT = Path(__file__).resolve().parents[2]

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

DB_9MER_PATH = SUITE_ROOT / "config" / "clinical_842_9mer_db.json"
OAS_9MER_PATH = SUITE_ROOT / "config" / "oas_human_9mer_v1.json.gz"
CC_FR_TABLE_PATH = SUITE_ROOT / "config" / "cc_fr_table_vhvl_v1.json"
GERMLINE_CMC_PATH = SUITE_ROOT / "config" / "germline_cmc_anchors.json"

AMINO_ACIDS = list("ACDEFGHIKLMNPQRSTVWY")

# Layer-2 voting threshold: top-ranked AA needs at least this many supporting
# weighted votes to be statistically credible (otherwise no replacement).
# Votes are weighted: W_CLINICAL_VOTE per clinical-842 window hit,
#                     W_OAS_VOTE per OAS window hit.
MIN_VOTES_LAYER2 = 50

# Layer-2 confidence ratio: default (non-conservative substitutions).
# Conservative substitutions (positive BLOSUM62 score) use a lower adaptive
# ratio — see _blosum_adaptive_ratio().
LAYER2_CONFIDENCE_RATIO = 3.0

# Family-conditioned voting: minimum total votes from the family sub-library
# for the top candidate before we trust the family result.
FAMILY_BACKOFF_THRESHOLD = 15

# OAS-Assist dual-database voting.
#
# Clinical-842 is the primary evidence source. OAS is a binary presence/absence
# human-repertoire support signal, not a count distribution, so OAS must not be
# allowed to pass Layer-2 by itself. Weighted votes are used only to rank/tie-break
# candidates; acceptance uses the raw clinical and OAS support gates below.
#
# Strong clinical gate:
#   clinical_raw(candidate) >= MIN_VOTES_LAYER2
#
# OAS-assisted gate:
#   clinical_raw(candidate) >= OAS_ASSIST_MIN_CLINICAL_VOTES
#   AND candidate OAS-covered windows >= OAS_ASSIST_MIN_OAS_WINDOWS
#   AND candidate OAS-covered windows improves original by >= OAS_ASSIST_MIN_OAS_DELTA
#
# Both gates still require the BLOSUM-adaptive clinical ratio and Layer-4 CMC veto.
W_CLINICAL_VOTE = 10
W_OAS_VOTE = 1
OAS_ASSIST_MIN_CLINICAL_VOTES = 15
OAS_ASSIST_MIN_OAS_WINDOWS = 3
OAS_ASSIST_MIN_OAS_DELTA = 2

# Layer-3 (CC-FR family backoff) disabled — Kabat alignment not implemented.
ENABLE_LAYER3_DEFAULT = False
MIN_N_LAYER3 = 20
MIN_LAYER3_CANDIDATE_FREQ = 0.70
MAX_LAYER3_ORIGINAL_FREQ = 0.02

# CMC charge envelope (per residue change)
MAX_CHARGE_DELTA = 1.5

# ─────────────────────────────────────────────────────────────────────────────
# BLOSUM62 — used only for adaptive confidence ratio scaling.
# Conservative substitutions require less clinical evidence to be accepted.
# ─────────────────────────────────────────────────────────────────────────────

try:
    from Bio.Align import substitution_matrices as _sm
    _BL62_RAW = _sm.load("BLOSUM62")
    def _blosum62(a: str, b: str) -> int:
        try:
            return int(_BL62_RAW[a][b])
        except (KeyError, IndexError):
            return -4
except Exception:
    # Fallback minimal table if Biopython not present or matrix missing.
    # Covers the most common conservative pairs (score > 0 = conservative).
    _BL62_CONSERVATIVE = frozenset({
        ('I','V'),('V','I'),('I','L'),('L','I'),('V','L'),('L','V'),
        ('A','S'),('S','A'),('A','T'),('T','A'),('S','T'),('T','S'),
        ('Q','E'),('E','Q'),('Q','K'),('K','Q'),('R','K'),('K','R'),
        ('N','D'),('D','N'),('N','S'),('S','N'),
        ('Y','F'),('F','Y'),('Y','W'),('W','Y'),
        ('M','L'),('L','M'),('M','I'),('I','M'),('M','V'),('V','M'),
    })
    def _blosum62(a: str, b: str) -> int:  # type: ignore[misc]
        if a == b:
            return 2
        return 1 if (a, b) in _BL62_CONSERVATIVE else -1


def _blosum_adaptive_ratio(original_aa: str, candidate_aa: str) -> float:
    """
    Return the confidence ratio required for Layer-2 to accept a replacement,
    scaled by biochemical conservatism (BLOSUM62 score):

      BLOSUM62 > 0  (conservative)  → ratio 1.5   e.g. I→V, Q→E, S→T
      BLOSUM62 = 0  (neutral)       → ratio 2.0   e.g. A→G
      BLOSUM62 < 0  (non-conserv.)  → ratio 3.0   e.g. S→R (default)

    Rationale: The 842 clinical library is small; conservative substitutions
    are underrepresented simply because variants are not catalogued, not because
    they are clinically wrong. Relaxing the ratio for BLOSUM-positive pairs
    reflects real evolutionary tolerance without guessing.
    """
    score = _blosum62(original_aa, candidate_aa)
    if score > 0:
        return 1.5
    if score == 0:
        return 2.0
    return LAYER2_CONFIDENCE_RATIO   # 3.0 for non-conservative


# ─────────────────────────────────────────────────────────────────────────────
# Protection level tiers
# ─────────────────────────────────────────────────────────────────────────────

class ProtectionLevel(Enum):
    """
    HARD      — Never modify. Structural or disulfide integrity.
    SOFT      — Override only with very strong clinical evidence
                (top_votes >= 100 AND ratio >= 10×). Documented risk.
    ADVISORY  — Engine logs the risk and allows replacement if evidence
                is sufficient (normal Layer-2 thresholds apply, but the
                decision record carries the advisory flag). Used for positions
                where clinical practice commonly does modify (e.g. Q1→E1 in
                VK to prevent N-terminal pyroglutamylation heterogeneity).
    """
    HARD     = "HARD"
    SOFT     = "SOFT"
    ADVISORY = "ADVISORY"

# SOFT override thresholds (stricter than normal Layer-2)
_SOFT_MIN_VOTES  = 100
_SOFT_MIN_RATIO  = 10.0

# ─────────────────────────────────────────────────────────────────────────────
# Protection rules (VH/VL specific) — linear FR positions within each segment.
# ─────────────────────────────────────────────────────────────────────────────

# Charged class definitions for charge flip detection
_POS_CHARGED = frozenset("KRH")
_NEG_CHARGED = frozenset("DE")

# N-glyc motif regex: NxS/T where x != P
_NGLYC_RE = re.compile(r"N[^P][ST]")


# ─────────────────────────────────────────────────────────────────────────────
# Result containers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PositionDecision:
    """Per-position substitution decision with full provenance."""
    position: int             # 0-indexed within concatenated FR1+CDR1+...+FR3
    fr_segment: str           # FR1 / FR2 / FR3
    fr_pos: int               # 0-indexed within FR segment
    original_aa: str
    proposed_aa: str
    decision: str             # KEEP / REPLACED / VETOED / PROTECTED
    layer: str                # layer-1 / layer-2 / layer-3 / layer-4 / no-change
    evidence: Dict            # source data: votes, freq, n_used, etc.


@dataclass
class HumanizationResult:
    """Full output from a contextual humanization run."""
    chain: str                # "VH" or "VK"
    germline: Optional[str]   # canonical field: holds VH or VL germline string
    family: Optional[str]     # IGHVX or IGKVX family prefix
    input_seq: str            # concat: FR1+CDR1+FR2+CDR2+FR3
    output_seq: str
    n_positions_evaluated: int
    n_replacements: int
    n_protected: int
    n_vetoed: int
    n_no_data: int
    decisions: List[PositionDecision] = field(default_factory=list)
    summary_by_layer: Dict[str, int] = field(default_factory=dict)

    @property
    def vh_germline(self) -> Optional[str]:
        """Back-compat alias — use .germline instead."""
        return self.germline


# ─────────────────────────────────────────────────────────────────────────────
# The Engine
# ─────────────────────────────────────────────────────────────────────────────

class ContextualSubstitutionEngine:
    """
    Three-layer FR humanization engine.

    The engine is stateless after init — all data structures are loaded once
    into memory and reused across many antibodies (suitable for batch / API use).
    """

    def __init__(self,
                 db_9mer_path: Path = DB_9MER_PATH,
                 cc_fr_path: Path = CC_FR_TABLE_PATH,
                 enable_layer3: bool = ENABLE_LAYER3_DEFAULT,
                 verbose: bool = False):
        self.verbose = verbose
        self.enable_layer3 = enable_layer3
        self._load_databases(db_9mer_path, cc_fr_path)
        if self.verbose and not self.enable_layer3:
            print("[Engine] Layer-3 (CC-FR family backoff) is DISABLED. "
                  "Pipeline runs Layer-1 + Layer-2 + Layer-4 only.")

    def _load_databases(self, db_9mer_path: Path, cc_fr_path: Path) -> None:
        import gzip as _gzip

        if not db_9mer_path.exists():
            raise FileNotFoundError(
                f"Missing 9-mer DB at {db_9mer_path}. "
                f"Run scripts/build_clinical_9mer_db.py first."
            )
        if not cc_fr_path.exists():
            raise FileNotFoundError(
                f"Missing CC-FR table at {cc_fr_path}. "
                f"Run scripts/build_ccfr_table_vhvl.py first."
            )

        db_9mer_data = json.loads(db_9mer_path.read_text(encoding="utf-8"))

        # VH databases
        self.db_9mer: Dict[str, int] = db_9mer_data["9mers"]
        self.db_9mer_family: Dict[str, Dict[str, int]] = db_9mer_data.get("family_9mers", {})
        self.family_n: Dict[str, int] = db_9mer_data.get("family_n_antibodies", {})

        # VK (IGK kappa) databases — schema v1.3+; empty dicts if absent
        self.db_vk_9mer: Dict[str, int] = db_9mer_data.get("vl_9mers", {})
        self.db_vk_family: Dict[str, Dict[str, int]] = db_9mer_data.get("vl_family_9mers", {})
        self.vk_family_n: Dict[str, int] = db_9mer_data.get("vl_family_n_antibodies", {})

        # OAS supplement — chain-agnostic frozenset (presence/absence)
        # Provides ~5.7M 9-mers from >=10%-prevalence healthy human subjects.
        # Loaded as frozenset for O(1) lookup; contributes W_OAS_VOTE per hit.
        self.db_oas: frozenset = frozenset()
        oas_path = OAS_9MER_PATH
        if oas_path.exists():
            try:
                with _gzip.open(oas_path, "rt", encoding="utf-8") as f:
                    oas_data = json.load(f)
                self.db_oas = frozenset(oas_data.get("9mers", []))
                if self.verbose:
                    print(f"[Engine] OAS supplement   : {len(self.db_oas):,} 9-mers "
                          f"(W_OAS={W_OAS_VOTE}, W_CLINICAL={W_CLINICAL_VOTE})")
            except Exception as exc:
                if self.verbose:
                    print(f"[Engine] OAS supplement WARN: could not load ({exc}). "
                          f"Running without OAS supplement.")
        else:
            if self.verbose:
                print(f"[Engine] OAS supplement   : not found at {oas_path}. "
                      f"Run scripts/build_oas_9mer_supplement.py to enable.")

        cc_fr_data = json.loads(cc_fr_path.read_text(encoding="utf-8"))
        self.cc_fr: Dict = cc_fr_data["vhvl_ccfr"]

        if self.verbose:
            print(f"[Engine] VH global 9-mers : {len(self.db_9mer):,}")
            vh_fam = ", ".join(f"{f}={self.family_n.get(f,0)}"
                               for f in sorted(self.db_9mer_family))
            print(f"[Engine] VH families      : {vh_fam or 'none'}")
            print(f"[Engine] VK global 9-mers : {len(self.db_vk_9mer):,}")
            vk_fam = ", ".join(f"{f}={self.vk_family_n.get(f,0)}"
                               for f in sorted(self.db_vk_family))
            print(f"[Engine] VK families      : {vk_fam or 'none (schema <1.3)'}")
            print(f"[Engine] CC-FR families   : {len(self.cc_fr)}")

    # ─────────────────────────────────────────────────────────────────────
    # Layer 1 — Protection filter
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _is_protected(fr_segment: str, fr_pos: int, aa: str,
                      chain: str = "VH") -> Tuple[Optional[ProtectionLevel], str]:
        """
        Returns (ProtectionLevel_or_None, reason).

        None  → position is free (no protection applies)
        HARD  → never modify under any circumstances
        SOFT  → modifiable only with very strong clinical evidence
                (top_votes >= 100, ratio >= 10x)
        ADVISORY → modifiable under normal Layer-2 thresholds; decision record
                   will carry an advisory flag for downstream review

        Protection tiers:
        ──────────────────────────────────────────────────────────────────
        VH:
          Cys (all FR)          HARD  — canonical disulfide, structural
          Trp in FR1/FR2        HARD  — Kabat 36 beta-sheet anchor / FR2 core

        VK:
          Cys (all FR)          HARD  — canonical disulfide
          Trp (all FR)          HARD  — VL beta-sheet packing anchor
          Tyr/Phe FR2[3,16]    SOFT  — VH/VL hydrophobic interface core
                                        (820/842 conserved; very occasionally
                                         engineered away in clinical antibodies)
          Gln FR1[0]           ADVISORY — pyroglutamylation risk; Q→E is a
                                          known clinical CMC practice to eliminate
                                          N-terminal heterogeneity. Allow if
                                          Layer-2 has normal-strength evidence.
        """
        if aa == "C":
            return ProtectionLevel.HARD, "canonical_cys"

        if chain == "VH":
            if aa == "W" and fr_segment in ("FR1", "FR2"):
                return ProtectionLevel.HARD, "conserved_trp_VH"

        elif chain == "VK":
            # ── Trp: absolute structural anchors ──────────────────────────
            if aa == "W":
                return ProtectionLevel.HARD, f"conserved_trp_VK_{fr_segment}"

            # ── VH/VL hydrophobic interface core — SOFT ───────────────────
            # FR2[3]  = Tyr/Phe (820/842 ≈ 97%) — Kabat 36 equivalent
            # FR2[16] = Tyr/Phe (773/842 ≈ 92%) — Kabat 49 beta-turn cap
            # Demoted from HARD to SOFT: a handful of approved antibodies
            # carry changes here, so very strong 9-mer evidence (≥100 votes,
            # ≥10x ratio) overrides the protection.
            if fr_segment == "FR2" and aa in ("Y", "F") and fr_pos in (3, 16):
                return (ProtectionLevel.SOFT,
                        f"vhvl_interface_hydrophobic_VK_FR2_pos{fr_pos}")

            # ── N-terminal Gln — ADVISORY ─────────────────────────────────
            # Q→E at position 0 of VK FR1 is an established clinical CMC
            # practice (prevents pGlu formation during manufacturing).
            # Demoted from HARD to ADVISORY so Layer-2 can apply this change
            # when clinical evidence supports it (ratio × normal threshold).
            if aa == "Q" and fr_segment == "FR1" and fr_pos == 0:
                return (ProtectionLevel.ADVISORY,
                        "vk_nterminal_gln_pyroglu_risk_advisory")

        return None, ""

    # ─────────────────────────────────────────────────────────────────────
    # Layer 2 — 9-mer context voting
    # ─────────────────────────────────────────────────────────────────────

    def _score_with_db(self,
                       db: Dict[str, int],
                       full_seq: str,
                       target_pos: int,
                       weight: int = 1) -> Dict[str, int]:
        """
        Core scoring loop: for each of 20 AAs, sum votes from all overlapping
        9-mer windows that cover target_pos using the given 9-mer database.

        weight: multiply each database hit by this value before accumulating.
                Default 1 preserves raw counts; use W_CLINICAL_VOTE / W_OAS_VOTE
                when combining clinical-842 and OAS contributions.
        """
        start_idx = max(0, target_pos - 8)
        end_idx   = min(len(full_seq) - 9, target_pos)
        scores: Dict[str, int] = {}
        for aa in AMINO_ACIDS:
            mutated = full_seq[:target_pos] + aa + full_seq[target_pos + 1:]
            total = 0
            for i in range(start_idx, end_idx + 1):
                window = mutated[i:i + 9]
                total += db.get(window, 0) * weight
            scores[aa] = total
        return scores

    def _score_with_oas(self, full_seq: str, target_pos: int) -> Dict[str, int]:
        """
        OAS presence/absence scoring: for each of 20 AAs, count how many
        overlapping 9-mer windows (covering target_pos) are present in the
        OAS frozenset.

        Returns zero scores if db_oas is empty (OAS supplement not loaded).
        """
        if not self.db_oas:
            return {aa: 0 for aa in AMINO_ACIDS}
        start_idx = max(0, target_pos - 8)
        end_idx   = min(len(full_seq) - 9, target_pos)
        scores: Dict[str, int] = {}
        for aa in AMINO_ACIDS:
            mutated = full_seq[:target_pos] + aa + full_seq[target_pos + 1:]
            total = 0
            for i in range(start_idx, end_idx + 1):
                window = mutated[i:i + 9]
                if window in self.db_oas:
                    total += 1
            scores[aa] = total
        return scores

    @staticmethod
    def _merge_scores(s1: Dict[str, int], s2: Dict[str, int]) -> Dict[str, int]:
        """Element-wise sum of two AA-score dicts."""
        return {aa: s1.get(aa, 0) + s2.get(aa, 0) for aa in AMINO_ACIDS}

    @staticmethod
    def _scale_scores(scores: Dict[str, int], weight: int) -> Dict[str, int]:
        """Multiply all AA scores by a fixed weight."""
        return {aa: scores.get(aa, 0) * weight for aa in AMINO_ACIDS}

    def _layer2_vote(self,
                     full_seq: str,
                     target_pos: int,
                     family: str = "",
                     chain: str = "VH") -> Tuple[Optional[str], int, Dict[str, int], str]:
        """
        Vote among 20 AAs at target_pos using overlapping 9-mer windows.

        chain="VH" -> uses VH 9-mer global + family sub-libraries.
        chain="VK" -> uses VK (IGK) 9-mer global + family sub-libraries.

        OAS-Assist voting strategy:
          1. Compute clinical-842 raw scores (family-conditioned → global fallback).
          2. Compute OAS raw scores (chain-agnostic presence/absence).
          3. Rank candidates by weighted score:
                clinical_raw * W_CLINICAL_VOTE + oas_raw * W_OAS_VOTE
             Weighted score is for ranking/tie-breaking only.
          4. Acceptance is handled in humanize_fr using dual gates:
                clinical-strong OR OAS-assisted,
             both with BLOSUM-adaptive clinical ratio and CMC veto.

        Family-conditioned clinical logic:
          - If family sub-library top candidate >= FAMILY_BACKOFF_THRESHOLD
            (raw clinical votes), use family clinical scores as clinical signal.
          - Otherwise use chain-specific global clinical pool.

        Returns (best_aa, top_votes, all_scores, vote_source).
        top_votes and all_scores reflect weighted ranking scores for compatibility.
        Detailed raw clinical/OAS scores are stored in self._last_layer2_vote.
        vote_source indicates the clinical source used ("family:X" or "global_VH/VK").
        """
        if chain == "VK":
            fam_db_map  = self.db_vk_family
            global_db   = self.db_vk_9mer
            global_tag  = "global_VK"
        else:
            fam_db_map  = self.db_9mer_family
            global_db   = self.db_9mer
            global_tag  = "global_VH"

        fam_db = fam_db_map.get(family) if family else None

        # ── Determine clinical source (family vs global) ──────────────────────
        clinical_source = global_tag
        clinical_db = global_db
        if fam_db:
            # Check if family library has strong enough signal (raw votes)
            fam_raw = self._score_with_db(fam_db, full_seq, target_pos, weight=1)
            ranked_fam_raw = sorted(fam_raw.items(), key=lambda x: -x[1])
            if ranked_fam_raw and ranked_fam_raw[0][1] >= FAMILY_BACKOFF_THRESHOLD:
                clinical_db = fam_db
                clinical_source = f"family:{family}"

        # ── Clinical-842 raw scores ──────────────────────────────────────────
        clinical_raw = self._score_with_db(clinical_db, full_seq, target_pos, weight=1)

        # ── OAS supplement scores ─────────────────────────────────────────────
        oas_raw = self._score_with_oas(full_seq, target_pos)

        # ── Weighted totals for ranking only ─────────────────────────────────
        weighted = self._merge_scores(
            self._scale_scores(clinical_raw, W_CLINICAL_VOTE),
            self._scale_scores(oas_raw, W_OAS_VOTE),
        )
        ranked = sorted(weighted.items(), key=lambda x: -x[1])

        self._last_layer2_vote = {
            "clinical_raw_scores": clinical_raw,
            "oas_raw_scores": oas_raw,
            "weighted_scores": weighted,
            "clinical_source": clinical_source,
            "weights": {
                "clinical": W_CLINICAL_VOTE,
                "oas": W_OAS_VOTE,
            },
        }

        if not ranked or ranked[0][1] == 0:
            return None, 0, weighted, clinical_source

        best_aa, top_votes = ranked[0]
        return best_aa, top_votes, weighted, clinical_source

    # ─────────────────────────────────────────────────────────────────────
    # Layer 3 — CC-FR family/position frequency backoff
    # ─────────────────────────────────────────────────────────────────────

    def _layer3_lookup(self,
                       family: str,
                       fr_segment: str,
                       fr_pos: int) -> Optional[Dict]:
        """
        Returns the CC-FR entry for this family/segment/position, or None
        if no clinical data is available.
        """
        fam = self.cc_fr.get(family)
        if fam is None:
            return None
        seg = fam.get(fr_segment, {})
        return seg.get(str(fr_pos))

    # ─────────────────────────────────────────────────────────────────────
    # Layer 4 — CMC veto
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _layer4_cmc_veto(original_seq: str,
                         mutated_seq: str,
                         pos: int,
                         original_aa: str,
                         proposed_aa: str) -> Tuple[bool, str]:
        """
        Returns (vetoed, reason).

        Vetoes (in priority order):

        1. Free Cys introduction
           Proposed AA is C but original is not C → new free cysteine can form
           spurious disulfide bonds, cause aggregation, and create PK/tox liabilities.

        2. Glycine removal (G → any)
           Gly is the only backbone-flexible residue (φ/ψ unconstrained). In FR
           turns (e.g. FR1 Gly-Gly-Gly stretch, FR3 CDR-exit Gly), removal
           over-rigidifies the turn and can collapse CDR conformation. Any
           substitution of an existing G in the framework is forbidden.

        3. Proline removal (P → any)
           Pro locks the backbone at specific φ ≈ -60° through its pyrrolidine
           ring. Conserved FR Pro residues (e.g. FR2 Pro-Gly motif at Kabat 40–41,
           and the FR1/FR3 structural anchors) provide rigid pivots that orient
           CDR loops. Replacing a Pro with any other residue destroys this pivot,
           leading to CDR positional drift.

        4. Proline introduction (any → P)
           Inserting Pro into a non-Pro position disrupts the local secondary
           structure (helix or sheet) because Pro cannot donate an H-bond and
           imposes a rigid backbone kink. In β-strand-rich FR regions this is
           especially dangerous.

        5. N-glycosylation motif creation (NxS/T where x ≠ P)
           N-linked glycosylation in the variable domain can sterically block
           antigen binding, increase heterogeneity during expression, and create
           CDR liability that varies by expression host.

        6. Strong charge flip (K/R/H ↔ D/E)
           Reversing the sign of a charged residue at the FR surface shifts the
           local electrostatic environment by +2 to +3 units, which can:
           (a) disrupt VH/VL interface salt bridges (b) alter pI by ≥0.5 pH
           units (c) create charge patches scored by TAP/PPC metrics.
        """
        # ── 1. Free Cys introduction ─────────────────────────────────────────
        if proposed_aa == "C" and original_aa != "C":
            return True, "introduces_free_cys"

        # ── 2. Glycine removal ───────────────────────────────────────────────
        # Glycine is the backbone flexibility anchor in FR turns. Any replacement
        # is forbidden because:
        #   - We cannot know without a structure whether this G is in a tight turn.
        #   - The 9-mer voting will almost never suggest replacing G (Gly 9-mers
        #     score very high in clinical data precisely because they are conserved).
        #   - If Layer 2 voted for a replacement here anyway (sparse data edge case),
        #     this hard veto prevents backbone damage.
        if original_aa == "G":
            return True, "gly_removal_backbone_anchor"

        # ── 3. Proline removal ───────────────────────────────────────────────
        # Pro locks the backbone torsion angle. Removing it is structurally
        # equivalent to removing a rigid spacer — the downstream loop will drift.
        # This applies even when Layer 2 voted for a change (e.g., because a
        # different antibody in 842 happened to use a non-Pro at an equivalent
        # position — that antibody has a different structural context).
        if original_aa == "P":
            return True, "pro_removal_backbone_lock"

        # ── 4. Proline introduction ──────────────────────────────────────────
        # Inserting Pro in a non-Pro FR position:
        #   - Breaks H-bond donation capacity at that residue.
        #   - Imposes a kink that is incompatible with β-strand or α-helix segments.
        #   - Introduces a cis/trans isomerization risk (slow folding, heterogeneity).
        # Note: Layer 2 will rarely vote for Pro introduction because Pro 9-mers
        # only score high at positions that are ALREADY Pro in the source antibody.
        # This veto exists as a hard backstop for pathological sparse-data cases.
        if proposed_aa == "P" and original_aa != "P":
            return True, "pro_introduction_backbone_disrupt"

        # ── 5. N-glycosylation motif creation ────────────────────────────────
        win_start = max(0, pos - 2)
        win_end = min(len(mutated_seq), pos + 3)
        before = original_seq[win_start:win_end]
        after  = mutated_seq[win_start:win_end]
        if _NGLYC_RE.search(after) and not _NGLYC_RE.search(before):
            return True, "creates_n_glyc_motif"

        # ── 6. Strong charge flip ─────────────────────────────────────────────
        # K/R/H → D/E or D/E → K/R/H:
        # Includes His in positive group because at physiological pH (7.0–7.4)
        # His is ~10–15% protonated and participates in charge-pair networks.
        if (original_aa in _POS_CHARGED and proposed_aa in _NEG_CHARGED) or \
           (original_aa in _NEG_CHARGED and proposed_aa in _POS_CHARGED):
            return True, "strong_charge_flip"

        return False, ""

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _germline_family(germline_str: str) -> str:
        """Extract IGHVX or IGKVX family prefix from a germline string."""
        g = (germline_str or "").strip().upper()
        # e.g. IGHV3-23*01 -> IGHV3;  IGKV1-39*01 -> IGKV1
        import re as _re
        m = _re.match(r"(IG[HKL]V\d+)", g)
        if m:
            return m.group(1)
        if "-" in g:
            return g.split("-")[0]
        if "*" in g:
            return g.split("*")[0]
        return g

    def humanize_fr(self,
                    fr1: str,
                    cdr1: str,
                    fr2: str,
                    cdr2: str,
                    fr3: str,
                    vh_germline: str = "",
                    chain: str = "VH") -> HumanizationResult:
        """
        Run the engine on a complete FR1+CDR1+FR2+CDR2+FR3 layout.

        chain="VH"  — heavy chain (IGHV germline expected)
        chain="VK"  — kappa light chain (IGKV germline expected)

        Pass germline via `vh_germline` for VH, or the VL germline string for VK.
        CDRs are NOT modified; they provide 9-mer context for boundary FRs.

        Raises:
            ValueError: if chain is not "VH" / "VK" (case-insensitive).
            ValueError: if chain="VK" but germline is IGLV (lambda not supported).
        """
        # ── Normalise and validate chain ─────────────────────────────────────
        chain = chain.upper()
        if chain not in ("VH", "VK"):
            raise ValueError(
                f"chain must be 'VH' or 'VK', got {chain!r}. "
                f"IGL (lambda) is not supported by clinical_842_9mer_db — "
                f"a dedicated lambda library is required."
            )

        # Detect IGLV germline passed to a VK run — always a silent error
        germline_upper = (vh_germline or "").upper()
        if chain == "VK" and "IGLV" in germline_upper:
            raise ValueError(
                f"chain='VK' but germline {vh_germline!r} is an IGL (lambda) "
                f"germline. The clinical_842_9mer_db contains only IGKV (kappa) "
                f"sequences. Use chain='VK' only with IGKV germlines, or provide "
                f"a dedicated IGL library."
            )

        family = self._germline_family(vh_germline)

        # Build segment map: position → (segment_name, segment_local_pos)
        seg_map: List[Tuple[str, int]] = []
        concat_parts: List[str] = []
        for name, seq in [("FR1", fr1), ("CDR1", cdr1), ("FR2", fr2),
                          ("CDR2", cdr2), ("FR3", fr3)]:
            for i, aa in enumerate(seq.upper()):
                seg_map.append((name, i))
                concat_parts.append(aa)

        original_concat = "".join(concat_parts)
        mutated_seq = list(original_concat)
        decisions: List[PositionDecision] = []

        for pos, (seg_name, seg_pos) in enumerate(seg_map):
            # CDRs untouched
            if not seg_name.startswith("FR"):
                continue

            original_aa = original_concat[pos]

            # ── Layer 1: Protection (tiered) ─────────────────────────────
            prot_level, reason = self._is_protected(seg_name, seg_pos, original_aa,
                                                    chain=chain)
            if prot_level is ProtectionLevel.HARD:
                decisions.append(PositionDecision(
                    position=pos, fr_segment=seg_name, fr_pos=seg_pos,
                    original_aa=original_aa, proposed_aa=original_aa,
                    decision="PROTECTED", layer="layer-1",
                    evidence={"reason": reason, "protection_level": "HARD"},
                ))
                continue
            # SOFT and ADVISORY are NOT blocked here — they proceed to Layer 2
            # but face different acceptance thresholds below.

            # ── Layer 2: 9-mer voting (use ORIGINAL sequence, not mutated) ──
            best_aa_l2, top_votes, _scores, vote_source = self._layer2_vote(
                original_concat, pos, family=family, chain=chain
            )

            proposed_aa = None
            chosen_layer = None
            evidence: Dict = {}

            if best_aa_l2 and best_aa_l2 != original_aa:
                vote_detail = getattr(self, "_last_layer2_vote", {})
                clinical_scores = vote_detail.get("clinical_raw_scores", {})
                oas_scores = vote_detail.get("oas_raw_scores", {})
                weighted_scores = vote_detail.get("weighted_scores", _scores)

                clinical_top_votes = clinical_scores.get(best_aa_l2, 0)
                clinical_original_votes = clinical_scores.get(original_aa, 0)
                oas_top_windows = oas_scores.get(best_aa_l2, 0)
                oas_original_windows = oas_scores.get(original_aa, 0)
                oas_delta = oas_top_windows - oas_original_windows
                original_votes = weighted_scores.get(original_aa, 0)
                actual_ratio = clinical_top_votes / max(clinical_original_votes, 1)
                weighted_ratio = top_votes / max(original_votes, 1)

                # Determine required ratio: BLOSUM-adaptive for free positions,
                # stricter for SOFT-protected positions.
                if prot_level is ProtectionLevel.SOFT:
                    required_votes = _SOFT_MIN_VOTES
                    required_ratio = _SOFT_MIN_RATIO
                else:
                    # ADVISORY or unprotected: use BLOSUM-adaptive ratio.
                    required_votes = MIN_VOTES_LAYER2
                    required_ratio = _blosum_adaptive_ratio(original_aa, best_aa_l2)

                blosum_score = _blosum62(original_aa, best_aa_l2)

                clinical_strong = (
                    clinical_top_votes >= required_votes
                    and actual_ratio >= required_ratio
                )
                oas_assisted = (
                    prot_level is not ProtectionLevel.SOFT
                    and clinical_top_votes >= OAS_ASSIST_MIN_CLINICAL_VOTES
                    and actual_ratio >= required_ratio
                    and oas_top_windows >= OAS_ASSIST_MIN_OAS_WINDOWS
                    and oas_delta >= OAS_ASSIST_MIN_OAS_DELTA
                )

                if clinical_strong or oas_assisted:
                    proposed_aa  = best_aa_l2
                    chosen_layer = "layer-2"
                    evidence = {
                        "acceptance_mode": (
                            "clinical_strong" if clinical_strong else "oas_assisted"
                        ),
                        "top_aa_votes":    top_votes,
                        "original_aa_votes": original_votes,
                        "weighted_vote_ratio": round(weighted_ratio, 2),
                        "clinical_top_votes": clinical_top_votes,
                        "clinical_original_votes": clinical_original_votes,
                        "clinical_vote_ratio": round(actual_ratio, 2),
                        "oas_top_windows": oas_top_windows,
                        "oas_original_windows": oas_original_windows,
                        "oas_delta_windows": oas_delta,
                        "vote_ratio":      round(actual_ratio, 2),
                        "vote_source":     vote_source,
                        "blosum62_score":  blosum_score,
                        "required_ratio":  required_ratio,
                        "required_votes":  required_votes,
                        "oas_assist_min_clinical_votes": OAS_ASSIST_MIN_CLINICAL_VOTES,
                        "oas_assist_min_oas_windows": OAS_ASSIST_MIN_OAS_WINDOWS,
                        "oas_assist_min_oas_delta": OAS_ASSIST_MIN_OAS_DELTA,
                        "top_5_weighted": sorted(
                            weighted_scores.items(), key=lambda x: -x[1]
                        )[:5],
                        "top_5_clinical_raw": sorted(
                            clinical_scores.items(), key=lambda x: -x[1]
                        )[:5],
                        "top_5_oas_raw": sorted(
                            oas_scores.items(), key=lambda x: -x[1]
                        )[:5],
                    }
                    if prot_level is ProtectionLevel.ADVISORY:
                        evidence["advisory"] = reason
                    elif prot_level is ProtectionLevel.SOFT:
                        evidence["soft_override"] = reason

            # ── Layer 3: CC-FR backoff (gated by enable_layer3 flag) ──────
            if proposed_aa is None and self.enable_layer3:
                cc_entry = self._layer3_lookup(family, seg_name, seg_pos)
                if cc_entry and cc_entry.get("n_used", 0) >= MIN_N_LAYER3 and \
                   cc_entry.get("position_type") == "pure_fr":
                    aa_top5 = cc_entry.get("aa_top5", [])
                    aa_freq = cc_entry.get("aa_freq", {})
                    if aa_top5 and aa_top5[0] != original_aa:
                        candidate = aa_top5[0]
                        cand_freq = aa_freq.get(candidate, 0)
                        orig_freq = aa_freq.get(original_aa, 0)
                        # Strict: candidate must dominate AND original must be
                        # essentially absent in clinical pool at this position
                        if cand_freq >= MIN_LAYER3_CANDIDATE_FREQ and \
                           orig_freq <= MAX_LAYER3_ORIGINAL_FREQ:
                            proposed_aa = candidate
                            chosen_layer = "layer-3"
                            evidence = {
                                "support_level": cc_entry.get("support_level"),
                                "n_used": cc_entry.get("n_used"),
                                "candidate_freq": cand_freq,
                                "original_freq": orig_freq,
                                "position_type": cc_entry.get("position_type"),
                            }

            # ── No replacement chosen ────────────────────────────────────
            if proposed_aa is None or proposed_aa == original_aa:
                keep_ev: Dict = {}
                keep_decision = "KEEP"
                if prot_level is ProtectionLevel.SOFT:
                    keep_decision = "PROTECTED"
                    keep_ev = {"reason": reason, "protection_level": "SOFT",
                               "note": "insufficient_evidence_to_override"}
                elif prot_level is ProtectionLevel.ADVISORY:
                    keep_ev = {"advisory": reason,
                               "note": "evidence_below_threshold"}
                decisions.append(PositionDecision(
                    position=pos, fr_segment=seg_name, fr_pos=seg_pos,
                    original_aa=original_aa, proposed_aa=original_aa,
                    decision=keep_decision, layer="no-change",
                    evidence=keep_ev,
                ))
                continue

            # ── Layer 4: CMC veto ────────────────────────────────────────
            tentative = mutated_seq.copy()
            tentative[pos] = proposed_aa
            vetoed, veto_reason = self._layer4_cmc_veto(
                original_concat, "".join(tentative), pos, original_aa, proposed_aa
            )
            if vetoed:
                decisions.append(PositionDecision(
                    position=pos, fr_segment=seg_name, fr_pos=seg_pos,
                    original_aa=original_aa, proposed_aa=proposed_aa,
                    decision="VETOED", layer="layer-4",
                    evidence={"veto_reason": veto_reason, "from_layer": chosen_layer,
                              **evidence},
                ))
                continue

            # ── Apply replacement ────────────────────────────────────────
            mutated_seq[pos] = proposed_aa
            decisions.append(PositionDecision(
                position=pos, fr_segment=seg_name, fr_pos=seg_pos,
                original_aa=original_aa, proposed_aa=proposed_aa,
                decision="REPLACED", layer=chosen_layer,
                evidence=evidence,
            ))

        # ── Global sanity check — roll back weakest violations ──────────
        # After all per-position decisions, validate the assembled sequence
        # for global properties that individual per-position veto cannot catch
        # (e.g. a combination of two replacements creates a new N-glyc site).
        # Violations are rolled back in ascending evidence-strength order until
        # the sequence is clean.
        mutated_seq = self._global_sanity_check(
            original_concat, mutated_seq, decisions
        )

        # Aggregate stats
        layer_counts: Dict[str, int] = {}
        for d in decisions:
            layer_counts[d.layer] = layer_counts.get(d.layer, 0) + 1

        return HumanizationResult(
            chain=chain,
            germline=vh_germline or None,
            family=family or None,
            input_seq=original_concat,
            output_seq="".join(mutated_seq),
            n_positions_evaluated=len([d for d in decisions
                                       if d.fr_segment.startswith("FR")]),
            n_replacements=len([d for d in decisions if d.decision == "REPLACED"]),
            n_protected=len([d for d in decisions if d.decision == "PROTECTED"]),
            n_vetoed=len([d for d in decisions if d.decision == "VETOED"]),
            n_no_data=len([d for d in decisions if d.layer == "no-change"]),
            decisions=decisions,
            summary_by_layer=layer_counts,
        )

    def _global_sanity_check(self,
                              original_concat: str,
                              mutated_seq: List[str],
                              decisions: List[PositionDecision]) -> List[str]:
        """
        Post-processing global integrity pass.

        Checks the fully assembled mutated sequence for problems that per-position
        Layer-4 veto cannot catch (e.g. two distant replacements together create
        an N-glyc motif, or a new free Cys is introduced by a combination).

        Violations are resolved by rolling back the REPLACED decision with the
        lowest vote evidence (weakest clinical support), iterating until the
        sequence is clean or no more replacements remain.

        Modifies `mutated_seq` in-place and updates decision records.
        Returns the (possibly modified) mutated_seq for convenience.
        """
        def _assembled() -> str:
            return "".join(mutated_seq)

        def _has_new_nglyc(seq: str) -> bool:
            new_sites = set(m.start() for m in _NGLYC_RE.finditer(seq))
            orig_sites = set(m.start() for m in _NGLYC_RE.finditer(original_concat))
            return bool(new_sites - orig_sites)

        def _has_new_free_cys(seq: str) -> bool:
            # A 'C' not present in original at same position is a new free Cys.
            return any(
                seq[i] == 'C' and original_concat[i] != 'C'
                for i in range(min(len(seq), len(original_concat)))
            )

        # Collect replacements sorted by weakest evidence first (lowest top_votes)
        replaced = [d for d in decisions if d.decision == "REPLACED"]
        replaced_by_strength = sorted(
            replaced,
            key=lambda d: d.evidence.get("top_aa_votes", 999999)
        )

        max_rollbacks = len(replaced)
        for _ in range(max_rollbacks):
            seq = _assembled()
            issues = []
            if _has_new_nglyc(seq):
                issues.append("global_nglyc_combo")
            if _has_new_free_cys(seq):
                issues.append("global_free_cys_combo")

            if not issues:
                break  # sequence is clean

            if not replaced_by_strength:
                break  # nothing left to roll back

            # Roll back the weakest replacement
            weakest = replaced_by_strength.pop(0)
            mutated_seq[weakest.position] = weakest.original_aa
            weakest.decision  = "VETOED"
            weakest.layer     = "layer-4-global"
            weakest.proposed_aa = weakest.original_aa
            weakest.evidence["veto_reason"] = f"global_sanity: {', '.join(issues)}"

        return mutated_seq

    def to_dict(self, result: HumanizationResult) -> Dict:
        """Convert HumanizationResult to JSON-serializable dict."""
        return {
            "chain": result.chain,
            "germline": result.germline,
            "vh_germline": result.germline,   # back-compat alias
            "family": result.family,
            "input_seq": result.input_seq,
            "output_seq": result.output_seq,
            "n_positions_evaluated": result.n_positions_evaluated,
            "n_replacements": result.n_replacements,
            "n_protected": result.n_protected,
            "n_vetoed": result.n_vetoed,
            "n_no_data": result.n_no_data,
            "summary_by_layer": result.summary_by_layer,
            "decisions": [asdict(d) for d in result.decisions],
        }
