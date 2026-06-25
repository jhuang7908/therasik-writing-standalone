"""Explore pyhmmer hit alignment attributes to extract IMGT state vectors."""
import pyhmmer, os
from pyhmmer.plan7 import HMMFile
from anarci.anarci import HMM_path, number_sequence_from_alignment, _hmm_alignment_to_states

HMM = os.path.join(HMM_path, 'ALL.hmm')
seq = 'DVQLVESGGGSVQAGGSLRLSCAVSGSTYSPCTTGWVRQAPGKGLEWVSSISSPGTIYYQDSVKGRFTISRDNAKNTVYLQMNSLQREDTGMYYCQIQCGSIREYWGQGTQVTVS'
seqs = [('test', seq)]

alphabet = pyhmmer.easel.Alphabet.amino()
sb = [pyhmmer.easel.TextSequence(name=n.encode(), sequence=s.encode()) for n,s in seqs]
digitized = pyhmmer.easel.TextSequenceBlock(sb).digitize(alphabet)

with HMMFile(HMM) as hmm_file:
    for top_hits in pyhmmer.hmmer.hmmscan(digitized, hmm_file, cpus=1):
        print(f'Query hits: {len(top_hits)}', flush=True)
        # Get the best hit
        hit = top_hits[0]
        print(f'Best hit: score={hit.score:.1f}', flush=True)
        print(f'Hit attrs: {[a for a in dir(hit) if not a.startswith("_")]}', flush=True)
        
        dom = hit.best_domain
        print(f'\nDomain attrs: {[a for a in dir(dom) if not a.startswith("_")]}', flush=True)
        
        aln = dom.alignment
        print(f'\nAlignment attrs: {[a for a in dir(aln) if not a.startswith("_")]}', flush=True)
        print(f'hmm_name: {aln.hmm_name}', flush=True)
        print(f'target_name: {aln.target_name}', flush=True)
        print(f'hmm_sequence (first 40): {aln.hmm_sequence[:40]}', flush=True)
        print(f'target_sequence (first 40): {aln.target_sequence[:40]}', flush=True)
        
        # Check if there's a reference_annotation (RF)
        if hasattr(aln, 'reference_annotation'):
            print(f'reference_annotation (first 40): {aln.reference_annotation[:40]}', flush=True)
        if hasattr(aln, 'posterior_probabilities'):
            print(f'posterior_probabilities (first 40): {aln.posterior_probabilities[:40]}', flush=True)
        if hasattr(aln, 'identity_sequence'):
            print(f'identity_sequence (first 40): {aln.identity_sequence[:40]}', flush=True)
            
        print(f'\nhmm_from: {aln.hmm_from}, hmm_to: {aln.hmm_to}', flush=True)
        print(f'target_from: {aln.target_from}, target_to: {aln.target_to}', flush=True)
        break
