import sys
from pathlib import Path

# Add root to sys.path to allow importing from scripts
SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from scripts.build_cat_production_germline_library_v2 import (
    simple_developability,
    tier_from_metrics,
    cmc_rank_key,
)
from core.cmc.generic_cmc_scanner import scan_cmc_liabilities

def test_tier_from_metrics():
    # Tier 1: flags <= 4, pI in 5.5-9.0, instability < 55
    assert tier_from_metrics(flags=3, p_i=6.5, instability=40.0) == "tier1"
    
    # Tier 2: flags <= 8, pI in 4.8-9.5, instability < 70
    assert tier_from_metrics(flags=5, p_i=6.5, instability=40.0) == "tier2"  # flags > 4
    assert tier_from_metrics(flags=3, p_i=4.9, instability=40.0) == "tier2"  # pI < 5.5
    assert tier_from_metrics(flags=3, p_i=6.5, instability=60.0) == "tier2"  # instability > 55
    
    # Tier 3: fails tier 2
    assert tier_from_metrics(flags=9, p_i=6.5, instability=40.0) == "tier3"  # flags > 8
    assert tier_from_metrics(flags=3, p_i=4.0, instability=40.0) == "tier3"  # pI < 4.8
    assert tier_from_metrics(flags=3, p_i=6.5, instability=80.0) == "tier3"  # instability > 70


def test_cmc_rank_key():
    # Key format: (total_flags, instability_index, pI_penalty, gene)
    
    row_best = {
        "cmc_full": {"summary": {"total_flags": 1}},
        "developability": {"instability_index": 30.0, "pI": 7.5},
        "gene": "A"
    }
    
    row_more_flags = {
        "cmc_full": {"summary": {"total_flags": 3}},
        "developability": {"instability_index": 30.0, "pI": 7.5},
        "gene": "B"
    }
    
    row_worse_instability = {
        "cmc_full": {"summary": {"total_flags": 1}},
        "developability": {"instability_index": 40.0, "pI": 7.5},
        "gene": "C"
    }
    
    row_worse_pi = {
        "cmc_full": {"summary": {"total_flags": 1}},
        "developability": {"instability_index": 30.0, "pI": 9.0}, # penalty = min(|9-7.5|, |9-8.0|) = 1.0
        "gene": "D"
    }
    
    key_best = cmc_rank_key(row_best)
    key_flags = cmc_rank_key(row_more_flags)
    key_inst = cmc_rank_key(row_worse_instability)
    key_pi = cmc_rank_key(row_worse_pi)
    
    # Flags is primary sort
    assert key_best < key_flags
    # Instability is secondary
    assert key_best < key_inst
    # pI penalty is tertiary
    assert key_best < key_pi
    
    print("cmc_rank_key test passed!")


def test_developability_scoring():
    # A dummy sequence
    seq = "EVQLVESGGDLVKPGGSLRLTCVASGFTFSSYDMNWVRQAPGKGLQWVAYISSGGSSTYYADAVKGRFTISRDNAKNTLYLQMNSLRAEDTAMYYCAG"
    
    dev = simple_developability(seq)
    assert "pI" in dev
    assert "instability_index" in dev
    assert "gravy" in dev
    assert dev["length"] == len(seq)
    
    cmc = scan_cmc_liabilities(seq)
    assert "summary" in cmc
    assert "total_flags" in cmc["summary"]
    
    print(f"Developability test passed! pI: {dev['pI']}, instability: {dev['instability_index']}, flags: {cmc['summary']['total_flags']}")


if __name__ == "__main__":
    test_tier_from_metrics()
    test_cmc_rank_key()
    test_developability_scoring()
    print("All petization CMC scoring tests passed successfully.")
