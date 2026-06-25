"""
core/vaccine_design/multi_epitope_assembler.py
──────────────────────────────────────────────
Multi-epitope mRNA vaccine construct designer.

Pipeline:
  1. Epitope collection (MHC-I + MHC-II)
  2. Spacer/linker insertion (AAY for MHC-I, GPGPG for MHC-II)
  3. Junctional neoepitope check (prevent new MHC binders at junctions)
  4. Ordering optimization (minimize junctional epitopes)
  5. Signal peptide + MITD fusion (enhance MHC-I presentation)
  6. Codon optimization + mRNA folding (via CodonOptimizer)

Usage:
    asm = MultiEpitopeAssembler()
    construct = asm.assemble(
        mhc1_epitopes=["GILGFVFTL", "NLVPMVATV"],
        mhc2_epitopes=["PKYVKQNTLKLAT"],
    )
"""
from __future__ import annotations

import logging
import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

__version__ = "1.0.0"

logger = logging.getLogger(__name__)

# ── signal sequences & fusion domains ────────────────────────────────────────

SIGNAL_PEPTIDES = {
    "tPA":    "MDAMKRGLCCVLLLCGAVFVSPS",  # tissue plasminogen activator
    "IgK":    "METDTLLLWVLLLWVPGSTGD",    # Ig kappa
    "CD8a":   "MALPVTALLLPLALLLHAARP",     # CD8 alpha
}

MITD_SEQUENCE = (
    "IVGIVAGLAVLAVVVIGAVVATVMCRRKSSGGKGGSYSQAASSDSAQGSDVSL"
    "TACKV"
)

# ── spacer / linker library ──────────────────────────────────────────────────

SPACERS = {
    "MHC-I":    "AAY",        # proteasomal cleavage promoting
    "MHC-II":   "GPGPG",      # flexible linker, prevents MHC-I processing
    "flexible": "GGGGS",      # generic flexible linker
    "rigid":    "EAAAK",      # alpha-helical rigid spacer
    "PADRE":    "AKFVAAWTLKAAA",  # Pan-DR epitope (universal CD4 help)
}


@dataclass
class EpitopeEntry:
    sequence: str
    mhc_class: str       # "I" or "II"
    allele: str = ""
    source: str = ""     # gene/protein of origin
    affinity_nM: float = 0.0


@dataclass
class JunctionCheck:
    left_epitope: str
    right_epitope: str
    spacer: str
    junction_seq: str    # 5aa_left + spacer + 5aa_right
    new_binders: int     # number of new MHC binders at junction
    is_clean: bool


@dataclass
class VaccineConstruct:
    name: str
    full_protein: str           # signal + epitopes + spacers + MITD
    epitope_map: List[Dict]     # position mapping of each epitope
    signal_peptide: str
    mitd_fused: bool
    spacer_type_mhc1: str
    spacer_type_mhc2: str
    total_epitopes: int
    mhc1_count: int
    mhc2_count: int
    length_aa: int
    junctional_binders: int     # total junctional neoepitopes found
    padre_included: bool


class MultiEpitopeAssembler:
    """Design multi-epitope vaccine constructs — local, CPU-only."""

    def __init__(
        self,
        signal: str = "tPA",
        add_mitd: bool = True,
        add_padre: bool = True,
        mhc1_spacer: str = "AAY",
        mhc2_spacer: str = "GPGPG",
        check_junctions: bool = True,
        allele_for_junction_check: str = "HLA-A*02:01",
    ):
        self.signal = SIGNAL_PEPTIDES.get(signal, signal)
        self.signal_name = signal
        self.add_mitd = add_mitd
        self.add_padre = add_padre
        self.mhc1_spacer = mhc1_spacer
        self.mhc2_spacer = mhc2_spacer
        self.check_junctions = check_junctions
        self.junction_allele = allele_for_junction_check
        self._predictor = None

    @property
    def predictor(self):
        if self._predictor is None and self.check_junctions:
            from mhcflurry import Class1PresentationPredictor
            self._predictor = Class1PresentationPredictor.load()
        return self._predictor

    # ── junctional neoepitope check ──────────────────────────────────────

    def _check_junction(
        self,
        left_epitope: str,
        right_epitope: str,
        spacer: str,
    ) -> JunctionCheck:
        """Check if the junction between two epitopes creates new MHC binders."""
        flank = 5
        left_tail = left_epitope[-flank:] if len(left_epitope) >= flank else left_epitope
        right_head = right_epitope[:flank] if len(right_epitope) >= flank else right_epitope
        junction_seq = left_tail + spacer + right_head

        new_binders = 0
        if self.predictor and len(junction_seq) >= 8:
            peptides = []
            for plen in [8, 9, 10]:
                for i in range(len(junction_seq) - plen + 1):
                    pep = junction_seq[i:i + plen]
                    if any(c not in "ACDEFGHIKLMNPQRSTVWY" for c in pep):
                        continue
                    peptides.append(pep)

            if peptides:
                df = self.predictor.predict(
                    peptides=peptides,
                    alleles=[self.junction_allele],
                    verbose=0,
                )
                new_binders = int((df["presentation_percentile"] < 2.0).sum())

        return JunctionCheck(
            left_epitope=left_epitope,
            right_epitope=right_epitope,
            spacer=spacer,
            junction_seq=junction_seq,
            new_binders=new_binders,
            is_clean=(new_binders == 0),
        )

    # ── ordering optimization ────────────────────────────────────────────

    def _optimize_order(
        self,
        epitopes: List[EpitopeEntry],
    ) -> List[EpitopeEntry]:
        """Greedy ordering to minimize junctional neoepitopes.

        For small N (≤8), try all permutations. For larger N, use greedy.
        """
        if not self.check_junctions or len(epitopes) <= 1:
            return epitopes

        if len(epitopes) <= 8:
            return self._brute_force_order(epitopes)
        return self._greedy_order(epitopes)

    def _brute_force_order(self, epitopes: List[EpitopeEntry]) -> List[EpitopeEntry]:
        best_order = epitopes
        best_score = 9999

        for perm in itertools.permutations(epitopes):
            score = 0
            for i in range(len(perm) - 1):
                spacer = self.mhc1_spacer if perm[i].mhc_class == "I" else self.mhc2_spacer
                jc = self._check_junction(perm[i].sequence, perm[i+1].sequence, spacer)
                score += jc.new_binders
            if score < best_score:
                best_score = score
                best_order = list(perm)
            if score == 0:
                break

        return best_order

    def _greedy_order(self, epitopes: List[EpitopeEntry]) -> List[EpitopeEntry]:
        remaining = list(epitopes)
        ordered = [remaining.pop(0)]

        while remaining:
            best_next = None
            best_score = 9999
            for candidate in remaining:
                spacer = self.mhc1_spacer if ordered[-1].mhc_class == "I" else self.mhc2_spacer
                jc = self._check_junction(ordered[-1].sequence, candidate.sequence, spacer)
                if jc.new_binders < best_score:
                    best_score = jc.new_binders
                    best_next = candidate
            remaining.remove(best_next)
            ordered.append(best_next)

        return ordered

    # ── main assembly ────────────────────────────────────────────────────

    def assemble(
        self,
        mhc1_epitopes: Optional[List[str]] = None,
        mhc2_epitopes: Optional[List[str]] = None,
        epitope_entries: Optional[List[EpitopeEntry]] = None,
        construct_name: str = "InSynBio_mRNA_Vaccine_v1",
    ) -> VaccineConstruct:
        """Assemble a multi-epitope vaccine construct.

        Args:
            mhc1_epitopes: List of MHC-I epitope sequences (8-11 aa)
            mhc2_epitopes: List of MHC-II epitope sequences (13-25 aa)
            epitope_entries: Pre-built EpitopeEntry list (overrides above)
            construct_name: Name for this construct
        """
        entries: List[EpitopeEntry] = []
        if epitope_entries:
            entries = epitope_entries
        else:
            for pep in (mhc1_epitopes or []):
                entries.append(EpitopeEntry(sequence=pep, mhc_class="I"))
            for pep in (mhc2_epitopes or []):
                entries.append(EpitopeEntry(sequence=pep, mhc_class="II"))

        if not entries:
            raise ValueError("No epitopes provided")

        if self.add_padre:
            entries.append(EpitopeEntry(
                sequence=SPACERS["PADRE"],
                mhc_class="II",
                source="PADRE_universal_Th",
            ))

        ordered = self._optimize_order(entries)

        parts = [self.signal]
        epitope_map = []
        total_junctional = 0
        pos = len(self.signal)

        for i, entry in enumerate(ordered):
            if i > 0:
                spacer = self.mhc1_spacer if entry.mhc_class == "I" else self.mhc2_spacer
                parts.append(spacer)

                jc = self._check_junction(
                    ordered[i-1].sequence, entry.sequence, spacer
                ) if self.check_junctions else None

                if jc:
                    total_junctional += jc.new_binders
                pos += len(spacer if i > 0 else "")

            epitope_map.append({
                "index": i,
                "sequence": entry.sequence,
                "mhc_class": entry.mhc_class,
                "start_aa": pos + 1,
                "end_aa": pos + len(entry.sequence),
                "source": entry.source,
            })
            parts.append(entry.sequence)
            pos += len(entry.sequence)

        if self.add_mitd:
            parts.append(SPACERS["flexible"])
            parts.append(MITD_SEQUENCE)

        full_protein = "".join(parts)
        mhc1_count = sum(1 for e in ordered if e.mhc_class == "I")
        mhc2_count = sum(1 for e in ordered if e.mhc_class == "II")

        return VaccineConstruct(
            name=construct_name,
            full_protein=full_protein,
            epitope_map=epitope_map,
            signal_peptide=self.signal_name,
            mitd_fused=self.add_mitd,
            spacer_type_mhc1=self.mhc1_spacer,
            spacer_type_mhc2=self.mhc2_spacer,
            total_epitopes=len(ordered),
            mhc1_count=mhc1_count,
            mhc2_count=mhc2_count,
            length_aa=len(full_protein),
            junctional_binders=total_junctional,
            padre_included=self.add_padre,
        )

    # ── convenience: full mRNA pipeline ──────────────────────────────────

    def assemble_and_optimize(
        self,
        mhc1_epitopes: Optional[List[str]] = None,
        mhc2_epitopes: Optional[List[str]] = None,
        construct_name: str = "InSynBio_mRNA_Vaccine_v1",
    ) -> Dict:
        """Assemble construct + codon-optimize → ready-to-synthesize mRNA."""
        from .codon_optimizer import CodonOptimizer

        construct = self.assemble(
            mhc1_epitopes=mhc1_epitopes,
            mhc2_epitopes=mhc2_epitopes,
            construct_name=construct_name,
        )

        optimizer = CodonOptimizer()
        opt_result = optimizer.optimize(construct.full_protein)

        from dataclasses import asdict
        return {
            "construct": asdict(construct),
            "codon_optimization": asdict(opt_result),
        }
