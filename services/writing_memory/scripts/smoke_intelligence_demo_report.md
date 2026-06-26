# Module 4 Intelligence — Smoke Test Report

- **When:** 2026-06-04T04:16:33.955798+00:00
- **Base:** https://write.insynbio.com
- **Project ID:** `demo_m4_lit_pat`
- **Elapsed:** 50.3s
- **Result:** 25 PASS / 2 WARN / 0 FAIL (of 27)

## Verification Status

Automated API smoke against production; case evidence in table below.

## Cases

| ID | Feature | Endpoint | Status | Evidence |
|----|---------|----------|--------|----------|
| F01 | Account · library backend | `GET /intelligence/library/status` | **PASS** | backend=sqlite, count=23 |
| F02 | Literature Search | `POST /library/openalex/search` | **PASS** | 5 works; first=Multinational Study of the Efficacy and Safety of Humanized  |
| F03 | Literature · 💾 Save (single) | `POST /intelligence/library/save` | **PASS** | id=42, inserted=True |
| F04 | Literature · 💾 Save all | `POST /intelligence/library/save (×N)` | **PASS** | saved 3/3 from search batch |
| F05 | Literature Database · ↻ All | `GET /intelligence/library/list` | **PASS** | listed=26, total_in_project=26, project=demo_m4_lit_pat |
| F06 | Literature Database · semantic search | `POST /intelligence/library/search` | **PASS** | 5 hit(s); top=Multinational Study of the Efficacy and Safety of  |
| F07 | Hotspot Digest | `POST /intelligence/digest/generate` | **PASS** | saved_report_id=11, len=2792 |
| F08 | Hotspot Digest · history | `GET /intelligence/reports/list?kind=digest` | **PASS** | 1 digest report(s) |
| F09 | Patent Search · ODP status | `GET /ip/config` | **PASS** | odp=True, source=uspto_odp |
| F10 | Patent Search | `POST /ip/patent/search` | **PASS** | 3 hits; first US 19165731; source=uspto_odp |
| F11 | Patent · 💾 Save | `POST /intelligence/library/save (patent)` | **PASS** | patent doc id=45 |
| F12 | Patent Database | `GET /intelligence/library/list?source=patent` | **PASS** | 5 patent row(s) in library |
| F13 | Patent · View record (in-app) | `GET /ip/patent/detail` | **PASS** | title=ANTI-CD27 MONOCLONAL ANTIBODY AND USE THEREOF; assignee=SHANGHAI CELGEN BIO-PHARMACEUTICAL CO.,  |
| F14 | Patent · Antibody sequences (ODP ST.26) | `GET /ip/patent/sequences` | **WARN** | sequences=0; note=No sequence listing XML in USPTO file wrapper for this application. Try a granted antibody patent, paste FASTA/ST.26 und |
| F15 | Sequence/Structure · Parse FASTA | `POST /ip/sequence/parse` | **PASS** | chains=2, antibody_like=2 |
| F16 | Sequence → Patent lookup (keyword) | `POST /ip/sequence/search` | **WARN** | 5 patent lead(s); note=MVP: keyword proxy only — full sequence homology search (WIPO/USPTO BLAST) plann |
| F17 | FTO Analysis | `POST /intelligence/fto/draft` | **PASS** | count=4, saved=12 |
| F18 | FTO · history | `GET /intelligence/reports/list?kind=fto` | **PASS** | 1 FTO report(s) |
| F19 | AI Chat (library-grounded) | `POST /intelligence/chat` | **PASS** | reply_len=680, sources=5 |
| F20 | Literature · → Facts | `POST /library/openalex/import_to_facts` | **PASS** | facts count=2 |
| F21 | Patent · → Facts | `POST /ip/import_to_facts` | **PASS** | count=2 |
| F23 | Library · reference styles | `GET /intelligence/library/styles` | **PASS** | styles=3 |
| F24 | Library · RIS import/export | `POST import + GET export` | **PASS** | parsed=1, export_ok=True |
| F25 | Library · format references (排版) | `POST /intelligence/library/format` | **PASS** | refs=23 |
| F26 | Literature · Unpaywall OA | `POST /library/openalex/search` | **PASS** | works=3, oa_fields=True |
| F27 | Library · sync with Write | `POST /intelligence/library/sync` | **PASS** | to_write={'direction': 'to_write', 'project_id': 'demo_m4_lit_pat', 'pushed': 4, 'updated': 19, 'skipped_non_literature': 5, 'total_intel_literature': 23}, from_write={'direction': 'from_write', 'project_id': 'demo_m4_lit_pat', 'saved': 3, 'updated': 12, 'skipped_other_project': 0, 'write_entries_seen': 15} |
| F22 | Module 4 IDE shell | `GET /intelligence` | **PASS** | v2.0 I/O markers present |

## Adversarial Checks

- **Alternative:** Empty library may be user error (no Save) not API failure — F05 fails if Save cases failed. PASS/WARN if saves succeeded.
- **Failure mode:** ODP may return no SEQLST for recent apps — F14 WARN expected, not product regression. PASS
- **Boundary:** Sequence search is keyword proxy not BLAST — F16 marked WARN by design. PASS

## Sources

- Live API: https://write.insynbio.com [verified]
- Script: `services/writing_memory/scripts/smoke_intelligence_module4.py` [verified]
