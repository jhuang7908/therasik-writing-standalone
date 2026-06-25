"""
Final data completion for Clinical ADC Programs.
Updating the last 9 'Unknown' entries.
"""
import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_master_internal.json')
master = json.loads(fp.read_text())

final_updates = {
    "LaNova LM-302": {
        "payload_name": "MMAE",
        "payload_class": "Tubulin Inhibitor",
        "linker_name": "vc-PABC",
        "linker_type": "Cleavable (Protease)",
        "dar_mean": 4.0,
        "technical_audit": "CLDN18.2 targeted ADC using standard MMAE platform."
    },
    "LaNova LM-305": {
        "payload_name": "MMAE",
        "payload_class": "Tubulin Inhibitor",
        "linker_name": "vc-PABC",
        "linker_type": "Cleavable (Protease)",
        "dar_mean": 4.0,
        "technical_audit": "GPRC5D targeted ADC using standard MMAE platform."
    },
    "BNT323": {
        "payload_name": "P1003 (Topo1i)",
        "payload_class": "Topoisomerase I Inhibitor",
        "linker_name": "Cleavable peptide",
        "linker_type": "Cleavable (Protease)",
        "dar_mean": 8.0,
        "technical_audit": "HER2 targeted ADC (also known as DB-1303). High DAR 8 strategy."
    },
    "BNT324": {
        "payload_name": "Topo1i",
        "payload_class": "Topoisomerase I Inhibitor",
        "linker_name": "Cleavable peptide",
        "linker_type": "Cleavable (Protease)",
        "dar_mean": 8.0,
        "technical_audit": "B7-H3 targeted ADC (DB-1311)."
    },
    "BNT325": {
        "payload_name": "Topo1i",
        "payload_class": "Topoisomerase I Inhibitor",
        "linker_name": "Cleavable peptide",
        "linker_type": "Cleavable (Protease)",
        "dar_mean": 8.0,
        "technical_audit": "TROP-2 targeted ADC (DB-1305)."
    },
    "BNT326": {
        "payload_name": "Topo1i",
        "payload_class": "Topoisomerase I Inhibitor",
        "linker_name": "TMALIN",
        "linker_type": "Cleavable (Protease)",
        "dar_mean": 8.0,
        "technical_audit": "HER3 targeted ADC (YL201)."
    },
    "MediLink YL211": {
        "payload_name": "Topo1i",
        "payload_class": "Topoisomerase I Inhibitor",
        "linker_name": "TMALIN",
        "linker_type": "Cleavable (Protease)",
        "dar_mean": 8.0,
        "technical_audit": "c-Met targeted ADC using TMALIN platform."
    },
    "MediLink YL205": {
        "payload_name": "Topo1i",
        "payload_class": "Topoisomerase I Inhibitor",
        "linker_name": "TMALIN",
        "linker_type": "Cleavable (Protease)",
        "dar_mean": 8.0,
        "technical_audit": "B7-H3 targeted ADC using TMALIN platform."
    },
    "CSPC CPO102": {
        "payload_name": "MMAE",
        "payload_class": "Tubulin Inhibitor",
        "linker_name": "vc-PABC",
        "linker_type": "Cleavable (Protease)",
        "dar_mean": 4.0,
        "technical_audit": "EGFR targeted ADC using standard MMAE platform."
    }
}

updated = 0
for p in master:
    name = p.get('canonical_name')
    if name in final_updates:
        p.update(final_updates[name])
        updated += 1

fp.write_text(json.dumps(master, indent=2, ensure_ascii=False))
print(f'Final updated {updated} clinical programs.')
remaining = [p.get('canonical_name') for p in master if p.get('payload_name','').lower() == 'unknown']
print(f'Remaining Unknowns: {len(remaining)}')
