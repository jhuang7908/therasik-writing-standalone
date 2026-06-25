# Benchmark Sequences for Dual Map Validation

This directory contains benchmark FASTA files for validating IMGT/Kabat dual mapping consistency.

## Files

### `fasta/egfr_7d12_vhh.fasta`
- **Source**: PDB 4KRM/4KRL (7D12-EGFR complex)
- **Chain**: B (VHH domain)
- **Description**: 7D12 VHH nanobody targeting human EGFR
- **Expected chain_type**: VHH (or H)

### `fasta/pd1_6jbt_mouse_fab_vhvl.fasta`
- **Source**: PDB 6JBT (anti-PD-1 mouse Fab)
- **Chains**: 
  - B: Heavy chain (VH + Fc)
  - C: Light chain (VL + CL)
- **Expected chain_types**: VH (or H) and VL (or L)
- **Note**: Contains Fc/CL regions; ANARCI should identify VH and VL portions

## Usage

```bash
# Validate 7D12 VHH
python tools/validate_dual_map_consistency.py \
  --seq_fasta data/benchmarks/fasta/egfr_7d12_vhh.fasta \
  --out reports/mapping/egfr_7d12_vhh_dual_map_report.json

# Validate mouse Fab (VH + VL)
python tools/validate_dual_map_consistency.py \
  --seq_fasta data/benchmarks/fasta/pd1_6jbt_mouse_fab_vhvl.fasta \
  --out reports/mapping/pd1_6jbt_mouse_fab_vhvl_dual_map_report.json
```

## Validation Criteria

The validation script (`tools/validate_dual_map_consistency.py`) will:

1. **Filter antibody chains only**: Only process chains with `chain_type` in {VHH, VH, VL} (or 'H', 'L', 'K')
2. **Exclude non-antibody chains**: Antigen chains (e.g., PD-1) are identified as `non_antibody` and excluded from validation
3. **Report statistics**: For antibody chains only, report:
   - Dual map status (full/partial/conflict/failed)
   - Positions with both IMGT and Kabat
   - Gap counts
   - Insertion counts

## Expected Results

- **7D12 VHH**: Should be identified as VHH chain, dual map should be "full" or "partial"
- **6JBT VH**: Should be identified as VH chain
- **6JBT VL**: Should be identified as VL chain
- **PD-1 antigen** (if present): Should be excluded as non-antibody










