"""
fast_clash_check.py — Fast Interface Steric Clash Detection
============================================================
Answers the question: "Does the redesigned CDR sidechain physically fit
against the antigen, or does it collide with the antigen surface?"

Two-level approach:
  Level 0 (~0 s, no structure needed):
    Compare amino-acid volumes at known interface positions.
    A mutation to a significantly larger residue at a contact site is
    immediately suspicious. Used as a pre-filter before Level 1.

  Level 1 (~5 s, uses EvoEF2):
    EvoEF2 BuildMutant repacks the new sidechains IN THE CONTEXT OF THE
    ANTIGEN (whole complex), then we measure vdW overlap between the
    antibody CDR region and the antigen.
    This is more accurate than ImmuneBuilder (which repacks in vacuum)
    because the antigen atoms act as steric constraints during packing.

Why not ImmuneBuilder?
  ImmuneBuilder predicts the antibody MONOMER structure; the antigen is
  absent. Any sidechain orientation produced this way is unconstrained by
  the interface. Rigid superposition of such a structure back into the
  complex routinely produces false-positive clashes or misses real ones.
  EvoEF2 BuildMutant + this module costs < 5s and is physically more
  correct for fixed-backbone (single CDR) redesign.

Outputs per sequence
--------------------
  clash_count      : number of heavy-atom pairs with vdW overlap > 0.4 Å
  clash_severity   : largest overlap found (Å); 0.0 = no clash
  epitope_overlap  : fraction of WT epitope residues still within 5 Å of CDR
  n_contacts       : total VHH–antigen heavy-atom contacts at 5 Å
  volume_score     : Level-0 sum of volume deltas at interface positions (Ų)
  passed           : True if clash_count <= clash_count_max AND
                     epitope_overlap >= epitope_overlap_min
  flags            : human-readable reasons for failure

Usage
-----
  # Build checker once per project:
  checker = FastClashChecker(
      wt_complex_pdb     = "complex_repaired.pdb",
      ab_chain           = "A",
      ag_chain           = "B",
      cdr_pdb_residues   = [52,53,54,55,56,57,58,59,62,63,64,65,66,67,68,69,70],
      evoef2_exe         = "tools/EvoEF2_src/EvoEF2.exe",
  )

  # For each candidate sequence (given mutations as dicts):
  mutations = [{"chain":"A","resi":57,"wt":"Y","mut":"F"},
               {"chain":"A","resi":58,"wt":"P","mut":"A"}]
  result = checker.check(seq_id="denovo_0042", mutations=mutations, level=1)
  print(result.passed, result.clash_count, result.epitope_overlap)

  # Batch:
  results = checker.check_batch(candidate_mutations_dict, level=1)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── Amino-acid volumes (Ų, from Chothia 1975, rounded) ───────────────────────
# Used for Level-0 volume comparison at interface positions.
AA_VOLUME: dict[str, float] = {
    "G":  60.1, "A":  88.6, "S":  89.0, "P": 112.7, "V": 140.0,
    "T": 116.1, "C": 108.5, "I": 166.7, "L": 166.7, "N": 114.1,
    "D": 111.1, "Q": 143.8, "E": 138.4, "M": 162.9, "H": 153.2,
    "K": 168.6, "F": 189.9, "R": 173.4, "Y": 193.6, "W": 227.8,
}

# ── Simplified van der Waals radii for heavy atoms (Å) ───────────────────────
VDW_RADII: dict[str, float] = {
    "C": 1.70, "N": 1.55, "O": 1.52, "S": 1.80,
    "P": 1.80, "F": 1.47, "CL": 1.75, "BR": 1.85,
}
_VDW_DEFAULT = 1.60

# ── Contact / clash parameters ────────────────────────────────────────────────
CONTACT_CUTOFF_A   = 5.0   # Å for epitope/contact detection
CLASH_OVERLAP_MIN  = 0.4   # Å; pairs closer than (Ri+Rj - this) are clashes
VOLUME_DELTA_WARN  = 40.0  # Ų; per-site volume increase that raises a warning
VOLUME_DELTA_FAIL  = 80.0  # Ų; per-site volume increase that is a hard flag


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ClashResult:
    seq_id:           str
    level:            int            # 0 = volume-only, 1 = EvoEF2+atomic
    clash_count:      int            # vdW-overlap pairs (Level 1 only; 0 at L0)
    clash_severity:   float          # largest overlap in Å (0.0 if none)
    epitope_overlap:  float          # fraction of WT epitope still contacted
    n_contacts:       int            # total CDR–Ag heavy-atom contacts (5 Å)
    volume_score:     float          # sum of per-site volume deltas (Ų)
    passed:           bool
    flags:            list[str] = field(default_factory=list)
    metrics:          dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq_id":          self.seq_id,
            "level":           self.level,
            "clash_count":     self.clash_count,
            "clash_severity":  round(self.clash_severity, 3),
            "epitope_overlap": round(self.epitope_overlap, 3),
            "n_contacts":      self.n_contacts,
            "volume_score":    round(self.volume_score, 1),
            "passed":          self.passed,
            "flags":           self.flags,
            "metrics":         self.metrics,
        }


# ── Main class ────────────────────────────────────────────────────────────────

class FastClashChecker:
    """
    Fast steric clash and epitope-overlap checker for fixed-backbone CDR redesign.

    Parameters
    ----------
    wt_complex_pdb : str or Path
        WT antibody–antigen complex PDB (heavy atoms only recommended).
    ab_chain : str
        Antibody chain ID (e.g. "A").
    ag_chain : str
        Antigen chain ID (e.g. "B").
    cdr_pdb_residues : list[int]
        PDB residue numbers of the redesigned CDR (used to scope clash detection
        to the interface region only, for speed).
    evoef2_exe : str or Path or None
        Path to EvoEF2 executable.  If None, Level-1 is disabled.
    clash_count_max : int
        Maximum allowed steric clashes before a sequence fails. Default 0.
    epitope_overlap_min : float
        Minimum fraction of WT epitope residues that must still be contacted.
        Default 0.70 (70%).
    volume_flag_per_site : float
        Per-site volume increase (Ų) that raises a Level-0 flag. Default 80.
    """

    def __init__(
        self,
        wt_complex_pdb:       str | Path,
        ab_chain:             str = "A",
        ag_chain:             str = "B",
        cdr_pdb_residues:     list[int] | None = None,
        evoef2_exe:           str | Path | None = None,
        clash_count_max:      int   = 0,
        epitope_overlap_min:  float = 0.70,
        volume_flag_per_site: float = VOLUME_DELTA_FAIL,
    ):
        self.wt_pdb          = Path(wt_complex_pdb)
        self.ab_chain        = ab_chain
        self.ag_chain        = ag_chain
        self.cdr_pdb_residues = set(cdr_pdb_residues or [])
        self.evoef2_exe      = str(evoef2_exe) if evoef2_exe else None
        self.clash_count_max = clash_count_max
        self.epi_min         = epitope_overlap_min
        self.vol_fail        = volume_flag_per_site

        # Pre-compute WT epitope residue set + antigen NeighborSearch
        self._wt_epitope, self._ag_ns, self._ag_atoms = \
            self._build_wt_interface()

    # ── Pre-computation ───────────────────────────────────────────────────

    def _build_wt_interface(self):
        """Compute WT epitope set and build NeighborSearch on antigen atoms."""
        from Bio.PDB import PDBParser, NeighborSearch

        parser = PDBParser(QUIET=True)
        s = parser.get_structure("wt", str(self.wt_pdb))
        model = s[0]

        # Antigen heavy atoms (for fast NeighborSearch)
        ag_atoms = [a for a in model[self.ag_chain].get_atoms()
                    if a.element != "H"]
        ns = NeighborSearch(ag_atoms)

        # WT epitope: antigen residues within 5 Å of any CDR heavy atom
        cdr_atoms = [
            a for a in model[self.ab_chain].get_atoms()
            if a.element != "H"
            and a.get_parent().get_id()[1] in self.cdr_pdb_residues
        ]
        wt_epitope: set[int] = set()
        for atom in cdr_atoms:
            for nearby in ns.search(atom.coord, CONTACT_CUTOFF_A, "A"):
                wt_epitope.add(nearby.get_parent().get_id()[1])

        return wt_epitope, ns, ag_atoms

    # ── Level 0: Volume comparison ────────────────────────────────────────

    def _level0_volume(self, mutations: list[dict]) -> tuple[float, list[str]]:
        """
        For each mutation at a CDR position, compute the volume difference
        between the new and old amino acid.

        Returns (total_volume_delta, flags).
        """
        flags: list[str] = []
        total_delta = 0.0

        for m in mutations:
            if m.get("chain") != self.ab_chain:
                continue
            resi = m.get("resi")
            if resi not in self.cdr_pdb_residues:
                continue
            wt_aa  = m.get("wt", "?")
            mut_aa = m.get("mut", "?")
            delta  = AA_VOLUME.get(mut_aa, 130.0) - AA_VOLUME.get(wt_aa, 130.0)
            total_delta += delta

            if delta >= self.vol_fail:
                flags.append(
                    f"VOL_LARGE@res{resi}({wt_aa}->{mut_aa},"
                    f"+{delta:.0f}A3)"
                )
            elif delta >= VOLUME_DELTA_WARN:
                flags.append(
                    f"VOL_WARN@res{resi}({wt_aa}->{mut_aa},"
                    f"+{delta:.0f}A3)"
                )

        return total_delta, flags

    # ── Level 1: EvoEF2 + atomic clash ───────────────────────────────────

    def _build_mutant_noH(self, mutations: list[dict], work_dir: str) -> str | None:
        """
        Write a H-free copy of WT complex, run EvoEF2 BuildMutant,
        return path to mutant PDB or None on failure.
        """
        from Bio.PDB import PDBParser, PDBIO, Select

        class NoHSelect(Select):
            def accept_atom(self, atom):
                return atom.element != "H"

        # Write H-free PDB
        parser = PDBParser(QUIET=True)
        s = parser.get_structure("wt", str(self.wt_pdb))
        noH_path = os.path.join(work_dir, "complex_noH.pdb")
        io = PDBIO()
        io.set_structure(s)
        io.save(noH_path, NoHSelect())

        if not mutations:
            return noH_path

        # Write EvoEF2 mutation file: WTaaChainResnumMutaa;
        mut_str = ",".join(
            f"{m['wt']}{m['chain']}{m['resi']}{m['mut']}"
            for m in mutations
            if m.get("chain") == self.ab_chain
        ) + ";"
        if mut_str == ";":
            return noH_path

        with open(os.path.join(work_dir, "individual_list.txt"), "w") as f:
            f.write(mut_str + "\n")

        result = subprocess.run(
            [self.evoef2_exe, "--command=BuildMutant",
             "--pdb=complex_noH.pdb",
             "--mutant_file=individual_list.txt"],
            capture_output=True, text=True, cwd=work_dir, timeout=120,
        )
        mutant_path = os.path.join(work_dir, "complex_noH_Model_0001.pdb")
        return mutant_path if os.path.exists(mutant_path) else None

    def _count_clashes_and_contacts(
        self,
        pdb_path: str,
        scope_residues: set[int] | None = None,
    ) -> dict[str, Any]:
        """
        Load a complex PDB and compute:
          - clash_count : heavy-atom pairs with vdW overlap > CLASH_OVERLAP_MIN
          - clash_severity : max overlap found
          - n_contacts : CDR–antigen contacts at CONTACT_CUTOFF_A
          - epitope_overlap : fraction of WT epitope still contacted
        """
        from Bio.PDB import PDBParser, NeighborSearch

        parser = PDBParser(QUIET=True)
        try:
            s = parser.get_structure("m", pdb_path)
        except Exception as exc:
            return {"error": str(exc), "clash_count": 999,
                    "clash_severity": 9.9, "n_contacts": 0,
                    "epitope_overlap": 0.0}

        model = s[0]
        scope = scope_residues or self.cdr_pdb_residues

        # CDR heavy atoms in mutant
        try:
            cdr_atoms = [
                a for a in model[self.ab_chain].get_atoms()
                if a.element != "H"
                and a.get_parent().get_id()[1] in scope
            ]
        except KeyError:
            return {"error": f"chain {self.ab_chain} not found",
                    "clash_count": 999, "clash_severity": 9.9,
                    "n_contacts": 0, "epitope_overlap": 0.0}

        # Antigen heavy atoms (build fresh NeighborSearch from mutant PDB)
        try:
            ag_atoms_mut = [a for a in model[self.ag_chain].get_atoms()
                            if a.element != "H"]
        except KeyError:
            return {"error": f"chain {self.ag_chain} not found",
                    "clash_count": 999, "clash_severity": 9.9,
                    "n_contacts": 0, "epitope_overlap": 0.0}

        ns = NeighborSearch(ag_atoms_mut)

        clash_count  = 0
        max_overlap  = 0.0
        contacts_ag: set[int] = set()

        for ab_atom in cdr_atoms:
            ri = VDW_RADII.get(ab_atom.element, _VDW_DEFAULT)
            # Search within sum of max VDW radii (2.0 Å) + contact cutoff
            nearby = ns.search(ab_atom.coord, CONTACT_CUTOFF_A, "A")
            for ag_atom in nearby:
                dist = float(ab_atom - ag_atom)
                rj   = VDW_RADII.get(ag_atom.element, _VDW_DEFAULT)

                # Contact detection (5 Å)
                if dist <= CONTACT_CUTOFF_A:
                    contacts_ag.add(ag_atom.get_parent().get_id()[1])

                # Clash detection: vdW overlap
                overlap = (ri + rj) - dist
                if overlap > CLASH_OVERLAP_MIN:
                    clash_count += 1
                    if overlap > max_overlap:
                        max_overlap = overlap

        epitope_overlap = (
            len(contacts_ag & self._wt_epitope) / len(self._wt_epitope)
            if self._wt_epitope else 0.0
        )

        return {
            "clash_count":     clash_count,
            "clash_severity":  round(max_overlap, 3),
            "n_contacts":      len(contacts_ag),
            "epitope_overlap": round(epitope_overlap, 3),
        }

    # ── Public API ────────────────────────────────────────────────────────

    def check(
        self,
        seq_id:    str,
        mutations: list[dict],
        level:     int = 1,
    ) -> ClashResult:
        """
        Run clash check for a single candidate.

        Parameters
        ----------
        seq_id : str
            Identifier (for logging).
        mutations : list[dict]
            Each dict: {"chain": "A", "resi": 57, "wt": "Y", "mut": "F"}
        level : int
            0 = volume check only (instant, no EvoEF2)
            1 = EvoEF2 BuildMutant + atomic clash (requires evoef2_exe)

        Returns
        -------
        ClashResult
        """
        vol_delta, vol_flags = self._level0_volume(mutations)
        flags = list(vol_flags)

        # Level 0 only
        if level == 0 or self.evoef2_exe is None:
            vol_fail_flags = [f for f in flags if f.startswith("VOL_LARGE")]
            passed = len(vol_fail_flags) == 0
            return ClashResult(
                seq_id        = seq_id,
                level         = 0,
                clash_count   = 0,
                clash_severity= 0.0,
                epitope_overlap= 0.0,
                n_contacts    = 0,
                volume_score  = vol_delta,
                passed        = passed,
                flags         = flags,
            )

        # Level 1: EvoEF2 + atomic
        with tempfile.TemporaryDirectory() as tmp:
            mutant_pdb = self._build_mutant_noH(mutations, tmp)

            if mutant_pdb is None:
                flags.append("EVOEF2_BUILD_FAILED")
                return ClashResult(
                    seq_id=seq_id, level=1, clash_count=999,
                    clash_severity=9.9, epitope_overlap=0.0,
                    n_contacts=0, volume_score=vol_delta,
                    passed=False, flags=flags,
                )

            metrics = self._count_clashes_and_contacts(mutant_pdb)

        if "error" in metrics:
            flags.append(f"PARSE_ERROR:{metrics['error']}")
            return ClashResult(
                seq_id=seq_id, level=1, clash_count=999,
                clash_severity=9.9, epitope_overlap=0.0,
                n_contacts=0, volume_score=vol_delta,
                passed=False, flags=flags,
            )

        clash_count    = metrics["clash_count"]
        clash_severity = metrics["clash_severity"]
        epi_overlap    = metrics["epitope_overlap"]
        n_contacts     = metrics["n_contacts"]

        if clash_count > self.clash_count_max:
            flags.append(
                f"CLASH:{clash_count}_pairs_max_overlap_{clash_severity:.2f}A"
            )
        if epi_overlap < self.epi_min:
            flags.append(
                f"EPITOPE_LOST:{epi_overlap:.2f}<{self.epi_min:.2f}"
            )

        passed = (clash_count <= self.clash_count_max
                  and epi_overlap >= self.epi_min
                  and len([f for f in flags if f.startswith("VOL_LARGE")]) == 0)

        return ClashResult(
            seq_id        = seq_id,
            level         = 1,
            clash_count   = clash_count,
            clash_severity= clash_severity,
            epitope_overlap= epi_overlap,
            n_contacts    = n_contacts,
            volume_score  = vol_delta,
            passed        = passed,
            flags         = flags,
            metrics       = metrics,
        )

    def check_batch(
        self,
        candidates: dict[str, list[dict]],
        level:      int = 1,
        verbose:    bool = True,
    ) -> dict[str, ClashResult]:
        """
        Check a batch of candidates.

        Parameters
        ----------
        candidates : dict {seq_id: mutations_list}
        level : int  0 or 1
        verbose : bool  print per-sequence summary

        Returns
        -------
        dict {seq_id: ClashResult}
        """
        results: dict[str, ClashResult] = {}
        n_pass = n_fail = 0

        for seq_id, mutations in candidates.items():
            r = self.check(seq_id, mutations, level=level)
            results[seq_id] = r
            if r.passed:
                n_pass += 1
            else:
                n_fail += 1
            if verbose:
                status = "PASS" if r.passed else "FAIL"
                if r.level == 1:
                    print(
                        f"  [{status}] {seq_id:<40} "
                        f"clash={r.clash_count} "
                        f"epi={r.epitope_overlap:.2f} "
                        f"vol={r.volume_score:+.0f} "
                        + (f"| {r.flags[0]}" if r.flags else "")
                    )
                else:
                    print(
                        f"  [{status}] {seq_id:<40} "
                        f"vol={r.volume_score:+.0f} "
                        + (f"| {r.flags[0]}" if r.flags else "")
                    )

        if verbose:
            print(
                f"\n  T1.5 Clash Gate: {n_pass} PASS | {n_fail} FAIL "
                f"(out of {len(candidates)}, level={level})"
            )
        return results


# ── Factory: build from mask_strategy.json ────────────────────────────────────

def from_mask_json(
    mask_json_path: str | Path,
    evoef2_exe:     str | Path | None = None,
    clash_count_max: int = 0,
    epitope_overlap_min: float = 0.70,
) -> FastClashChecker:
    """
    Convenience factory: build a FastClashChecker from a project's mask_strategy.json.

    The mask must contain:
      - pdb_file : absolute path to the WT complex PDB
      - vhh_chain / antigen_chain : chain IDs
      - cdr_regions.{CDR}.pdb_resnums : PDB residue numbers for designed CDRs

    Parameters
    ----------
    mask_json_path : path to mask_strategy.json
    evoef2_exe : optional path to EvoEF2 executable (enables Level 1)
    """
    import json
    mask = json.loads(Path(mask_json_path).read_text(encoding="utf-8"))

    pdb_file  = mask["pdb_file"]
    ab_chain  = mask.get("vhh_chain", "A")
    ag_chain  = mask.get("antigen_chain", "B")

    # Collect PDB residue numbers for all redesigned CDRs
    redesign = set(mask.get("design_mask", {}).get("redesign_cdrs", []))
    cdr_pdb_residues: list[int] = []
    for cdr_name in redesign:
        info = mask.get("cdr_regions", {}).get(cdr_name, {})
        cdr_pdb_residues.extend(info.get("pdb_resnums", []))

    # Auto-detect EvoEF2 if not provided
    if evoef2_exe is None:
        suite_root = Path(mask_json_path).resolve().parents[3]
        candidate  = suite_root / "tools" / "EvoEF2_src" / "EvoEF2.exe"
        if candidate.exists():
            evoef2_exe = str(candidate)

    return FastClashChecker(
        wt_complex_pdb      = pdb_file,
        ab_chain            = ab_chain,
        ag_chain            = ag_chain,
        cdr_pdb_residues    = cdr_pdb_residues,
        evoef2_exe          = evoef2_exe,
        clash_count_max     = clash_count_max,
        epitope_overlap_min = epitope_overlap_min,
    )


# ── Mutation builder helpers ───────────────────────────────────────────────────

def mutations_from_sequences(
    wt_seq:          str,
    cand_seq:        str,
    cdr_linear:      tuple[int, int],
    cdr_pdb_resnums: list[int],
    chain:           str = "A",
) -> list[dict]:
    """
    Build EvoEF2-compatible mutation list by comparing WT and candidate sequences
    within the CDR range.

    Parameters
    ----------
    wt_seq : full WT amino-acid sequence (0-indexed)
    cand_seq : full candidate sequence (same length)
    cdr_linear : (start, end_inclusive) 0-indexed linear positions of CDR
    cdr_pdb_resnums : corresponding PDB residue numbers (must be same length as CDR)
    chain : PDB chain ID

    Returns
    -------
    list of {"chain", "resi", "wt", "mut"} dicts for changed positions only
    """
    cdr_start, cdr_end = cdr_linear
    cdr_len = cdr_end - cdr_start + 1

    if len(cdr_pdb_resnums) != cdr_len:
        raise ValueError(
            f"cdr_pdb_resnums length {len(cdr_pdb_resnums)} != "
            f"CDR length {cdr_len}"
        )

    mutations: list[dict] = []
    for i, (lin_pos, pdb_resi) in enumerate(
        zip(range(cdr_start, cdr_end + 1), cdr_pdb_resnums)
    ):
        if lin_pos >= len(wt_seq) or lin_pos >= len(cand_seq):
            break
        wt_aa   = wt_seq[lin_pos]
        cand_aa = cand_seq[lin_pos]
        if wt_aa != cand_aa:
            mutations.append({
                "chain": chain,
                "resi":  pdb_resi,
                "wt":    wt_aa,
                "mut":   cand_aa,
            })
    return mutations


# ── Amino-acid volume analysis helper ─────────────────────────────────────────

def volume_change_at_interface(
    wt_seq:           str,
    cand_seq:         str,
    interface_linear: list[int],
) -> dict[str, Any]:
    """
    Compute per-site and total volume changes at interface positions.
    Fast Level-0 sanity check requiring no structure.

    Parameters
    ----------
    interface_linear : list of 0-indexed linear positions that are
        in contact with the antigen in the WT complex

    Returns
    -------
    dict with total_delta, per_site list, and a flag list
    """
    per_site = []
    flags    = []
    total    = 0.0

    for pos in interface_linear:
        if pos >= len(wt_seq) or pos >= len(cand_seq):
            continue
        wt_aa  = wt_seq[pos]
        mut_aa = cand_seq[pos]
        if wt_aa == mut_aa:
            continue
        delta = AA_VOLUME.get(mut_aa, 130.0) - AA_VOLUME.get(wt_aa, 130.0)
        total += delta
        per_site.append({"linear": pos, "wt": wt_aa, "mut": mut_aa,
                         "delta_A3": round(delta, 1)})
        if delta >= VOLUME_DELTA_FAIL:
            flags.append(f"L0_VOL_LARGE@lin{pos}({wt_aa}->{mut_aa},{delta:+.0f})")
        elif delta >= VOLUME_DELTA_WARN:
            flags.append(f"L0_VOL_WARN@lin{pos}({wt_aa}->{mut_aa},{delta:+.0f})")

    return {"total_delta_A3": round(total, 1), "per_site": per_site,
            "flags": flags}


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> None:
    import argparse, json

    p = argparse.ArgumentParser(
        description="T1.5 Fast Steric Clash & Epitope-Overlap Check"
    )
    p.add_argument("--mask_json",   required=True)
    p.add_argument("--fasta",       required=True,
                   help="FASTA of candidate sequences")
    p.add_argument("--output",      default="reports/t15_clash_check.json")
    p.add_argument("--level",       type=int, default=1,
                   choices=[0, 1],
                   help="0=volume only, 1=EvoEF2+atomic (default 1)")
    p.add_argument("--clash_max",   type=int, default=0)
    p.add_argument("--epi_min",     type=float, default=0.70)
    p.add_argument("--evoef2",      default=None)
    p.add_argument("--verbose",     action="store_true")
    args = p.parse_args()

    checker = from_mask_json(
        args.mask_json,
        evoef2_exe          = args.evoef2,
        clash_count_max     = args.clash_max,
        epitope_overlap_min = args.epi_min,
    )

    mask = json.loads(Path(args.mask_json).read_text())
    wt_seq   = mask["wt_sequence"]
    redesign = mask.get("design_mask", {}).get("redesign_cdrs", [])

    # Build mutation list for each candidate
    from core.evaluation.sequence_liability_qc import load_fasta
    seqs = load_fasta(args.fasta)
    print(f"Loaded {len(seqs)} sequences. WT epitope size: {len(checker._wt_epitope)}")

    candidates: dict[str, list[dict]] = {}
    for sid, seq in seqs.items():
        muts: list[dict] = []
        for cdr_name in redesign:
            info    = mask["cdr_regions"][cdr_name]
            lin     = (info["linear_start"], info["linear_end"])
            pdbnums = info["pdb_resnums"]
            muts   += mutations_from_sequences(
                wt_seq, seq, lin, pdbnums,
                chain=mask.get("vhh_chain", "A")
            )
        candidates[sid] = muts

    results = checker.check_batch(candidates, level=args.level, verbose=args.verbose)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps({sid: r.to_dict() for sid, r in results.items()},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nResults written to: {args.output}")


if __name__ == "__main__":
    _cli()
