"""Dump raw ANARCII IMGT numbering for SP34 donor + converted."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii

SAMPLES = {
    "SP34_donor": "DIKLQSGAELARPGASVKMSCKTSGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS",
    "SP34_converted": "EVQLVESGGGLIQPGGSLRLSCAVSGYTFTRYTMSWVRQAPGKGLEWVSVINPSRGYTNYNQKFKDRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARYYDDHYSLDYWGQGTMVTVSS",
}

for name, seq in SAMPLES.items():
    print(f"\n=== {name} ===")
    rows = imgt_number_anarcii(seq)
    # Show positions 22-45 (FR1 end → CDR1 → FR2 start)
    print("pos | ins | aa | region(approx)")
    for r in rows:
        pos = r.get("pos")
        if not isinstance(pos, int):
            continue
        if 22 <= pos <= 45:
            ins = r.get("ins_code") or " "
            aa = r.get("aa")
            region = "FR1" if pos <= 26 else ("CDR1" if pos <= 38 else "FR2")
            print(f" {pos:3d} | '{ins}' | {aa} | {region}")
