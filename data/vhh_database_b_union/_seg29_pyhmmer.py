"""
VHH-29 CDR segmentation using pyhmmer directly.
Bypasses the broken hmmscan subprocess in anarci.
"""
import json, csv, os, sys
from pathlib import Path

import pyhmmer
from pyhmmer.plan7 import HMMFile

# -- anarci internal references we need --
import importlib, sys
_aa_module = importlib.import_module('anarci.anarci')
all_reference_states = list(range(1, 129))  # IMGT reference states
get_hmm_length = _aa_module.get_hmm_length
number_sequence_from_alignment = _aa_module.number_sequence_from_alignment

root = Path(r'd:/InSynBio-AI-Research/Antibody_Engineer_Suite')
HMM = Path(_aa_module.HMM_path) / 'ALL.hmm'


def pyhmmer_domain_to_state_vector(domain, seq_len, order=0, n_domains=1):
    """Convert pyhmmer Domain alignment to anarci state vector format."""
    aln = domain.alignment
    hmm_seq = aln.hmm_sequence
    pp_str = aln.posterior_probabilities

    # RF derivation: '.' in hmm_sequence = insert column, else match/delete 'x'
    rf_str = ''.join('.' if c == '.' else 'x' for c in hmm_seq)

    hmm_start = aln.hmm_from - 1   # 0-indexed
    hmm_end = aln.hmm_to            # exclusive (same convention as BioPython)
    seq_start = aln.target_from - 1  # 0-indexed
    seq_end = aln.target_to           # exclusive

    hit_name = str(aln.hmm_name.decode() if isinstance(aln.hmm_name, bytes) else aln.hmm_name)
    species, ctype = hit_name.split('_')
    hmm_length = get_hmm_length(species, ctype)

    # N-terminal extension (same logic as _hmm_alignment_to_states)
    if order == 0 and hmm_start and hmm_start < 5:
        n_ext = hmm_start
        if hmm_start > seq_start:
            n_ext = min(seq_start, hmm_start - seq_start)
        pp_str = '8' * n_ext + pp_str
        rf_str = 'x' * n_ext + rf_str
        seq_start -= n_ext
        hmm_start -= n_ext

    # C-terminal extension for single domain
    if n_domains == 1 and seq_end < seq_len and (123 < hmm_end < hmm_length):
        n_ext = min(hmm_length - hmm_end, seq_len - seq_end)
        pp_str = pp_str + '8' * n_ext
        rf_str = rf_str + 'x' * n_ext
        seq_end += n_ext
        hmm_end += n_ext

    hmm_states = all_reference_states[hmm_start:hmm_end]
    seq_indices = list(range(seq_start, seq_end))

    h, s = 0, 0
    state_vector = []
    for i in range(len(pp_str)):
        if rf_str[i] == 'x':
            state_type = 'm'
        else:
            state_type = 'i'

        if pp_str[i] == '.':
            state_type = 'd'
            seq_idx = None
        else:
            if s < len(seq_indices):
                seq_idx = seq_indices[s]
            else:
                seq_idx = None

        if h < len(hmm_states):
            state_vector.append(((hmm_states[h], state_type), seq_idx))
        else:
            state_vector.append(((None, state_type), seq_idx))

        if state_type == 'm':
            h += 1
            s += 1
        elif state_type == 'i':
            s += 1
        else:
            h += 1

    return state_vector, species, ctype


def number_vhh(seq_id, seq, bit_score_threshold=80):
    """Number a VHH sequence using pyhmmer + anarci IMGT numbering."""
    alphabet = pyhmmer.easel.Alphabet.amino()
    seq_block = pyhmmer.easel.TextSequenceBlock([
        pyhmmer.easel.TextSequence(name=seq_id.encode(), sequence=seq.encode())
    ]).digitize(alphabet)

    with HMMFile(str(HMM)) as hmm_file:
        all_hits = list(pyhmmer.hmmer.hmmscan(seq_block, hmm_file, cpus=1))

    if not all_hits:
        return None, None

    top_hits = all_hits[0]  # One TopHits per query sequence
    # Filter by score threshold and take best hit per domain
    domains_by_score = []
    for hit in top_hits:
        if hit.score >= bit_score_threshold:
            domains_by_score.append((hit.score, hit.best_domain))

    if not domains_by_score:
        return None, None

    # Sort by score, take best hit
    domains_by_score.sort(reverse=True)
    best_domain = domains_by_score[0][1]

    try:
        state_vector, species, ctype = pyhmmer_domain_to_state_vector(
            best_domain, len(seq), order=0, n_domains=1
        )
    except Exception as e:
        print(f'    state_vector error for {seq_id}: {e}', flush=True)
        return None, None

    try:
        result = number_sequence_from_alignment(state_vector, seq, scheme='imgt', chain_type=ctype)
        # Returns (numbered_list, startindex, endindex)
        numbered_list = result[0]
        return numbered_list, (species, ctype)
    except Exception as e:
        print(f'    numbering error for {seq_id}: {e}', flush=True)
        return None, None


IMGT_CDR1 = (27, 38)
IMGT_CDR2 = (56, 65)
IMGT_CDR3 = (105, 117)


def extract_cdrs(numbering):
    """Extract CDR sequences from IMGT numbered sequence."""
    def extract(lo, hi):
        return ''.join(
            aa for (pos, ins), aa in numbering
            if lo <= pos <= hi and aa not in ('-', 'X', '*')
        )
    return extract(*IMGT_CDR1), extract(*IMGT_CDR2), extract(*IMGT_CDR3)


# --- Main ---
seqs_data = json.load(open(root / 'data/vhh_database_b_union/database_b_sequences.json'))
entries = seqs_data['entries']
print(f'Processing {len(entries)} sequences...', flush=True)

results = []
for e in entries:
    sid = e['safe_id']
    seq = e['sequence']
    try:
        numbering, info = number_vhh(sid, seq)
        if numbering:
            cdr1, cdr2, cdr3 = extract_cdrs(numbering)
            r = {'safe_id': sid, 'CDR1': cdr1, 'CDR2': cdr2, 'CDR3': cdr3}
            results.append(r)
            print(f'  OK {sid} ({info[0]}_{info[1]}): CDR3={cdr3} (len={len(cdr3)})', flush=True)
        else:
            print(f'  SKIP {sid}: no numbering', flush=True)
    except Exception as ex:
        import traceback
        print(f'  ERROR {sid}: {ex}', flush=True)
        traceback.print_exc()

outpath = root / 'data/vhh_database_b_union/vhh29_cdr_segments.csv'
with open(outpath, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['safe_id', 'CDR1', 'CDR2', 'CDR3'])
    w.writeheader()
    w.writerows(results)

print(f'\nDone. Saved {len(results)}/{len(entries)} rows to {outpath}', flush=True)
