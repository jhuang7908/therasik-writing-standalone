import json, pathlib, sys

BASE = pathlib.Path("projects/fgf 23/vam_boltz_scan/FGF23")

# Ala scan
ala_path = BASE / "stage2_ala_scan/stage2_ala_scan.json"
if ala_path.is_file():
    ala = json.loads(ala_path.read_text())
    m = ala["_meta"]
    print("=== STAGE 2: ALA SCAN ===")
    print(f"  n_scored : {m['n_scored']}  errors={m['n_errors']}")
    print(f"  WT dG    : {m['wt_evoef2_dg']}")
    print(f"  top_cdr  : {m['top_cdr_for_saturation']}")
    print("  CDR loop ranking:")
    for x in ala["locus_summary"]:
        print(f"    #{x['rank_by_binding_impact']} {x['locus']:<14} "
              f"hotspots={x['n_hotspot_ddg_gt_1']}  "
              f"sum_ddg+={x['sum_positive_ddg']:.3f}  "
              f"max_ddg={x['max_ddg']:.3f}")
else:
    print("Ala scan: NOT YET")

print()

# Saturation
sat_path = BASE / "stage3_saturation/stage3_saturation.json"
if sat_path.is_file():
    sat = json.loads(sat_path.read_text())
    print("=== STAGE 3: SATURATION ===")
    print(f"  loops     : {sat['loops']}")
    print(f"  n_total   : {sat['n_total']}")
    print(f"  n_beneficial (ddg<=-0.5): {sat['n_beneficial']}")
    if sat["beneficial"]:
        print("  Top beneficial mutations:")
        for b in sat["beneficial"][:10]:
            print(f"    {b['variant']:<12} ddg={b['evoef2_ddg']:+.3f}  {b['locus']}")
    else:
        print("  *** No beneficial mutations found ***")
else:
    print("Saturation: NOT YET")
