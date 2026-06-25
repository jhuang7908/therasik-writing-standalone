import json, glob, math

base = "C:/Users/NextVivo/Downloads/cf_result_1n8z/muMAb4D5_VHH_VGRW_SR_R2HER2_DomainIV_26db0/muMAb4D5_VHH_VGRW_SR_R2HER2_DomainIV_26db0"

print("=== ColabFold Multimer Scores (all 10 models) ===")
print("%-5s %-8s %-8s %-12s %-30s" % ("Rank", "iptm", "ptm", "rank_conf", "model"))

all_scores = []
for rank in range(1, 11):
    files = glob.glob(base + "_scores_rank_%03d_*.json" % rank)
    if files:
        with open(files[0]) as f:
            d = json.load(f)
        fname = files[0]
        model_str = fname.split("alphafold2_multimer_v3_")[-1].replace(".json","")
        iptm = d.get("iptm", 0)
        ptm  = d.get("ptm", 0)
        rc   = d.get("ranking_confidence", 0)
        all_scores.append((rank, iptm, ptm, rc, model_str))
        print("%-5d %-8.3f %-8.3f %-12.3f %-30s" % (rank, iptm, ptm, rc, model_str))

print()
best_rank, best_iptm, best_ptm, best_rc, best_model = all_scores[0]
print("Best model: rank %d, iptm=%.3f, ptm=%.3f, ranking_confidence=%.3f" % (
    best_rank, best_iptm, best_ptm, best_rc))
print()

# Threshold interpretation
print("=== ipTM Interpretation ===")
if best_iptm >= 0.8:
    print("ipTM >= 0.8: HIGH CONFIDENCE binding interface")
elif best_iptm >= 0.6:
    print("ipTM 0.6-0.8: MEDIUM confidence, plausible binding pose")
elif best_iptm >= 0.4:
    print("ipTM 0.4-0.6: LOW confidence, uncertain binding")
else:
    print("ipTM < 0.4: NO CONFIDENT INTERFACE — AF2 does not predict binding")

print()

# PAE cross-chain analysis from best model
best_score_file = glob.glob(base + "_scores_rank_001_*.json")[0]
with open(best_score_file) as f:
    best = json.load(f)

plddt = best.get("plddt", [])
n_total = len(plddt)
n_vhh = 120
n_her2 = n_total - n_vhh

print("=== pLDDT ===")
print("Total residues in model: %d (VHH: %d + HER2-DomIV: %d)" % (n_total, n_vhh, n_her2))
if plddt:
    vhh_plddt = plddt[:n_vhh]
    her2_plddt = plddt[n_vhh:]
    print("VHH pLDDT:      mean=%.1f  min=%.1f  max=%.1f" % (
        sum(vhh_plddt)/len(vhh_plddt), min(vhh_plddt), max(vhh_plddt)))
    print("HER2-DomIV pLDDT: mean=%.1f  min=%.1f  max=%.1f" % (
        sum(her2_plddt)/len(her2_plddt), min(her2_plddt), max(her2_plddt)))

# PAE
pae_file = base + "_predicted_aligned_error_v1.json"
with open(pae_file) as f:
    pae_data = json.load(f)

pae = pae_data.get("predicted_aligned_error", [])
print()
print("=== PAE Cross-chain Analysis ===")
if pae:
    cross_1 = [pae[i][j] for i in range(n_vhh) for j in range(n_vhh, n_total)]
    cross_2 = [pae[i][j] for i in range(n_vhh, n_total) for j in range(n_vhh)]
    c1_mean = sum(cross_1)/len(cross_1)
    c2_mean = sum(cross_2)/len(cross_2)
    cross_mean = (c1_mean + c2_mean) / 2

    print("PAE VHH -> HER2: mean=%.1f A" % c1_mean)
    print("PAE HER2 -> VHH: mean=%.1f A" % c2_mean)
    print("Mean cross-chain PAE: %.1f A" % cross_mean)
    print()

    # Find min PAE region (likely the true interface if any)
    min_pae = min(cross_1 + cross_2)
    print("Min cross-chain PAE: %.1f A" % min_pae)

    # Interface residues with PAE < 10
    interface_vhh = set()
    interface_her2 = set()
    for i in range(n_vhh):
        for j in range(n_vhh, n_total):
            if pae[i][j] < 10:
                interface_vhh.add(i+1)
                interface_her2.add(j-n_vhh+1)
    print("VHH residues with cross-PAE < 10A:", sorted(interface_vhh) if interface_vhh else "NONE")
    print("HER2 residues with cross-PAE < 10A:", sorted(interface_her2) if interface_her2 else "NONE")

    print()
    print("=== DIAGNOSIS ===")
    if best_iptm < 0.4 and cross_mean > 20:
        print("CONCLUSION: AF2 predicts the VHH and HER2 DomainIV are NOT confidently bound.")
        print("Two chains are placed independently without a confident interface.")
        print()
        print("LIKELY CAUSES:")
        print("1. VHH CDR sequences have no AF2 training co-complex data (novel engineering)")
        print("2. HER2 DomainIV (141 aa) isolated fragment may lack context for AF2 docking")
        print("3. The VHH (derived from VH) lacks co-evolutionary signal with HER2 in the AF2 MSA")
        print()
        print("RECOMMENDATION:")
        print("  Use full HER2 ECD (aa 23-627) instead of isolated Domain IV for better AF2 context")
        print("  Or use template-based docking with 1N8Z as starting template")
    elif best_iptm >= 0.6:
        print("CONCLUSION: AF2 predicts a plausible binding interface.")
    else:
        print("CONCLUSION: Low confidence — see ipTM and PAE values above.")

# Also print CSV summary if available
csv_file = base + ".csv"
try:
    with open(csv_file) as f:
        print()
        print("=== CSV Summary ===")
        print(f.read())
except:
    pass
