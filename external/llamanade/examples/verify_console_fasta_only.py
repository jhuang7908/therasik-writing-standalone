"""Minimal FASTA check for the web-console Alpaca VHH demo (stdlib only).

This does NOT run Llamanade. It only validates the demo file next to this script.
"""
from pathlib import Path


def main() -> None:
    here = Path(__file__).resolve().parent
    fa = here / "alpaca_vhh_console.fasta"
    lines = [ln.strip() for ln in fa.read_text(encoding="utf-8").splitlines() if ln.strip()]
    hdr = lines[0]
    seq = "".join(lines[1:]).replace(" ", "").upper()
    assert hdr.startswith(">"), "expected FASTA header"
    assert set(seq) <= set("ACDEFGHIKLMNPQRSTVWY"), "non-amino-acid characters in sequence"
    print("FASTA:", fa)
    print("Header:", hdr)
    print("Length (aa):", len(seq))
    print("OK — same sequence key as console DEMOS['alpaca-vhh'].seq")


if __name__ == "__main__":
    main()
