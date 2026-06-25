"""
4B12 VH/VL Humanization Analysis
Step 1-4: Segmentation, germline attribution, Vernier zone, human framework candidates
"""
import os
from anarcii import Anarcii

BASE = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\germlines"

VH_SEQ = "QVQLKQSRPGLVAPSQSLSITCTVSGFSLTNYGVHWVRQPPGKGLEWVGMIWAGGRTNYNSALMSRLSISKDNSKSQVFLKMNSLQIDDTAIYYCAREDEGYYALDYWGQGTSVTVSS"
VL_SEQ = "DILMTQSSSYLSVSLGGRVTITCKASDHINNWLAWYQQKPGNAPRLLISGATSLETGVPSRFSGSGSGKDYTLSITSLQTEDIATYYCHQYWITPYTFGGGTRLEIK"

IMGT_REGIONS = {
    "FR1": (1, 26), "CDR1": (27, 38), "FR2": (39, 55),
    "CDR2": (56, 65), "FR3": (66, 104), "CDR3": (105, 117), "FR4": (118, 130),
}

# Vernier zone positions (IMGT numbering, from our 458-structure correlation report)
VH_VERNIER = {
    "T1": [71],
    "T2": [2, 27, 28, 29, 30, 69, 93, 94],
    "T3": [48, 49, 67, 73, 78],
}
VL_VERNIER = {
    "T1": [71],
    "T2": [36, 46],
    "T3": [2, 4, 49, 69, 98],
}


def load_fasta(path):
    seqs = {}
    name, buf = None, []
    if not os.path.exists(path):
        return seqs
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith(">"):
                if name:
                    seqs[name] = "".join(buf)
                parts = line[1:].split("|")
                name = parts[1] if len(parts) > 1 else line[1:]
                buf = []
            else:
                buf.append(line)
    if name:
        seqs[name] = "".join(buf)
    return seqs


def pct_id(s1, s2):
    n = min(len(s1), len(s2))
    if n == 0:
        return 0.0
    return sum(a == b for a, b in zip(s1, s2)) / max(len(s1), len(s2)) * 100


def top_matches(query, gls, n=5):
    sc = [(pct_id(query, ref[: len(query) + 5]), k, ref) for k, ref in gls.items()]
    return sorted(sc, reverse=True)[:n]


def number_seq(engine, seq, label="seq"):
    res = engine.number([(label, seq)])
    info = res[label]
    pos_map = {pos: aa for (pos, ins), aa in info["numbering"] if aa != "-"}
    regions = {}
    for reg, (lo, hi) in IMGT_REGIONS.items():
        regions[reg] = "".join(
            aa for (pos, _), aa in info["numbering"] if lo <= pos <= hi and aa != "-"
        )
    return pos_map, info["chain_type"], regions


def analyze_chain(engine, seq, label, vernier_tiers, germline_V_db, germline_J_db,
                  hu_V_db, hu_J_db, v_region_seq):
    pos_map, chain_type, regions = number_seq(engine, seq, label)

    print(f"\n{'='*70}")
    print(f"  {label}  (chain: {chain_type})")
    print(f"{'='*70}")
    for reg in ("FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"):
        s = regions[reg]
        print(f"  {reg:5s} ({len(s):2d} aa): {s}")

    # --- Germline attribution ---
    mu_top = top_matches(v_region_seq, germline_V_db, 3)
    print(f"\n[Mouse germline V-gene attribution]")
    for pct, name, seq_ in mu_top:
        print(f"  {name}: {pct:.1f}%")
    mu_name, mu_seq = mu_top[0][1], mu_top[0][2]

    # Number mouse germline
    try:
        mu_pos_map, _, _ = number_seq(engine, mu_seq, "mu_gl")
    except Exception:
        mu_pos_map = {}

    # --- Human framework candidates ---
    hu_top = top_matches(v_region_seq, hu_V_db, 5)
    print(f"\n[Human V-gene candidates]")
    for pct, name, seq_ in hu_top:
        print(f"  {name}: {pct:.1f}%")
    hu_name, hu_seq = hu_top[0][1], hu_top[0][2]
    try:
        hu_pos_map, _, _ = number_seq(engine, hu_seq, "hu_gl")
    except Exception:
        hu_pos_map = {}

    # J-gene FR4 match
    fr4 = regions["FR4"]
    hu_j_top = top_matches(fr4, hu_J_db, 3)
    print(f"\n[Human J-gene candidates (FR4 match: {fr4})]")
    for pct, name, seq_ in hu_j_top:
        print(f"  {name}: {pct:.1f}%  seq={seq_}")

    # --- Vernier zone table ---
    all_vpos = sorted(set(p for t in vernier_tiers.values() for p in t))
    print(f"\n[Vernier Zone Analysis]")
    print(f"  {'Pos':>4}  {'4B12':>5}  {'MouseGL':>8}  {'BestHuman':>10}  {'SHM':>4}  Tier  Decision")
    print("  " + "-" * 72)
    for pos in all_vpos:
        tier = next(t for t, ps in vernier_tiers.items() if pos in ps)
        ab_aa = pos_map.get(pos, "-")
        mu_aa = mu_pos_map.get(pos, "?")
        hu_aa = hu_pos_map.get(pos, "?")
        is_shm = ab_aa != mu_aa and mu_aa not in ["?", "-"]
        shm_flag = "SHM" if is_shm else ""

        if ab_aa == "-":
            decision = "ABSENT in sequence"
        elif ab_aa == hu_aa:
            decision = "OK - matches human"
        elif ab_aa == mu_aa and ab_aa != hu_aa:
            decision = ">> BACK-MUT candidate (germline, non-human)"
        elif is_shm and ab_aa != hu_aa:
            decision = "REVIEW - SHM, differs from both"
        elif is_shm and ab_aa == hu_aa:
            decision = "OK - SHM converged to human"
        else:
            decision = "CHECK"

        print(f"  {pos:>4}  {ab_aa:>5}  {mu_aa:>8}  {hu_aa:>10}  {shm_flag:>4}  {tier}  {decision}")

    # --- SHM in framework regions ---
    fr_positions = []
    for reg in ("FR1", "FR2", "FR3"):
        lo, hi = IMGT_REGIONS[reg]
        fr_positions.extend(range(lo, hi + 1))

    print(f"\n[Framework SHM positions (differences from mouse germline)]")
    shm_count = 0
    for pos in fr_positions:
        ab_aa = pos_map.get(pos, "-")
        mu_aa = mu_pos_map.get(pos, "-")
        hu_aa = hu_pos_map.get(pos, "-")
        if ab_aa != "-" and mu_aa not in ["-", "?"] and ab_aa != mu_aa:
            note = "(human)" if ab_aa == hu_aa else "(non-human SHM)"
            print(f"  pos {pos:3d}: 4B12={ab_aa}  MouseGL={mu_aa}  Human={hu_aa}  {note}")
            shm_count += 1
    if shm_count == 0:
        print("  None found - sequence matches germline in framework regions")

    # CDR lengths summary
    print(f"\n[CDR lengths (IMGT)]")
    for reg in ("CDR1", "CDR2", "CDR3"):
        print(f"  {reg}: {len(regions[reg])} aa  -> {regions[reg]}")

    return pos_map, regions, mu_name, hu_name, mu_pos_map, hu_pos_map


# ── MAIN ──────────────────────────────────────────────────────────────────
engine = Anarcii()

print("Loading germline databases...")
mu_IGHV = load_fasta(os.path.join(BASE, "mus_musculus_ig_aa", "IGHV_aa.fasta"))
mu_IGKV = load_fasta(os.path.join(BASE, "mus_musculus_ig_aa", "IGKV_aa.fasta"))
mu_IGHJ = load_fasta(os.path.join(BASE, "mus_musculus_ig_aa", "IGHJ_aa.fasta"))
mu_IGKJ = load_fasta(os.path.join(BASE, "mus_musculus_ig_aa", "IGKJ_aa.fasta"))
hu_IGHV = load_fasta(os.path.join(BASE, "human_ig_aa", "IGHV_aa.fasta"))
hu_IGKV = load_fasta(os.path.join(BASE, "human_ig_aa", "IGKV_aa.fasta"))
hu_IGHJ = load_fasta(os.path.join(BASE, "human_ig_aa", "IGHJ_aa.fasta"))
hu_IGKJ = load_fasta(os.path.join(BASE, "human_ig_aa", "IGKJ_aa.fasta"))
print("Done.\n")

# V-region only (up to conserved C at IMGT pos 104)
VH_V = "QVQLKQSRPGLVAPSQSLSITCTVSGFSLTNYGVHWVRQPPGKGLEWVGMIWAGGRTNYNSALMSRLSISKDNSKSQVFLKMNSLQIDDTAIYYC"
VL_V = "DILMTQSSSYLSVSLGGRVTITCKASDHINNWLAWYQQKPGNAPRLLISGATSLETGVPSRFSGSGSGKDYTLSITSLQTEDIATYYC"

print("\n" + "#" * 70)
print("  4B12 HUMANIZATION ANALYSIS")
print("#" * 70)

vh_data = analyze_chain(engine, VH_SEQ, "4B12_VH", VH_VERNIER,
                        mu_IGHV, mu_IGHJ, hu_IGHV, hu_IGHJ, VH_V)

vl_data = analyze_chain(engine, VL_SEQ, "4B12_VL", VL_VERNIER,
                        mu_IGKV, mu_IGKJ, hu_IGKV, hu_IGKJ, VL_V)

print("\n" + "=" * 70)
print("SUMMARY FOR HUMAN REVIEW")
print("=" * 70)
vh_pos_map, vh_regions, vh_mu, vh_hu, vh_mu_map, vh_hu_map = vh_data
vl_pos_map, vl_regions, vl_mu, vl_hu, vl_mu_map, vl_hu_map = vl_data

print(f"\nVH: mouse germline = {vh_mu}")
print(f"VH: best human template = {vh_hu}")
print(f"VL: mouse germline = {vl_mu}")
print(f"VL: best human template = {vl_hu}")

print("\nVH CDRs to graft:")
for r in ("CDR1", "CDR2", "CDR3"):
    print(f"  {r}: {vh_regions[r]}  ({len(vh_regions[r])} aa)")

print("\nVL CDRs to graft:")
for r in ("CDR1", "CDR2", "CDR3"):
    print(f"  {r}: {vl_regions[r]}  ({len(vl_regions[r])} aa)")

print("\n[NEXT STEP] Please review Vernier zone back-mutation candidates above,")
print("then confirm human framework choice before proceeding to sequence assembly.")
