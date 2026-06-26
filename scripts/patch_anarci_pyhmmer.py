import os
import sys

ANARCI_PY = r"d:\Users\NextVivo\miniconda3\envs\affmat\Lib\site-packages\anarci\anarci.py"

PATCH_CODE = '''
    # --- pyhmmer path (no external hmmscan binary required) ---
    try:
        import pyhmmer
        from pyhmmer.plan7 import HMMFile
        import pyhmmer.hmmer
        from Bio.SearchIO.HmmerIO import Hmmer3TextParser
        import io

        alphabet = pyhmmer.easel.Alphabet.amino()
        seqs_block = [
            pyhmmer.easel.TextSequence(name=name.encode(), sequence=seq.encode())
            for name, seq in sequence_list
        ]
        digitized = pyhmmer.easel.TextSequenceBlock(seqs_block).digitize(alphabet)

        all_top_hits = []
        with HMMFile(HMM) as hmm_file:
            for top_hits in pyhmmer.hmmer.hmmscan(
                digitized, hmm_file,
                cpus=1 if ncpu is None else ncpu,
            ):
                all_top_hits.append(top_hits)

        # Create a full HMMER3 text output that Hmmer3TextParser can handle
        full_output = io.BytesIO()
        header = (
            "# HMMER 3.3.2 (Nov 2020); http://hmmer.org/\\n"
            "# Copyright (C) 2020 Howard Hughes Medical Institute.\\n"
            "# Freely distributed under the BSD open source license.\\n"
            "# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -\\n"
        )
        full_output.write(header.encode())
        
        for i, th in enumerate(all_top_hits):
            query_name = sequence_list[i][0]
            query_seq = sequence_list[i][1]
            full_output.write(f"Query:       {query_name}  [L={len(query_seq)}]\\n".encode())
            th.write(full_output)
            full_output.write(b"//\\n")
        
        full_output.seek(0)
        
        # DEBUG: print first 1000 chars of simulated output
        # print(full_output.getvalue()[:1000].decode())

        import tempfile as _tmpmod
        out_fd, out_path = _tmpmod.mkstemp(".txt", text=False)
        with os.fdopen(out_fd, 'wb') as fout:
            fout.write(full_output.getvalue())

        results = parse_hmmer_output(
            out_path, bit_score_threshold=bit_score_threshold,
            hmmer_species=hmmer_species
        )
        try:
            os.remove(out_path)
        except Exception:
            pass
        if results:
            return results

    except Exception as e:
        # print(f"DEBUG: pyhmmer path failed: {e}")
        pass
    # --- end pyhmmer attempt ---
'''

def main():
    if not os.path.exists(ANARCI_PY):
        print(f"Error: {ANARCI_PY} not found.")
        return

    with open(ANARCI_PY, 'r') as f:
        lines = f.readlines()

    new_lines = []
    skip = False
    for line in lines:
        if "# --- pyhmmer path" in line:
            skip = True
            new_lines.append(PATCH_CODE)
        elif "# --- end pyhmmer attempt" in line:
            skip = False
            continue
        if not skip:
            new_lines.append(line)

    with open(ANARCI_PY, 'w') as f:
        f.writelines(new_lines)
    print("Successfully patched anarci.py")

if __name__ == "__main__":
    main()
