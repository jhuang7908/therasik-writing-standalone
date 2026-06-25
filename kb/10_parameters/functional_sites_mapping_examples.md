# Functional Sites Mapping Status Report

## Dual Map Status

### Overall Statistics
- **Total functional sites**: 12
- **Sites with exact IMGT/Kabat match**: 12 (100.0%)
- **Sites with position mismatch**: 0
- **Conflict count**: 0

### Position Coverage
- **Total unique IMGT positions**: 30
- **Total unique Kabat positions**: 30
- **Overlapping positions**: 30
- **IMGT-only positions**: 0
- **Kabat-only positions**: 0

**Status**: ✅ **CONSISTENT** - All functional sites have matching IMGT and Kabat positions.

---

## Hallmark Sites Mapping Statistics

- **Total hallmark sites**: 3
- **Exact IMGT/Kabat matches**: 3 (100.0%)
- **Mismatches**: 0
- **IMGT positions covered**: 7 (positions: 37, 38, 39, 44, 45, 49, 50)
- **Kabat positions covered**: 7 (positions: 37, 38, 39, 44, 45, 49, 50)
- **Overlapping positions**: 7

**Status**: ✅ **CONSISTENT** - All hallmark sites have matching IMGT and Kabat positions.

### Hallmark Sites Details:
1. **HALLMARK_VHH_37_39**: IMGT [37, 38, 39] ↔ Kabat [37, 38, 39] ✅
2. **HALLMARK_VHH_44_45**: IMGT [44, 45] ↔ Kabat [44, 45] ✅
3. **HALLMARK_VHH_49_50**: IMGT [49, 50] ↔ Kabat [49, 50] ✅

---

## Vernier Sites Mapping Statistics

- **Total vernier sites**: 5
- **Exact IMGT/Kabat matches**: 5 (100.0%)
- **Mismatches**: 0
- **IMGT positions covered**: 14 (positions: 29, 30, 71, 72, 73, 78, 79, 80, 94, 95, 96, 102, 103, 104)
- **Kabat positions covered**: 14 (positions: 29, 30, 71, 72, 73, 78, 79, 80, 94, 95, 96, 102, 103, 104)
- **Overlapping positions**: 14

**Status**: ✅ **CONSISTENT** - All vernier sites have matching IMGT and Kabat positions.

### Vernier Sites Details:
1. **VERNIER_29_30**: IMGT [29, 30] ↔ Kabat [29, 30] ✅
2. **VERNIER_71_73**: IMGT [71, 72, 73] ↔ Kabat [71, 72, 73] ✅
3. **VERNIER_78_80**: IMGT [78, 79, 80] ↔ Kabat [78, 79, 80] ✅
4. **VERNIER_94_96**: IMGT [94, 95, 96] ↔ Kabat [94, 95, 96] ✅
5. **VERNIER_102_104**: IMGT [102, 103, 104] ↔ Kabat [102, 103, 104] ✅

---

## Conflict Examples

### Current Status
✅ **No conflicts detected** - All functional sites have consistent IMGT/Kabat mappings.

### Typical Conflict Pattern (Example)

In VHH/VH structures, a common conflict occurs at position 37:

**Conflict Type**: `kabat_to_imgt_gap`

**Example**:
```yaml
site_id: "HALLMARK_VHH_37"
role: "hallmark"
imgt_positions: []  # Position 37 is a gap in IMGT numbering
kabat_positions: [37]  # Position 37 exists in Kabat numbering
scope: [vhh]
notes: "VHH hallmark: Kabat 37 maps to IMGT gap (common VHH pattern)"
```

**Description**: 
- In VHH structures, Kabat position 37 typically exists and is part of the hallmark region
- In IMGT numbering, position 37 is often a gap (insertion region)
- This creates a mapping conflict: the same structural position has different numbering

**Impact**:
- Rules referencing `IMGT:37` would not find the position
- Rules referencing `Kabat:37` would find it
- Mutation plans must specify which numbering scheme is used
- Reports must clearly indicate which scheme is primary

**Resolution Strategy**:
- Use IMGT as primary numbering (as per `numbering.imgt.map` being required)
- Map Kabat positions to IMGT when needed
- Flag conflicts in `numbering.dual_map_qc.conflicts`
- Document in report when Kabat-only positions are referenced

---

## Summary

All functional sites in `functional_sites.yaml` currently have **perfect IMGT/Kabat alignment** (100% match rate). This is ideal for:
- Consistent rule execution
- Clear mutation positioning
- Unambiguous reporting

However, in real-world VHH sequences, conflicts may arise (especially at position 37). The validation and reporting system should handle these gracefully by:
1. Using IMGT as primary numbering
2. Mapping Kabat positions when needed
3. Flagging conflicts in `numbering.dual_map_qc`
4. Documenting conflicts in reports










