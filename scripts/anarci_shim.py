"""
anarci_shim.py

A compatibility shim that makes 'anarcii' look like 'anarci'.
Useful for tools like ImmuneBuilder that depend on the legacy 'anarci' package.

Usage:
    import scripts.anarci_shim
    import anarci  # This will now import the shimmed module backed by anarcii
    from ImmuneBuilder import ABodyBuilder2

"""

import sys
import types
from typing import List, Tuple, Dict, Any

try:
    from anarcii import Anarcii
except ImportError:
    raise ImportError("anarci_shim requires 'anarcii' to be installed.")

def legacy_anarci(sequences: List[Tuple[str, str]], scheme: str = "imgt", **kwargs) -> Tuple[List, List, List]:
    """
    Mimics anarci.anarci() return format for callers like abnativ / ImmuneBuilder.

    Real anarci.anarci([(id, seq)], scheme=...) returns a 3-tuple:
        (
          [  # per input sequence
            [  # chains found (list of 1 for a single-domain VH/VHH)
              (numbering_list, query_start, query_end)  # per chain
            ]
          ],
          [  # per input sequence
            [  # chains found
              {"chain_type": "H", "id": ..., "query_start": int, "query_end": int,
               "species": ..., "scheme": ..., "bitscore": ..., "evalue": ...,
               "bias": ..., "description": ""}
            ]
          ],
          [  # per input sequence
            [[header_row], [data_row], ...]  # HMM hit table
          ]
        )

    numbering_list is a list of ((pos, ins_code), aa) 2-tuples.
    """
    scheme_map = {
        'm': 'martin', 'martin': 'martin',
        'k': 'kabat', 'kabat': 'kabat',
        'c': 'chothia', 'chothia': 'chothia',
        'i': 'imgt', 'imgt': 'imgt',
        'a': 'aho', 'aho': 'aho'
    }
    canonical_scheme = scheme_map.get(scheme.lower(), scheme)

    engine = Anarcii()
    # Anarcii.number() does NOT accept a 'scheme' kwarg; use .to_scheme() after numbering.
    engine.number(sequences)
    results_raw = engine.to_scheme(canonical_scheme)

    per_seq_chains: List = []   # index [0]
    per_seq_details: List = []  # index [1]
    per_seq_hits: List = []     # index [2]

    for seq_id, seq in sequences:
        res = results_raw.get(seq_id)

        if res and res.get("numbering"):
            chain_type = res.get("chain_type", "H")
            raw_numbering = res["numbering"]

            # Build 2-tuple numbering list: ((pos, ins), aa)
            # Anarcii items are ((pos, ins), aa[, region_idx]) – keep only first two.
            numbering_list = [(item[0], item[1]) for item in raw_numbering]

            query_start = 0
            query_end = len(numbering_list)

            chain_tuple = (numbering_list, query_start, query_end)
            chain_dict = {
                "chain_type": chain_type,
                "id": seq_id,
                "query_start": query_start,
                "query_end": query_end,
                "species": res.get("species", "human"),
                "scheme": canonical_scheme,
                "bitscore": 200.0,
                "evalue": 1e-60,
                "bias": 0.0,
                "description": "",
            }
            # Minimal HMM hit table: header row + one data row
            hit_header = ["id", "description", "evalue", "bitscore", "bias",
                          "query_start", "query_end"]
            hit_row = [seq_id, "", 1e-60, 200.0, 0.0, query_start, query_end]

            per_seq_chains.append([[chain_tuple]])
            per_seq_details.append([[chain_dict]])
            per_seq_hits.append([[hit_header, hit_row]])
        else:
            per_seq_chains.append([None])
            per_seq_details.append([None])
            per_seq_hits.append([[]])

    # Flatten outer wrapper to match anarci.anarci() convention:
    # return[0] = list-per-sequence of chains-list
    # return[1] = list-per-sequence of details-list
    # return[2] = list-per-sequence of hit-table-list
    return (
        [entry[0] for entry in per_seq_chains],
        [entry[0] for entry in per_seq_details],
        [entry[0] for entry in per_seq_hits],
    )

def install_shim():
    """
    Installs the anarci shim into sys.modules.
    Call this before importing any library that depends on 'anarci'.
    """
    if "anarci" in sys.modules:
        # If it's already our shim, do nothing.
        if hasattr(sys.modules["anarci"], "anarci") and sys.modules["anarci"].anarci == legacy_anarci:
            return
        # If it's real anarci, we might want to override it? 
        # But here we assume real anarci is missing.
        
    m = types.ModuleType("anarci")
    m.anarci = legacy_anarci
    
    # Mock other functions/constants ImmuneBuilder might check
    m.validate_sequence = lambda x: True
    m.scheme_short_to_long = {
        'imgt': 'imgt', 'kabat': 'kabat', 'chothia': 'chothia', 'aho': 'aho', 'martin': 'martin',
        'i': 'imgt', 'k': 'kabat', 'c': 'chothia', 'a': 'aho', 'm': 'martin'
    }
    
    sys.modules["anarci"] = m
    # print("Injecting ANARCI shim (backed by ANARCII)...", file=sys.stderr)

# Auto-install on import? 
# Better to let user call install_shim() or just doing it if they import this module explicitly.
# Since the user will "import scripts.anarci_shim", we can auto-install.
install_shim()
