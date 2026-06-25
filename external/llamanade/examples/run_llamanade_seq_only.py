"""
run_llamanade_seq_only.py
──────────────────────────────────────────────────────────────────────────────
Llamanade sequence-only humanization — no Modeller, no protinter.

PURPOSE
  Faithfully replicate the Llamanade "frequency-based substitution" layer and
  add explicit annotation of WHY each position is protected or substituted.
  Designed as a self-contained learning / benchmarking tool that runs on
  Windows without Linux dependencies.

ALGORITHM FAITHFULNESS
  ● Numbering      : Martin scheme (original Llamanade) — we convert IMGT rows
                     from imgt_number_anarcii to Martin keys via a position map
                     built from the same ANARCI output.
  ● CDR definition : AbM definition over Martin numbering (same as Llamanade
                     params.py: ANNOTATION_SCHEME="martin", ANNOTATION_DEFINITION="AbM")
                     CDR boundaries: CDR1=26-36, CDR2=50-59, CDR3=95-103
  ● Frequency gate : freq(donor_aa at position) < 0.10 in human VH profile
                     → suggest top-frequency human residue
  ● Structural gate: Llamanade calls protinter for intra-molecular contacts
                     (ionic, cation-π, aromatic-aromatic). When protinter is
                     absent we substitute a rule-based approximation:
                     -- FR2 hallmark positions 37, 45, 47 (Martin) are marked
                        STRUCT_PROTECT (paper §Results — these form FR2:FR4 and
                        FR2:CDR3 scaffold interactions in VHH/Nb)
                     -- Any Cys residue (free or disulfide-forming) is protected
                     -- For non-VHH species (chicken, bovine, rabbit, etc.) the
                        user can supply an extra protect set via --extra-protect
  ● No T20 scoring  : requires blastp; omitted. The output includes per-position
                     human frequency which carries the same information.

EXTENSION TO SPECIAL SPECIES (chicken / bovine / rabbit / equine / shark)
  See SPECIES_NOTES dict at the bottom of this module and the --species flag.
  Key differences handled:
  ─────────────────────────────────────────────────────────────────────────
  Species     | VH family    | Key FR2 hallmarks | CDR3 quirks
  ────────────┼──────────────┼───────────────────┼────────────────────────
  Alpaca/VHH  | IGHV3 (VHH) | E44/R45/F47       | long, extra Cys pairs
  Rabbit      | IGHV3/IGHV1 | normal hallmarks   | often long CDR3 (>14)
  Chicken     | no IGHV like | CDR3-focused       | ultralong CDR3
  Bovine      | IGHV         | ultralong CDR3     | CDR3 can be 50-70 aa
              |              |                    | with β-strand stalk
  Shark IgNAR | VNAR         | W33/Y108 anchor    | similar to VHH
  ─────────────────────────────────────────────────────────────────────────
  The frequency profile (ANARCI_Hum_H.json) was built from human VH sequences.
  For rabbit/chicken/bovine, the same profile is used with an INCREASED
  freq_threshold (0.15 recommended for rabbit, 0.20 for chicken/bovine) because
  those species have more FR divergence from human germline.

USAGE
  python run_llamanade_seq_only.py \\
      --fasta examples/alpaca_vhh_console.fasta \\
      [--species alpaca|rabbit|chicken|bovine|shark] \\
      [--freq-threshold 0.10] \\
      [--extra-protect 37 45 47] \\
      [--out examples/llamanade_result.json]

──────────────────────────────────────────────────────────────────────────────
"""

import argparse
import json
import sys
from pathlib import Path

# ── locate the ANARCI_Hum_H.json shipped with Llamanade ──────────────────────
_HERE = Path(__file__).resolve().parent          # examples/
_UPSTREAM = _HERE.parent / "Llamanade_upstream"
_PROFILE_PATH = _UPSTREAM / "resources" / "resources" / "ANARCI_Hum_H.json"

# ── AbM CDR boundaries in Martin numbering (Llamanade defaults) ──────────────
# SCHEMES["AbM"]["martin"] = [26,36,50,59,95,103]
# meaning CDR1 = 26..36, CDR2 = 50..59, CDR3 = 95..103
_ABM_MARTIN_CDR = (26, 36, 50, 59, 95, 103)

# ── Structural protection rules (paper-derived, replaces protinter) ──────────
# Martin positions always protected regardless of frequency:
#   37  : FR2 – forms cation-π with W103(FR4) and π-π with W103; also shields CDR3
#   45  : FR2 – forms cation-π (R45:W103) interaction in VHH; solvent-exposed,
#           supports solubility; paper explicitly states "not recommended to change"
#   47  : FR2 – F/L47 forms π-π interaction with W103; VHH-specific scaffold anchor
# These three are the "FR2 hallmark" positions that Llamanade always locks.
_FR2_HALLMARK_MARTIN = {37, 45, 47}

# ── IMGT-to-Martin position remapping ────────────────────────────────────────
# Llamanade uses Martin numbering internally (ANARCI --scheme martin).
# Our imgt_number_anarcii uses IMGT. The correspondence for the key FR2
# hallmarks is: IMGT 37→Martin 37, IMGT 47→Martin 47, IMGT 45→Martin 45
# (they coincide for FR1-FR3 in heavy chain; insertion codes diverge in CDR3).
# We build a direct Martin-key numbering by re-calling ANARCI with martin scheme.

# ── Species-specific notes ───────────────────────────────────────────────────
SPECIES_NOTES = {
    "alpaca": {
        "description": "Camelid VHH. FR2 hallmarks E44/R45/F47(IMGT) critical for solubility"
                       " and CDR3 scaffold. Extra Cys pairs in long CDR3 (>17 aa) must be"
                       " protected. Structural protection: Martin 37, 45, 47.",
        "freq_threshold": 0.10,
        "extra_protect_martin": set(),
        "cdr3_cys_protect": True,
    },
    "rabbit": {
        "description": "Rabbit VH/VL. Framework more diverged than mouse from human."
                       " Recommended freq_threshold 0.15 (more substitutions needed)."
                       " CDR3 often long (>14 aa); monitor CDR3 Cys pairs.",
        "freq_threshold": 0.15,
        "extra_protect_martin": set(),
        "cdr3_cys_protect": True,
    },
    "chicken": {
        "description": "Chicken IgY. Uses single VH family. CDR3 is the primary diversity"
                       " source (often ultralong; may be encoded by a single V-segment with"
                       " long D insertions). Framework is more diverged; freq_threshold 0.20"
                       " recommended. No VL pairing in IgNAR-like isotypes.",
        "freq_threshold": 0.20,
        "extra_protect_martin": set(),
        "cdr3_cys_protect": True,
    },
    "bovine": {
        "description": "Bovine ultralong CDR3. CDR3 can be 50-70 aa with a β-strand stalk"
                       " (CDRH3 stalk: ~10 aa) and an apical disulfide-rich knob. The stalk"
                       " extends into the VH domain — positions 93-94 (Martin) anchor the"
                       " stalk and must NOT be humanized. Set extra_protect to include 93,94."
                       " Freq_threshold 0.20.",
        "freq_threshold": 0.20,
        "extra_protect_martin": {93, 94},
        "cdr3_cys_protect": True,
    },
    "shark": {
        "description": (
            "Shark IgNAR VNAR domain — single-domain, no light chain, structurally "
            "closest to camelid VHH. ANARCI numbers VNAR as chain_type='H' using the "
            "heavy-chain HMM; Kabat output is reliable.\n"
            "\n"
            "VNAR Types:\n"
            "  Type I   — canonical Ig disulfide C22-C92 only; has HV2 loop (Kabat "
            "~56–64 region) unique to Type I, adds a 3rd hypervariable region; "
            "HV2 should be treated as an extra CDR region.\n"
            "  Type II  — ADDITIONAL disulfide between CDR1 Cys (Kabat ~30-36) and "
            "CDR3 Cys (~99-100x); both are inside AbM CDR definitions so they are "
            "already CDR-locked. CRITICAL: if the CDR1 Cys maps outside pos 26-36 "
            "(e.g. pos 23-25), it must be manually added to extra_protect.\n"
            "  Type III/IV — germline-encoded, no extra disulfide, fewest "
            "substitutions needed.\n"
            "\n"
            "Structural anchors equivalent to VHH FR2:FR4:\n"
            "  W36 (Kabat, equivalent to VHH pos37) — forms π-π with FR4 W103\n"
            "  Y108 (Kabat FR4) — equivalent anchor, always protect.\n"
            "All FR Cys beyond canonical C22/C92 must be protected "
            "(protect_all_fr_cys=True is auto-enabled for shark)."
        ),
        "freq_threshold": 0.10,
        "extra_protect_martin": {36, 108},   # W36 and Y108 structural anchors
        "cdr3_cys_protect": True,
        "protect_all_fr_cys": True,          # shark-specific: any non-CDR Cys protected
    },
    "mouse": {
        "description": "Standard mouse VH. Well-covered by Llamanade profile. Default"
                       " freq_threshold 0.10 applies.",
        "freq_threshold": 0.10,
        "extra_protect_martin": set(),
        "cdr3_cys_protect": False,
    },
}


def load_human_profile(profile_path: Path) -> dict:
    return json.loads(profile_path.read_text(encoding="utf-8"))


def number_with_kabat(seq: str) -> list[dict]:
    """Use anarcii Python package (to_scheme 'kabat') — no hmmscan needed.

    Martin and Kabat numbering are nearly identical for heavy chains; Llamanade
    uses Martin scheme which is a minor Kabat variant (same CDR boundaries for
    AbM definition). Profile keys in ANARCI_Hum_H.json use Kabat-style integers
    and insertion codes (e.g. '52A', '100A'), matching anarcii Kabat output.

    Returns list of {pos: int, ins: str, aa: str}, gaps excluded.
    """
    # add project core to path so anarcii package is importable
    proj_root = Path(__file__).resolve().parents[3]  # …/Antibody_Engineer_Suite
    if str(proj_root) not in sys.path:
        sys.path.insert(0, str(proj_root))

    try:
        from anarcii import Anarcii
    except ImportError as e:
        raise ImportError(
            "anarcii package not found. Run from the anarcii conda env:\n"
            "  conda run -n anarcii python run_llamanade_seq_only.py ..."
        ) from e

    anarcii_obj = Anarcii()
    anarcii_obj.number(seq.upper().replace(" ", ""))
    kab_result = anarcii_obj.to_scheme("kabat")

    seq_data = kab_result.get("Sequence", {})
    numbering = seq_data.get("numbering", [])

    rows = []
    for (pos_int, ins_code), aa in numbering:
        if aa == "-" or aa is None:
            continue
        rows.append({
            "pos": int(pos_int),
            "ins": ins_code.strip().upper(),
            "aa": aa,
        })
    return rows


def martin_key(row: dict) -> str:
    """Llamanade profile key: '31A', '52', etc."""
    return str(row["pos"]) + row["ins"]


def cdr_positions(rows: list[dict]) -> set[str]:
    """Return set of Martin keys that fall inside AbM CDR boundaries."""
    c1s, c1e, c2s, c2e, c3s, c3e = _ABM_MARTIN_CDR
    cdr = set()
    for r in rows:
        p = r["pos"]
        if c1s <= p <= c1e or c2s <= p <= c2e or c3s <= p <= c3e:
            cdr.add(martin_key(r))
    return cdr


def cdr3_cys_pairs(rows: list[dict]) -> set[str]:
    """Return Martin keys of Cys residues inside CDR3 that are in a Cys-pair.
    Protection rationale: these form structural disulfide bridges stabilising
    long CDR3 loops in VHH/Nb and some rabbit/bovine antibodies. Mutating them
    destroys the loop scaffold.
    """
    c3s, c3e = _ABM_MARTIN_CDR[4], _ABM_MARTIN_CDR[5]
    cys_keys = [martin_key(r) for r in rows
                if c3s <= r["pos"] <= c3e and r["aa"] == "C"]
    if len(cys_keys) >= 2:
        return set(cys_keys)
    return set()


def all_fr_cys_positions(rows: list[dict], cdr_keys: set[str]) -> set[str]:
    """Return Martin keys of ALL Cys residues that are outside CDR (FR Cys).
    Used for shark VNAR where any FR Cys beyond the canonical C22/C92 may
    participate in structural disulfide bonds (e.g. Type II extra disulfide).
    Canonical C22 and C92 are also returned (they would be FREQ_OK anyway, but
    explicit protection ensures they survive any edge-case sequences).
    """
    return {martin_key(r) for r in rows
            if r["aa"] == "C" and martin_key(r) not in cdr_keys}


def humanize_seq_only(
    seq: str,
    species: str = "alpaca",
    freq_threshold: float | None = None,
    extra_protect_martin: set[int] | None = None,
    profile: dict | None = None,
    profile_path: Path | None = None,
) -> dict:
    """
    Core Llamanade sequence-only humanization.

    Protection layers (why a position is NOT humanized):
      1. CDR     : CDR1/CDR2/CDR3 (AbM definition, Martin scheme) — never touched
      2. FREQ_OK : donor residue already has freq >= threshold in human profile
      3. STRUCT  : FR2 hallmarks (Martin 37/45/47) — paper-derived structural anchor
      4. CYS     : Cys pair in CDR3 — structural disulfide scaffold
      5. EXTRA   : caller-supplied extra_protect set (species-specific e.g. bovine 93/94)
      6. MISSING : position not in human profile (insertion code only; no guidance)

    Returns
    -------
    dict with keys:
      original_seq, humanized_seq, mutations (list), per_position (list)
    """
    if profile is None:
        pp = profile_path or _PROFILE_PATH
        profile = load_human_profile(pp)

    spec = SPECIES_NOTES.get(species, SPECIES_NOTES["alpaca"])
    if freq_threshold is None:
        freq_threshold = spec["freq_threshold"]
    extra_protect = set(spec["extra_protect_martin"])
    if extra_protect_martin:
        extra_protect |= {int(p) for p in extra_protect_martin}
    protect_cys = spec["cdr3_cys_protect"]

    # ── number with Martin scheme ──────────────────────────────────────────
    rows = number_with_kabat(seq)
    if not rows:
        return {"error": "ANARCI returned no rows. Check hmmscan/ANARCI installation."}

    cdr_keys = cdr_positions(rows)
    cys_keys = cdr3_cys_pairs(rows) if protect_cys else set()
    # for shark: protect ALL FR Cys (any non-CDR Cys could be disulfide-forming)
    protect_all_fr_cys = spec.get("protect_all_fr_cys", False)
    if protect_all_fr_cys:
        cys_keys = cys_keys | all_fr_cys_positions(rows, cdr_keys)

    # ── per-position analysis ──────────────────────────────────────────────
    per_pos = []
    humanized_aa_list = []
    mutations = []

    for r in rows:
        mk = martin_key(r)
        orig_aa = r["aa"]
        pos_int = r["pos"]

        # --- CDR: always keep ---
        if mk in cdr_keys:
            per_pos.append({
                "martin_key": mk, "original_aa": orig_aa,
                "humanized_aa": orig_aa, "action": "KEEP",
                "reason": "CDR (AbM definition)",
                "human_freq": profile.get(mk, {}).get(orig_aa),
            })
            humanized_aa_list.append(orig_aa)
            continue

        # --- lookup human frequency ---
        pos_profile = profile.get(mk, {})
        freq = pos_profile.get(orig_aa)
        if freq is None:
            freq = min(pos_profile.values()) if pos_profile else None

        # --- structural protection ---
        if pos_int in _FR2_HALLMARK_MARTIN:
            per_pos.append({
                "martin_key": mk, "original_aa": orig_aa,
                "humanized_aa": orig_aa, "action": "KEEP",
                "reason": "STRUCT_PROTECT: FR2 hallmark (paper Fig 3-4; cation-π/π-π scaffold)",
                "human_freq": freq,
            })
            humanized_aa_list.append(orig_aa)
            continue

        if mk in cys_keys:
            per_pos.append({
                "martin_key": mk, "original_aa": orig_aa,
                "humanized_aa": orig_aa, "action": "KEEP",
                "reason": "STRUCT_PROTECT: CDR3 Cys pair (disulfide scaffold in long CDR3)",
                "human_freq": freq,
            })
            humanized_aa_list.append(orig_aa)
            continue

        if pos_int in extra_protect:
            per_pos.append({
                "martin_key": mk, "original_aa": orig_aa,
                "humanized_aa": orig_aa, "action": "KEEP",
                "reason": f"EXTRA_PROTECT: species={species} (e.g. bovine stalk anchor)",
                "human_freq": freq,
            })
            humanized_aa_list.append(orig_aa)
            continue

        # --- no human profile coverage ---
        if not pos_profile:
            per_pos.append({
                "martin_key": mk, "original_aa": orig_aa,
                "humanized_aa": orig_aa, "action": "KEEP",
                "reason": "MISSING_PROFILE: position not in human VH profile",
                "human_freq": None,
            })
            humanized_aa_list.append(orig_aa)
            continue

        # --- frequency gate ---
        if freq is not None and freq >= freq_threshold:
            per_pos.append({
                "martin_key": mk, "original_aa": orig_aa,
                "humanized_aa": orig_aa, "action": "KEEP",
                "reason": f"FREQ_OK: freq={freq:.3f} >= threshold {freq_threshold}",
                "human_freq": freq,
            })
            humanized_aa_list.append(orig_aa)
            continue

        # --- substitute: top frequency human residue at this position ---
        new_aa = next(iter(pos_profile))   # profile is sorted desc by freq
        per_pos.append({
            "martin_key": mk, "original_aa": orig_aa,
            "humanized_aa": new_aa, "action": "SUBSTITUTE",
            "reason": f"FREQ_LOW: freq={freq:.3f} < threshold {freq_threshold}; "
                      f"top human aa={new_aa} (freq={list(pos_profile.values())[0]:.3f})",
            "human_freq": freq,
        })
        humanized_aa_list.append(new_aa)
        mutations.append(f"{orig_aa}{mk}{new_aa}")

    humanized_seq = "".join(humanized_aa_list)

    # ── summary ──────────────────────────────────────────────────────────────
    n_sub = len(mutations)
    n_cdr = sum(1 for p in per_pos if p["reason"].startswith("CDR"))
    n_struct = sum(1 for p in per_pos if p["reason"].startswith("STRUCT"))
    n_extra = sum(1 for p in per_pos if p["reason"].startswith("EXTRA"))

    return {
        "species": species,
        "freq_threshold": freq_threshold,
        "original_seq": "".join(r["aa"] for r in rows),
        "humanized_seq": humanized_seq,
        "n_positions_numbered": len(rows),
        "n_substituted": n_sub,
        "n_cdr_locked": n_cdr,
        "n_struct_protected": n_struct,
        "n_extra_protected": n_extra,
        "mutations": mutations,
        "per_position": per_pos,
        "algorithm_note": (
            "Sequence-only mode (no Modeller / no protinter). "
            "Structural protection uses paper-derived FR2 hallmark rules "
            "(Martin 37/45/47) instead of per-atom interaction analysis. "
            "This is conservative: real Llamanade may protect additional "
            "residues found to be structurally interacting via protinter."
        ),
    }


def print_table(result: dict) -> None:
    if "error" in result:
        print("ERROR:", result["error"])
        return
    print(f"\n{'='*72}")
    print(f"  Llamanade seq-only  |  species={result['species']}"
          f"  |  threshold={result['freq_threshold']}")
    print(f"{'='*72}")
    print(f"  Original : {result['original_seq']}")
    print(f"  Humanized: {result['humanized_seq']}")
    delta = sum(1 for a, b in zip(result['original_seq'], result['humanized_seq']) if a != b)
    print(f"  ΔAA      : {delta}  |  Substitutions: {result['n_substituted']}"
          f"  |  CDR locked: {result['n_cdr_locked']}"
          f"  |  Struct protected: {result['n_struct_protected']}")
    print(f"\n  Mutations: {', '.join(result['mutations']) or 'none'}\n")
    print(f"  {'Pos':<6} {'Orig':<5} {'Hum':<5} {'Action':<12} Reason")
    print(f"  {'-'*65}")
    for p in result["per_position"]:
        freq_str = f"{p['human_freq']:.3f}" if p["human_freq"] is not None else " —  "
        action_tag = f"[{p['action']}]"
        print(f"  {p['martin_key']:<6} {p['original_aa']:<5} {p['humanized_aa']:<5}"
              f" {action_tag:<12} {p['reason'][:55]}")
    print(f"{'='*72}")
    print(f"  Algorithm note: {result['algorithm_note'][:120]}")
    print()


def main():
    ap = argparse.ArgumentParser(
        description="Llamanade sequence-only humanization (no Modeller / no protinter)"
    )
    ap.add_argument("--fasta", "-f", required=True, help="Input FASTA (single VHH/VH sequence)")
    ap.add_argument("--species", "-s", default="alpaca",
                    choices=list(SPECIES_NOTES.keys()),
                    help="Donor species — adjusts threshold and extra protect set")
    ap.add_argument("--freq-threshold", type=float, default=None,
                    help="Override frequency threshold (default: per species)")
    ap.add_argument("--extra-protect", nargs="*", type=int, default=None,
                    help="Additional Martin positions to protect (e.g. 93 94 for bovine)")
    ap.add_argument("--out", "-o", default=None,
                    help="Write JSON result to file")
    ap.add_argument("--quiet", "-q", action="store_true",
                    help="Suppress table output (only write JSON)")
    args = ap.parse_args()

    fasta_path = Path(args.fasta)
    lines = [l.strip() for l in fasta_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    seq = "".join(l for l in lines if not l.startswith(">")).upper()

    result = humanize_seq_only(
        seq=seq,
        species=args.species,
        freq_threshold=args.freq_threshold,
        extra_protect_martin=set(args.extra_protect) if args.extra_protect else None,
    )

    if not args.quiet:
        print_table(result)

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  JSON saved → {args.out}")


if __name__ == "__main__":
    main()
