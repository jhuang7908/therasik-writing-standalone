"""
FASTA and annotated sequence assembly for CAR constructs.
Concatenates element sequences in slot order with domain annotations.
Supports both amino acid and codon-optimized DNA output.
"""
from __future__ import annotations
import textwrap
from typing import Any

from .codon_optimizer import CodonOptimizer


class FASTAAssembler:
    """Assembles CAR construct sequences from element library."""

    def __init__(self, library_idx: dict[str, dict]):
        self._lib = library_idx
        self._codon_opt = CodonOptimizer()

    def assemble(self, element_ids: list[str], name: str = "CAR_construct") -> dict:
        segments: list[dict] = []
        full_seq = ""
        pos = 1

        for eid in element_ids:
            e = self._lib.get(eid, {})
            seq = e.get("sequence", "")
            if not seq or len(seq) < 3:
                continue

            is_dna = e.get("sequence_type") == "DNA"
            if is_dna:
                continue

            start = pos
            end = pos + len(seq) - 1
            segments.append({
                "id": eid,
                "name": e.get("name", eid),
                "category": e.get("category", ""),
                "start": start,
                "end": end,
                "length": len(seq),
                "sequence": seq,
            })
            full_seq += seq
            pos = end + 1

        return {
            "name": name,
            "total_length_aa": len(full_seq),
            "sequence": full_seq,
            "segments": segments,
            "fasta": self._to_fasta(name, full_seq),
            "annotated_fasta": self._to_annotated_fasta(name, segments),
            "domain_map": self._domain_map(segments),
        }

    def _to_fasta(self, name: str, seq: str, line_width: int = 80) -> str:
        lines = [f">{name} | {len(seq)}aa"]
        for i in range(0, len(seq), line_width):
            lines.append(seq[i : i + line_width])
        return "\n".join(lines)

    def _to_annotated_fasta(self, name: str, segments: list[dict]) -> str:
        lines = [f">{name} | domain-annotated"]
        for seg in segments:
            lines.append(f"; [{seg['start']}-{seg['end']}] {seg['id']} ({seg['category']}, {seg['length']}aa)")
            seq = seg["sequence"]
            for i in range(0, len(seq), 80):
                lines.append(seq[i : i + 80])
        return "\n".join(lines)

    def _domain_map(self, segments: list[dict]) -> str:
        if not segments:
            return ""
        total = segments[-1]["end"] if segments else 0
        lines = [f"Domain Map ({total}aa total):", "=" * 60]
        for seg in segments:
            bar_len = max(1, seg["length"] // 5)
            bar = "█" * bar_len
            lines.append(
                f"  {seg['start']:>5}-{seg['end']:<5} {bar} {seg['id']} ({seg['length']}aa)"
            )
        lines.append("=" * 60)
        return "\n".join(lines)

    def assemble_dna(
        self,
        element_ids: list[str],
        name: str = "CAR_construct",
        deplete_cpg: bool = False,
    ) -> dict:
        """Assemble and codon-optimize the construct into DNA.

        Returns dict with: dna_fasta, dna_sequence, cai, gc_content,
        length_bp, segments_dna, warnings.
        """
        aa_result = self.assemble(element_ids, name)
        aa_seq = aa_result["sequence"]
        if not aa_seq:
            return {"dna_fasta": "", "dna_sequence": "", "cai": 0, "gc_content": 0,
                    "length_bp": 0, "segments_dna": [], "warnings": ["No AA sequence to optimize"]}

        optimizer = CodonOptimizer(deplete_cpg=deplete_cpg)
        opt = optimizer.optimize(aa_seq)
        dna = opt["dna"]

        segments_dna = []
        for seg in aa_result["segments"]:
            nt_start = (seg["start"] - 1) * 3 + 1
            nt_end = seg["end"] * 3
            segments_dna.append({
                "id": seg["id"],
                "name": seg["name"],
                "category": seg["category"],
                "start_nt": nt_start,
                "end_nt": nt_end,
                "length_bp": seg["length"] * 3,
                "dna_sequence": dna[nt_start - 1: nt_end],
            })

        dna_fasta_lines = [f">{name}_DNA | {len(dna)}bp | CAI={opt['cai']:.3f} | GC={opt['gc_content']:.1%}"]
        for i in range(0, len(dna), 80):
            dna_fasta_lines.append(dna[i: i + 80])

        return {
            "dna_fasta": "\n".join(dna_fasta_lines),
            "dna_sequence": dna,
            "cai": opt["cai"],
            "gc_content": opt["gc_content"],
            "length_bp": opt["length_bp"],
            "segments_dna": segments_dna,
            "cpg_depleted": deplete_cpg,
            "warnings": opt["warnings"],
        }

    def export_genbank_features(self, element_ids: list[str], name: str = "CAR") -> str:
        """Export amino-acid level GenBank flat file."""
        result = self.assemble(element_ids, name)
        lines = [
            f"LOCUS       {name:<16} {result['total_length_aa']} aa    linear   SYN",
            f"DEFINITION  Chimeric Antigen Receptor construct, {len(result['segments'])} domains",
            "FEATURES             Location/Qualifiers",
        ]
        for seg in result["segments"]:
            lines.append(f"     misc_feature    {seg['start']}..{seg['end']}")
            lines.append(f'                     /label="{seg["id"]}"')
            lines.append(f'                     /note="{seg["category"]}: {seg["name"]}"')

        lines.append("ORIGIN")
        seq = result["sequence"]
        for i in range(0, len(seq), 60):
            chunk = seq[i : i + 60]
            spaced = " ".join(chunk[j : j + 10] for j in range(0, len(chunk), 10))
            lines.append(f"{i+1:>9} {spaced}")
        lines.append("//")
        return "\n".join(lines)

    def export_genbank_dna(self, element_ids: list[str], name: str = "CAR", deplete_cpg: bool = False) -> str:
        """Export DNA-level GenBank flat file with codon-optimized nucleotide sequence."""
        dna_result = self.assemble_dna(element_ids, name, deplete_cpg=deplete_cpg)
        dna = dna_result["dna_sequence"]
        if not dna:
            return ""

        lines = [
            f"LOCUS       {name:<16} {len(dna)} bp    ds-DNA  linear   SYN",
            f"DEFINITION  Chimeric Antigen Receptor, codon-optimized for Homo sapiens",
            f"COMMENT     CAI={dna_result['cai']:.3f}; GC={dna_result['gc_content']:.1%}",
            "FEATURES             Location/Qualifiers",
        ]
        for seg in dna_result["segments_dna"]:
            lines.append(f"     CDS             {seg['start_nt']}..{seg['end_nt']}")
            lines.append(f'                     /label="{seg["id"]}"')
            lines.append(f'                     /note="{seg["category"]}: {seg["name"]}"')

        lines.append("ORIGIN")
        dna_lower = dna.lower()
        for i in range(0, len(dna_lower), 60):
            chunk = dna_lower[i: i + 60]
            spaced = " ".join(chunk[j: j + 10] for j in range(0, len(chunk), 10))
            lines.append(f"{i+1:>9} {spaced}")
        lines.append("//")
        return "\n".join(lines)
