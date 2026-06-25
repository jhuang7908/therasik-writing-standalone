"""
sequence_delivery.assembler — Generalized antibody full-length assembly.

Supports:
  - IgG HC:  SP + VH + CH1 + Hinge + CH2 + CH3
  - kappa LC: SP + VL + CL
  - scFv:     SP + VH + linker + VL  (or VL + linker + VH)
  - Bispecific unit: two VH or VH+VL joined by a linker

All inputs are plain AA strings. Output is a DeliverySequence dataclass
that records provenance and can be rendered to FASTA or JSON.

Canonical linkers (pass by name):
  "G4S"   → GGGGS
  "G4S2"  → GGGGSGGGGS
  "G4S3"  → GGGGSGGGGSGGGGS
  "Whitlow" → GSTSGSGKPGSGEGSTKG
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import json


# ── Canonical linker sequences ─────────────────────────────────────────────
LINKER_LIBRARY: dict[str, str] = {
    "G4S":     "GGGGS",
    "G4S2":    "GGGGSGGGGS",
    "G4S3":    "GGGGSGGGGSGGGGS",
    "Whitlow": "GSTSGSGKPGSGEGSTKG",
}


# ── Dataclass: one assembled chain ────────────────────────────────────────
@dataclass
class AssembledChain:
    name: str
    chain_type: str          # "HC", "LC", "scFv", "custom"
    full_aa: str             # complete AA including SP
    parts: dict[str, str]   # {region_name: sequence_fragment}
    notes: list[str] = field(default_factory=list)

    def to_fasta(self) -> str:
        return f">{self.name}\n{self.full_aa}"

    def to_dict(self) -> dict:
        return asdict(self)

    def __len__(self) -> int:
        return len(self.full_aa)


# ── Dataclass: full antibody delivery package ─────────────────────────────
@dataclass
class DeliveryPackage:
    package_id: str
    chains: list[AssembledChain] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_chain(self, chain: AssembledChain) -> None:
        self.chains.append(chain)

    def to_fasta(self) -> str:
        return "\n".join(c.to_fasta() for c in self.chains)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {
                "package_id": self.package_id,
                "metadata": self.metadata,
                "chains": [c.to_dict() for c in self.chains],
            },
            indent=indent,
            ensure_ascii=False,
        )

    def save_fasta(self, path: str) -> None:
        from pathlib import Path
        Path(path).write_text(self.to_fasta(), encoding="utf-8")

    def save_json(self, path: str) -> None:
        from pathlib import Path
        Path(path).write_text(self.to_json(), encoding="utf-8")


# ── Assembly functions ─────────────────────────────────────────────────────

def assemble_heavy_chain(
    name: str,
    *,
    sp: str,
    vh: str,
    ch1: str,
    hinge: str,
    ch2: str,
    ch3: str,
    notes: Optional[list[str]] = None,
) -> AssembledChain:
    """Assemble a full IgG heavy chain: SP + VH + CH1 + Hinge + CH2 + CH3."""
    full = sp + vh + ch1 + hinge + ch2 + ch3
    parts = {
        "SP": sp, "VH": vh,
        "CH1": ch1, "Hinge": hinge, "CH2": ch2, "CH3": ch3,
    }
    return AssembledChain(
        name=name, chain_type="HC",
        full_aa=full, parts=parts, notes=notes or [],
    )


def assemble_light_chain(
    name: str,
    *,
    sp: str,
    vl: str,
    cl: str,
    notes: Optional[list[str]] = None,
) -> AssembledChain:
    """Assemble a full κ/λ light chain: SP + VL + CL."""
    full = sp + vl + cl
    parts = {"SP": sp, "VL": vl, "CL": cl}
    return AssembledChain(
        name=name, chain_type="LC",
        full_aa=full, parts=parts, notes=notes or [],
    )


def assemble_scfv(
    name: str,
    *,
    sp: str,
    vh: str,
    vl: str,
    linker: str = "G4S3",
    orientation: str = "VH-VL",
    notes: Optional[list[str]] = None,
) -> AssembledChain:
    """Assemble a single-chain Fv: SP + VH + linker + VL (or VL + linker + VH).

    Args:
        linker:      Named linker (see LINKER_LIBRARY) or custom AA string.
        orientation: "VH-VL" (default) or "VL-VH".
    """
    linker_seq = LINKER_LIBRARY.get(linker, linker)
    if orientation == "VL-VH":
        body = vl + linker_seq + vh
        parts = {"SP": sp, "VL": vl, "Linker": linker_seq, "VH": vh}
    else:
        body = vh + linker_seq + vl
        parts = {"SP": sp, "VH": vh, "Linker": linker_seq, "VL": vl}
    return AssembledChain(
        name=name, chain_type="scFv",
        full_aa=sp + body, parts=parts, notes=notes or [],
    )


def assemble_custom(
    name: str,
    *,
    parts: dict[str, str],
    order: list[str],
    notes: Optional[list[str]] = None,
) -> AssembledChain:
    """Assemble a chain from arbitrary named parts in the given order.

    Args:
        parts: {region_name: sequence}.
        order: list of region names to concatenate in order.
    """
    full = "".join(parts[k] for k in order)
    return AssembledChain(
        name=name, chain_type="custom",
        full_aa=full, parts=parts, notes=notes or [],
    )
