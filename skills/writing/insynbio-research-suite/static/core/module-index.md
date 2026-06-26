# Module Index — InSynBio Research Platform (General Biomedical Writing)

> **Scope:** General peer-reviewed biomedical research — oncology, immunology, gene therapy, drug discovery, structural biology, clinical trials, and more. Not limited to antibody engineering.  
> Master router: **`insynbio-therasik-suite`** · Brand SSOT: `config/insynbio_therasik_brands.json`  
> Domain taxonomy: `static/core/biomedical-domains.md`

## Writing Pipeline Stages

| Stage | nature-skills | InSynBio/Therasik module | Executable | Domain |
|-------|---------------|--------------------------|------------|--------|
| 选题 / brainstorm | (external) | `deep-research` | ARS skill | Any |
| 检索 | `nature-academic-search` | **`insynbio-literature-search`** | `scripts/insynbio_openalex.py` + corpus CLI | Any |
| 引用 / Zotero | `nature-citation` | **`insynbio-citation`** | `scripts/insynbio_citation.py` | Any |
| 综述 / 写作 | `nature-writing` | `academic-paper` + `writing_memory` | manuscript MD | Any |
| **风格校准** | *(ARS Step 10)* | **`style_calibration`** workflow | `ARS shared/style_calibration_protocol.md` | Any |
| 润色 | `nature-polishing` | **`insynbio-polishing`** | `scripts/insynbio_polishing.py` | Any |
| 全文 reader | `nature-reader` | **`insynbio-paper-reader`** | `scripts/insynbio_paper_reader.py` | Any |
| 预审稿 | `nature-reviewer` | `academic-paper-reviewer` | ARS skill | Any |
| 修回 | `nature-response` | `journal-submission-prep` (Module 6) | response letter templates | Any |
| 数据声明 | `nature-data` | manuscript §Data + bundle audit | — | Any |
| 投稿图 | `nature-figure` | **`insynbio-figure`** (Stable) | `scripts/insynbio_figure.py` | Any |
| **AFDB pLDDT** | *(GDM science-skills)* | `insynbio-figure` recipe `afdb_plddt` | `core/figure/afdb_plddt.py` | Structural |
| 专利 outline | `nature-paper-to-patent` | **`insynbio-paper-to-patent`** | `scripts/insynbio_paper_to_patent.py` | Any |
| **稿件护照** | *(ARS Material Passport)* | **`material_passport`** workflow | `scripts/insynbio_material_passport.py` | Any |
| **投稿包** | (weak) | **`journal-submission-bundle`** | `scripts/build_submission_bundle.py` | Any |
| **汇报 PPT** | `nature-paper2ppt` | **`insynbio-paper2ppt`** | `scripts/insynbio_paper2ppt.py` | Any |
| 中国内容 | (weak) | **Therasik / NextVivo** skills | `scripts/therasik_wechat_episode.py` | CN |
| 统筹 | (分散) | **`insynbio-therasik-suite`** + `insynbio_research.py` | project registry | Any |

## Domain-Specific Modules

| Domain | Additional module / gate |
|--------|--------------------------|
| Antibody / VHH | `AbEngineCore` + `insynbio-rigor` + `content-ssot-guard` fact gate |
| Clinical / Translational | CONSORT/STROBE/PRISMA checklist in bundle audit |
| Computational methods | Code availability + reproducibility statement check |
| Structural biology | PDB deposition check; `afdb_plddt` recipe for AF predictions |
| Gene therapy | Biosafety statement + vector characterization checklist |
| Vaccine / Infectious disease | Regulatory classification check in bundle audit |

## InSynBio-only layers (no nature equivalent)

- **AbEngineCore** — antibody-specific pipelines (VHH, VH/VL humanization, VAM, CMC)
- **Frozen literature registry** — de novo / antibody corpus with embeddings (`data/denovo_literature/`)
- **ScholarOne PASS/FAIL audit** — multi-field submission checklist
- **content-ssot-guard** — DeepSeek + Kimi fact gate (general biomedical)
- **Style Calibration** — author voice profiling (6-dimension, ARS shared protocol)
- **Material Passport** — cross-session manuscript state tracking (ARS Schema 9 adapted)
- **OpenAlex T3 layer** — free real-time DOI verify + topic search (`scripts/insynbio_openalex.py`)
