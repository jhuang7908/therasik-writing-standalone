"""
Fix human VH: remove 'X' entries from Llamanade NGS profile and re-normalize.
Run: python scripts/fix_human_vh_x_filter.py
"""
import json
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
VH_FILE = REPO / "data/reference/human_replacement_profiles/v1/human_ighv_aa_freq_llamanade_ngs_v1.json"
AA_ORDER = "ACDEFGHIKLMNPQRSTVWY"

def norm(d: dict) -> dict:
    filtered = {aa: v for aa, v in d.items() if aa in AA_ORDER and v > 0}
    tot = sum(filtered.values())
    if not tot:
        return {}
    return {aa: round(filtered[aa] / tot, 6) for aa in AA_ORDER if aa in filtered}

data = json.loads(VH_FILE.read_text())
positions = data["positions"]

n_had_x = sum(1 for p in positions.values() if "X" in p)
cleaned = {pos: norm(freqs) for pos, freqs in positions.items()}
cleaned = {pos: d for pos, d in cleaned.items() if d}  # drop all-zero

data["positions"] = cleaned
data["metadata"]["x_filter_applied"] = f"X removed and renormalized at {datetime.now(timezone.utc).isoformat()}"
data["metadata"]["n_positions_had_X"] = n_had_x
data["metadata"]["n_positions_after_filter"] = len(cleaned)

VH_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
print(f"Done: {n_had_x} positions had X, renormalized. {len(cleaned)} positions remaining.")

# Quick sanity check
for pos, freqs in list(cleaned.items())[:5]:
    s = round(sum(freqs.values()), 4)
    print(f"  pos{pos}: sum={s}  dom={max(freqs, key=freqs.get)}({max(freqs.values()):.3f})")
