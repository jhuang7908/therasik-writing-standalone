"""
SmartLink Matrix for tandem / multispecific antibody constructs.

This module is intentionally separate from IgG-like bispecific pairing logic.
It evaluates single-chain tandem formats:

- tandem scFv: scFv-linker-scFv(-linker-scFv...)
- tandem VHH: VHH-linker-VHH(-linker-VHH...)
- mixed tandem: scFv-linker-VHH or VHH-linker-scFv

The output is JSON-first and can be consumed by API routes, console UI, or
report renderers. It does not run structure prediction; structural confirmation
can be layered on top later.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import permutations
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from core.cmc.bispecific_cmc_engine import DEFAULT_LINKERS, ER_PI_CRIT, ER_PI_WARN
from core.cmc.cmc_metrics import (
    compute_GRAVY,
    compute_aggregation_motifs,
    compute_charge_patch_max7,
    compute_chemical_liabilities,
    compute_hydro_cluster_count,
    compute_hydro_patch_max9,
    compute_instability_index,
    compute_net_charge,
    compute_pI,
    compute_sap_7mer_proxy,
)

VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")

DEFAULT_SCFV_LINKERS: Dict[str, str] = {
    "G4S3": "GGGGSGGGGSGGGGS",
    "G4S4": "GGGGSGGGGSGGGGSGGGGS",
    "Whitlow": "GSTSGSGKPGSGEGSTKG",
}


@dataclass(frozen=True)
class TandemDomain:
    """One domain block in a tandem construct."""

    name: str
    kind: str  # "vhh" or "scfv"
    sequence: str = ""  # VHH sequence, or pre-assembled scFv if provided
    vh: str = ""
    vl: str = ""
    orientation: str = "VH-VL"  # for scFv only: "VH-VL" or "VL-VH"
    intra_linker_name: str = "G4S3"
    target: str = ""


@dataclass(frozen=True)
class LinkerCandidate:
    name: str
    sequence: str


@dataclass(frozen=True)
class SmartLinkRow:
    rank_key: float
    construct_id: str
    format_class: str
    domain_order: List[str]
    linker: str
    linker_seq: str
    sequence: str
    length: int
    pI: float
    net_charge_pH7: float
    GRAVY: float
    instability_index: float
    hydro_patch_max9: float
    charge_patch_max7: float
    SAP_score: float
    agg_motifs: int
    hydro_cluster_count: int
    pi_flag: str
    overall_status: str
    n_warn: int
    n_fail: int
    junction_liabilities: List[Dict[str, Any]]
    linker_charge_pH7: float
    linker_length: int
    notes: List[str]


def clean_aa(seq: str) -> str:
    """Return an uppercase amino-acid-only sequence."""

    return "".join(aa for aa in (seq or "").upper() if aa in VALID_AA)


def _pi_flag(pi: float, er_threshold: float = ER_PI_WARN) -> str:
    if pi >= ER_PI_CRIT:
        return "critical"
    if pi >= er_threshold:
        return "warn"
    return "pass"


def _status_from_counts(n_warn: int, n_fail: int) -> str:
    if n_fail:
        return "FAIL"
    if n_warn:
        return "WARN"
    return "PASS"


def _domain_sequence(domain: TandemDomain) -> str:
    kind = domain.kind.lower().strip()
    if kind == "vhh":
        seq = clean_aa(domain.sequence or domain.vh)
        if not seq:
            raise ValueError(f"VHH domain {domain.name!r} has no sequence")
        return seq

    if kind != "scfv":
        raise ValueError(f"Unsupported tandem domain kind: {domain.kind!r}")

    if domain.sequence:
        seq = clean_aa(domain.sequence)
        if not seq:
            raise ValueError(f"scFv domain {domain.name!r} has an empty sequence")
        return seq

    vh = clean_aa(domain.vh)
    vl = clean_aa(domain.vl)
    if not vh or not vl:
        raise ValueError(f"scFv domain {domain.name!r} requires VH and VL")
    intra = DEFAULT_SCFV_LINKERS.get(domain.intra_linker_name, domain.intra_linker_name)
    intra = clean_aa(intra)
    if domain.orientation.upper() == "VL-VH":
        return vl + intra + vh
    return vh + intra + vl


def infer_format_class(domains: Sequence[TandemDomain]) -> str:
    kinds = {d.kind.lower().strip() for d in domains}
    if kinds == {"scfv"}:
        return "tandem_scfv"
    if kinds == {"vhh"}:
        return "tandem_vhh"
    if kinds <= {"scfv", "vhh"}:
        return "mixed_scfv_vhh"
    return "tandem_unknown"


def _linker_candidates(linkers: Optional[Dict[str, str]]) -> List[LinkerCandidate]:
    raw = linkers or DEFAULT_LINKERS
    return [LinkerCandidate(name=k, sequence=clean_aa(v)) for k, v in raw.items()]


def _domain_orders(
    domains: Sequence[TandemDomain],
    *,
    compare_orders: bool,
    max_orders: int,
) -> List[Tuple[TandemDomain, ...]]:
    if not compare_orders:
        return [tuple(domains)]
    if len(domains) > 5:
        raise ValueError("SmartLink Matrix supports up to 5 tandem domains")
    orders = list(permutations(domains))
    if len(orders) > max_orders:
        # Keep deterministic behavior for UI use; callers can increase max_orders.
        orders = orders[:max_orders]
    return orders


def _junction_liabilities(sequence: str, junctions: Iterable[int]) -> List[Dict[str, Any]]:
    """Report sequence-liability motifs within +/- 3 aa of linker junctions."""

    out: List[Dict[str, Any]] = []
    liabilities = compute_chemical_liabilities(sequence)
    all_sites: List[Tuple[str, int]] = []
    for key, sites in liabilities.items():
        for pos in sites:
            all_sites.append((key, pos))

    for j in junctions:
        lo = max(0, j - 3)
        hi = min(len(sequence), j + 4)
        window = sequence[lo:hi]
        hits = [
            {"type": key, "position": pos}
            for key, pos in all_sites
            if lo <= pos < hi
        ]
        if hits:
            out.append({"junction": j, "window": window, "hits": hits})
    return out


def _metric_flags(metrics: Dict[str, Any], pi_flag: str, junction_n: int) -> Tuple[int, int, List[str]]:
    warn = 0
    fail = 0
    notes: List[str] = []

    def mark(condition_fail: bool, condition_warn: bool, label: str) -> None:
        nonlocal warn, fail
        if condition_fail:
            fail += 1
            notes.append(f"{label}: FAIL")
        elif condition_warn:
            warn += 1
            notes.append(f"{label}: WARN")

    mark(pi_flag == "critical", pi_flag == "warn", "fusion pI / ER expression")
    mark(metrics["GRAVY"] > 0.10, metrics["GRAVY"] > -0.05, "global GRAVY")
    mark(metrics["instability_index"] > 65.0, metrics["instability_index"] > 50.0, "instability index")
    mark(metrics["hydro_patch_max9"] > 0.90, metrics["hydro_patch_max9"] > 0.75, "hydrophobic patch")
    mark(metrics["SAP_score"] > 0.99, metrics["SAP_score"] > 0.857, "SAP proxy")
    mark(metrics["charge_patch_max7"] > 6.0, metrics["charge_patch_max7"] > 4.0, "charge patch")
    mark(metrics["agg_motifs"] > 7, metrics["agg_motifs"] > 5, "aggregation motifs")
    mark(metrics["hydro_cluster_count"] > 5, metrics["hydro_cluster_count"] > 3, "hydrophobic clusters")
    mark(junction_n > 2, junction_n > 0, "junction liability")
    return warn, fail, notes


def assemble_tandem_sequence(
    domains: Sequence[TandemDomain],
    linker: LinkerCandidate,
) -> Tuple[str, List[int]]:
    """Assemble domains with the same inter-domain linker at every junction."""

    parts: List[str] = []
    junctions: List[int] = []
    cursor = 0
    for idx, domain in enumerate(domains):
        if idx:
            parts.append(linker.sequence)
            cursor += len(linker.sequence)
            junctions.append(cursor)
        dseq = _domain_sequence(domain)
        parts.append(dseq)
        cursor += len(dseq)
        if idx < len(domains) - 1:
            junctions.append(cursor)
    return "".join(parts), junctions


def evaluate_tandem_construct(
    domains: Sequence[TandemDomain],
    linker: LinkerCandidate,
    *,
    construct_id: str = "tandem",
    er_threshold: float = ER_PI_WARN,
) -> SmartLinkRow:
    """Evaluate one domain order and one linker."""

    sequence, junctions = assemble_tandem_sequence(domains, linker)
    pi = compute_pI(sequence)
    pi_flag = _pi_flag(pi, er_threshold)
    metrics: Dict[str, Any] = {
        "GRAVY": compute_GRAVY(sequence),
        "instability_index": compute_instability_index(sequence),
        "hydro_patch_max9": compute_hydro_patch_max9(sequence),
        "charge_patch_max7": compute_charge_patch_max7(sequence),
        "SAP_score": compute_sap_7mer_proxy(sequence),
        "agg_motifs": compute_aggregation_motifs(sequence),
        "hydro_cluster_count": compute_hydro_cluster_count(sequence),
    }
    j_hits = _junction_liabilities(sequence, junctions)
    n_warn, n_fail, notes = _metric_flags(metrics, pi_flag, len(j_hits))
    status = _status_from_counts(n_warn, n_fail)

    # Higher is better. pI is used as a mild tie-breaker via rank_key.
    score = 100.0 - n_fail * 25.0 - n_warn * 8.0 - max(0.0, pi - 7.5)

    return SmartLinkRow(
        rank_key=round(score, 4),
        construct_id=construct_id,
        format_class=infer_format_class(domains),
        domain_order=[d.name for d in domains],
        linker=linker.name,
        linker_seq=linker.sequence,
        sequence=sequence,
        length=len(sequence),
        pI=pi,
        net_charge_pH7=compute_net_charge(sequence, 7.0),
        GRAVY=metrics["GRAVY"],
        instability_index=metrics["instability_index"],
        hydro_patch_max9=metrics["hydro_patch_max9"],
        charge_patch_max7=metrics["charge_patch_max7"],
        SAP_score=metrics["SAP_score"],
        agg_motifs=metrics["agg_motifs"],
        hydro_cluster_count=metrics["hydro_cluster_count"],
        pi_flag=pi_flag,
        overall_status=status,
        n_warn=n_warn,
        n_fail=n_fail,
        junction_liabilities=j_hits,
        linker_charge_pH7=compute_net_charge(linker.sequence, 7.0) if linker.sequence else 0.0,
        linker_length=len(linker.sequence),
        notes=notes,
    )


def compute_smartlink_matrix(
    domains: Sequence[TandemDomain],
    *,
    linkers: Optional[Dict[str, str]] = None,
    compare_orders: bool = True,
    max_orders: int = 120,
    er_threshold: float = ER_PI_WARN,
    construct_prefix: str = "smartlink",
) -> List[Dict[str, Any]]:
    """
    Compute orientation x linker matrix for tandem / multispecific constructs.

    Parameters
    ----------
    domains:
        Two to five TandemDomain objects.
    linkers:
        Optional inter-domain linker panel. Defaults to existing SmartLink
        linker panel from ``bispecific_cmc_engine``.
    compare_orders:
        If True, all N->C domain orders are evaluated. If False, input order is
        preserved and only linker choices are ranked.
    max_orders:
        Safety cap for permutation count.
    """

    if len(domains) < 2 or len(domains) > 5:
        raise ValueError("SmartLink Matrix requires 2 to 5 tandem domains")

    rows: List[SmartLinkRow] = []
    for order_idx, order in enumerate(
        _domain_orders(domains, compare_orders=compare_orders, max_orders=max_orders),
        start=1,
    ):
        for linker in _linker_candidates(linkers):
            cid = f"{construct_prefix}_{order_idx}_{linker.name.replace(' ', '_')}"
            rows.append(
                evaluate_tandem_construct(
                    order,
                    linker,
                    construct_id=cid,
                    er_threshold=er_threshold,
                )
            )

    rows.sort(key=lambda r: (-r.rank_key, r.n_fail, r.n_warn, r.pI, r.length))
    return [asdict(r) for r in rows]


def select_smartlink_recommendation(matrix: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Return primary, runner-up, and status counts from a SmartLink matrix."""

    if not matrix:
        raise ValueError("SmartLink matrix is empty")
    primary = matrix[0]
    runner_up = matrix[1] if len(matrix) > 1 else None
    return {
        "primary": primary,
        "runner_up": runner_up,
        "n_total": len(matrix),
        "n_pass": sum(1 for r in matrix if r["overall_status"] == "PASS"),
        "n_warn": sum(1 for r in matrix if r["overall_status"] == "WARN"),
        "n_fail": sum(1 for r in matrix if r["overall_status"] == "FAIL"),
        "format_class": primary.get("format_class"),
        "recommended_order": primary.get("domain_order"),
        "recommended_linker": primary.get("linker"),
    }


def run_smartlink_design(
    domains: Sequence[TandemDomain],
    *,
    linkers: Optional[Dict[str, str]] = None,
    compare_orders: bool = True,
    er_threshold: float = ER_PI_WARN,
    construct_prefix: str = "smartlink",
) -> Dict[str, Any]:
    """Convenience wrapper returning matrix + recommendation in one payload."""

    matrix = compute_smartlink_matrix(
        domains,
        linkers=linkers,
        compare_orders=compare_orders,
        er_threshold=er_threshold,
        construct_prefix=construct_prefix,
    )
    return {
        "analysis": "tandem_smartlink_matrix",
        "version": "v0.1",
        "input": {
            "n_domains": len(domains),
            "domain_names": [d.name for d in domains],
            "domain_kinds": [d.kind for d in domains],
            "compare_orders": compare_orders,
            "er_threshold": er_threshold,
        },
        "recommendation": select_smartlink_recommendation(matrix),
        "matrix": matrix,
    }

