# VHH v1 

: 2025-12-13 19:42:45

## 1. 

### 

|  |  |  |  |
|------|------|------|--------|
| manifest.json | ✅ | 0.00 MB | - |
| vhh_germline_assets_clean.jsonl | ✅ | 0.64 MB | 264 |
| vhh_germline_assets_clean_with_canonical_proxy.jsonl | ❌ | - | - |

## 2. VHH Hallmark 

⚠️ ， `analyze_vhh_hallmark_distribution.py`

## 3. 

|  |  |  |
|--------|------|------|
| VHH clean  | ✅ PASS | PASS: 264  |
| Hallmark  | ❌ FAIL | FAIL |
| Canonical proxy  | ❌ FAIL | FAIL:  |
| QC CSV  | ❌ FAIL | FAIL:  |

---

## 

1. : `python scripts/generate_vhh_v1_file_inventory.py`
2.  Hallmark : `python scripts/analyze_vhh_hallmark_distribution.py`
3.  Scaffold  Debug: `python scripts/generate_scaffold_ranking_debug_vhh.py --input_json <stage1_result.json>`
