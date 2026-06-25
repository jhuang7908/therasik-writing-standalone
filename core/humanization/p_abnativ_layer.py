"""

p-AbNatiV2 Pairing Guard Layer

==============================



Provides paired humanness and pairing likelihood evaluation using AbNatiV v2.



Rare PDB artifacts (duplicate FR4 residues with insertion codes) and extended VH

CDR2 insertions can cause the bundled AbNatiV ANARCI alignment to discard chains.

Overrides live in ``data/humanization_assay/pabnativ2_sequence_overrides.json``.

When paired scoring fails, optional unpaired VH2/VL2 fallback may fill scores.

"""

from __future__ import annotations



import json

from dataclasses import dataclass

from pathlib import Path

from typing import Any, Dict, Optional, Tuple



_SUITE_ROOT = Path(__file__).resolve().parents[2]

_OVERRIDES_JSON = _SUITE_ROOT / "data" / "humanization_assay" / "pabnativ2_sequence_overrides.json"

_OVERRIDES_CACHE: Optional[Dict[str, Any]] = None





@dataclass

class PairedAbNatiVResult:

    vh_humanness: Optional[float]

    vl_humanness: Optional[float]

    paired_humanness: Optional[float]

    pairing_likelihood: Optional[float]

    error: Optional[str] = None

    warning: Optional[str] = None





def _load_overrides() -> Dict[str, Any]:

    global _OVERRIDES_CACHE

    if _OVERRIDES_CACHE is not None:

        return _OVERRIDES_CACHE

    if not _OVERRIDES_JSON.exists():

        _OVERRIDES_CACHE = {}

        return _OVERRIDES_CACHE

    try:

        _OVERRIDES_CACHE = json.loads(_OVERRIDES_JSON.read_text(encoding="utf-8"))

    except Exception:

        _OVERRIDES_CACHE = {}

    return _OVERRIDES_CACHE





def _apply_sequence_overrides(seq_id: str, vh: str, vl: str) -> Tuple[str, str]:

    ov = _load_overrides().get(seq_id)

    if not isinstance(ov, dict):

        return vh, vl

    if isinstance(ov.get("vh_seq"), str) and ov["vh_seq"].strip():

        vh = "".join(aa for aa in ov["vh_seq"].upper() if aa in set("ACDEFGHIKLMNPQRSTVWY"))

    if isinstance(ov.get("vl_seq"), str) and ov["vl_seq"].strip():

        vl = "".join(aa for aa in ov["vl_seq"].upper() if aa in set("ACDEFGHIKLMNPQRSTVWY"))

    return vh, vl





def _fallback_unpaired_abnativ2(vh: str, vl: str, seq_id: str) -> PairedAbNatiVResult:

    """Use AbNatiV2 VH2/VL2 single-chain models when paired alignment fails."""

    from Bio.Seq import Seq

    from Bio.SeqRecord import SeqRecord

    from abnativ.model.scoring_functions import abnativ_scoring



    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")

    vh = "".join(aa for aa in vh.upper() if aa in valid_aa)

    vl = "".join(aa for aa in vl.upper() if aa in valid_aa)



    vh_s: Optional[float] = None

    vl_s: Optional[float] = None

    notes: list[str] = []



    try:

        df_h, _ = abnativ_scoring(

            "VH2",

            [SeqRecord(Seq(vh), id=seq_id)],

            batch_size=1,

            mean_score_only=True,

            do_align=True,

            verbose=False,

            run_parall_al=False,

        )

        col_h = "AbNatiV VH2 Score"

        if df_h is not None and len(df_h) >= 1 and col_h in df_h.columns:

            vh_s = round(float(df_h.iloc[0][col_h]), 4)

        elif df_h is None or len(df_h) < 1:

            notes.append("VH2:empty_or_discarded")

    except Exception as exc:

        notes.append(f"VH2:{exc}")



    try:

        df_l, _ = abnativ_scoring(

            "VL2",

            [SeqRecord(Seq(vl), id=seq_id)],

            batch_size=1,

            mean_score_only=True,

            do_align=True,

            verbose=False,

            run_parall_al=False,

        )

        col_l = "AbNatiV VL2 Score"

        if df_l is not None and len(df_l) >= 1 and col_l in df_l.columns:

            vl_s = round(float(df_l.iloc[0][col_l]), 4)

        elif df_l is None or len(df_l) < 1:

            notes.append("VL2:empty_or_discarded")

    except Exception as exc:

        notes.append(f"VL2:{exc}")



    if vh_s is not None and vl_s is not None:

        paired = round((vh_s + vl_s) / 2.0, 4)

        return PairedAbNatiVResult(

            vh_humanness=vh_s,

            vl_humanness=vl_s,

            paired_humanness=paired,

            pairing_likelihood=None,

            error=None,

            warning=(

                "Paired AbNatiV2 alignment failed; scores use unpaired VH2+VL2 mean; "

                "pairing likelihood not computed."

            ),

        )

    if vl_s is not None and vh_s is None:

        return PairedAbNatiVResult(

            vh_humanness=None,

            vl_humanness=vl_s,

            paired_humanness=vl_s,

            pairing_likelihood=None,

            error=None,

            warning=(

                "VH chain AbNatiV2 alignment failed (e.g. extended CDR2 insertions); "

                "VL humanness from unpaired VL2 only; pairing likelihood N/A."

            ),

        )

    return PairedAbNatiVResult(

        None,

        None,

        None,

        None,

        error="; ".join(notes) if notes else "AbNatiV unpaired fallback failed",

    )





def _merge_notes(warn: Optional[str], notes: list[str]) -> Optional[str]:

    tail = "; ".join(notes)

    if not tail:

        return warn

    if warn:

        return f"{warn} ({tail})"

    return tail





def score_paired_humanness(vh_seq: str, vl_seq: str, seq_id: str = "query") -> PairedAbNatiVResult:

    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")

    vh_clean = "".join(aa for aa in vh_seq.upper() if aa in valid_aa)

    vl_clean = "".join(aa for aa in vl_seq.upper() if aa in valid_aa)

    vh_clean, vl_clean = _apply_sequence_overrides(seq_id, vh_clean, vl_clean)



    if len(vh_clean) < 90 or len(vl_clean) < 90:

        return PairedAbNatiVResult(None, None, None, None, error="Sequence too short")



    try:

        import pandas as pd

    except ImportError as e:

        return PairedAbNatiVResult(None, None, None, None, error=f"ImportError: {e}")



    df_in = pd.DataFrame([{"ID": seq_id, "vh_seq": vh_clean, "vl_seq": vl_clean}])



    try:

        from abnativ.model.scoring_functions import abnativ_scoring_paired



        req_cols = (

            "AbNatiV Heavy Score",

            "AbNatiV Light Score",

            "AbNatiV Heavy-Light Score",

            "AbNatiV Pairing Score (%)",

        )

        notes: list[str] = []

        for do_align in (True, False):

            try:

                df, _ = abnativ_scoring_paired(

                    df_pairs=df_in,

                    col_id="ID",

                    col_vh="vh_seq",

                    col_vl="vl_seq",

                    batch_size=1,

                    mean_score_only=True,

                    do_align=do_align,

                    verbose=False,

                    run_parall_al=False,

                )

            except Exception as exc:

                notes.append(f"do_align={do_align}:{exc}")

                continue

            if df is None or getattr(df, "empty", True) or len(df) < 1:

                notes.append(f"do_align={do_align}:empty_result")

                continue



            row0 = df.iloc[0]

            missing = [c for c in req_cols if c not in row0.index]

            if missing:

                return PairedAbNatiVResult(

                    None,

                    None,

                    None,

                    None,

                    error=f"AbNatiV missing columns: {missing}",

                )



            vh_hum = round(float(row0["AbNatiV Heavy Score"]), 4)

            vl_hum = round(float(row0["AbNatiV Light Score"]), 4)

            paired_hum = round(float(row0["AbNatiV Heavy-Light Score"]), 4)

            pair_like = round(float(row0["AbNatiV Pairing Score (%)"]) / 100.0, 4)

            return PairedAbNatiVResult(

                vh_humanness=vh_hum,

                vl_humanness=vl_hum,

                paired_humanness=paired_hum,

                pairing_likelihood=pair_like,

            )



        fb = _fallback_unpaired_abnativ2(vh_clean, vl_clean, seq_id)

        if fb.vl_humanness is not None or fb.vh_humanness is not None:

            fb.warning = _merge_notes(fb.warning, notes)

            return fb

        return PairedAbNatiVResult(

            None,

            None,

            None,

            None,

            error="; ".join(notes) if notes else "AbNatiV returned empty result",

        )

    except Exception as e:

        return PairedAbNatiVResult(None, None, None, None, error=str(e))


