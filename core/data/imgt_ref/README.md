# IMGT Reference FASTA Files

This directory should contain IMGT reference FASTA files for human (and optionally dog) immunoglobulin germline sequences.

## Required Files

Place the following FASTA files in this directory:

1. **IGHV.fasta** - Human heavy chain variable region sequences
2. **IGKV.fasta** - Human kappa light chain variable region sequences  
3. **IGLV.fasta** - Human lambda light chain variable region sequences

## Download Instructions

### Option 1: IMGT Website (Recommended)

1. Visit: https://www.imgt.org/download/GENE-DB/
2. Navigate to "Reference sequences" section
3. Download:
   - Human IGHV sequences (FASTA format)
   - Human IGKV sequences (FASTA format)
   - Human IGLV sequences (FASTA format)
4. Rename files to match expected names:
   - `IGHV.fasta`
   - `IGKV.fasta`
   - `IGLV.fasta`
5. Place all files in this directory

### Option 2: Direct IMGT Download Links

- Human IGHV: https://www.imgt.org/download/GENE-DB/IMGTGENEDB-ReferenceSequences.fasta-nt-WithGaps-F+ORF+in-frame
- Human IGKV: (check IMGT website for current link)
- Human IGLV: (check IMGT website for current link)

**Note:** File names and formats may vary. The script `build_framework_library_from_imgt.py` will attempt to parse various IMGT header formats.

## File Format

Expected FASTA format:
```
>IGHV1-18*01 F|IGHV1|Homo sapiens|F+ORF+in-frame P|1
QVQLVQSGAEVKKPGASVKVSCKASGYTFTSYWINWVRQAPGQGLEWMGIIYPGDSDTRYSPSFQGQVTISADKSISTAYLQWSSLKASDTAMYYCAR
...
```

The script will extract germline IDs (e.g., `IGHV1-18*01`) from headers automatically.

## Verification

After placing files, run:
```bash
python scripts/build_framework_library_from_imgt.py --dry_run
```

This will verify that files are readable and sequences can be found for target germlines.
