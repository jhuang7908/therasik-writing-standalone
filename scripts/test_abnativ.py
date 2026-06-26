import sys
import os
import pandas as pd
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from abnativ.model.scoring_functions import abnativ_scoring

seq = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAYDIYGDGAMDYWGQGTLVTVSS"
recs = [SeqRecord(Seq(seq), id="test")]

print("Starting AbNatiV scoring...")
try:
    df_mean, df_profile = abnativ_scoring(
        model_type="VHH2",
        seq_records=recs,
        batch_size=1,
        mean_score_only=True,
        do_align=True,
        is_VHH=True,
        verbose=True,
        run_parall_al=False
    )
    print("Scoring successful!")
    print(df_mean)
except Exception as e:
    print(f"Scoring failed: {e}")
    import traceback
    traceback.print_exc()
