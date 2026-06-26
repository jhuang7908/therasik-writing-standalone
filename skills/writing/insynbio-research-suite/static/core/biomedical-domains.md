# InSynBio Research Platform — Biomedical Domain Taxonomy

**Scope declaration (v1.2.0):**
This platform supports **any peer-reviewed biomedical / life science manuscript** indexed or indexable by PubMed.
It is NOT limited to antibody engineering or any single specialty.
Domain is auto-detected from user context; if ambiguous, one clarifying question is asked.

Reference: PubMed MeSH tree (NLM) — https://www.ncbi.nlm.nih.gov/mesh

## Live Domain Verification (MeSH API)

This taxonomy is backed by the **NLM MeSH API** — not just a static list.

```powershell
# Verify a keyword → official MeSH tree position + InSynBio domain
python scripts/insynbio_mesh_lookup.py query "CRISPR-Cas"
python scripts/insynbio_mesh_lookup.py query "checkpoint inhibitor" --top 5

# Auto-detect domain from manuscript title / abstract
python scripts/insynbio_mesh_lookup.py detect --title "Structural basis of PD-L1 recognition"
python scripts/insynbio_mesh_lookup.py detect --abstract-file paper/abstract.txt

# Lookup by MeSH UID
python scripts/insynbio_mesh_lookup.py tree-path D000906
```

Output: MeSH heading · tree number(s) · MeSH category · InSynBio platform domain · scope note

**Anti-hallucination rule:** Domain claims in reports must be verifiable by this CLI.
If `detect` returns a domain, cite it as `[verified via MeSH API]`.
If not verifiable, mark as `[inferred from context]`.

---

## Domain Taxonomy (MeSH-aligned, 12 major categories, 80+ sub-domains)

### 1. Diseases [MeSH C]

| Sub-domain | Examples |
|---|---|
| Oncology / Cancer biology | Solid tumors, hematologic malignancies, tumor microenvironment, metastasis |
| Immuno-oncology | CAR-T, checkpoint inhibitors (PD-1/L1, CTLA-4), bispecific, ADC |
| Infectious disease | Bacterial, viral (HIV, influenza, SARS-CoV-2), fungal, parasitic, prion |
| Cardiovascular disease | Heart failure, coronary artery disease, arrhythmia, cardiomyopathy |
| Pulmonary / Respiratory | COPD, asthma, IPF, pulmonary hypertension, ARDS |
| Neurology | Neurodegeneration (AD, PD, ALS), epilepsy, stroke, MS, TBI |
| Psychiatry / Mental health | Depression, schizophrenia, bipolar, PTSD, addiction, autism spectrum |
| Endocrinology / Metabolic | Diabetes (T1/T2), obesity, thyroid, adrenal, PCOS, metabolic syndrome |
| Gastroenterology / Hepatology | IBD, liver disease (NAFLD/NASH, cirrhosis), GI cancers, microbiome |
| Nephrology / Urology | CKD, AKI, dialysis, renal transplant, bladder/prostate disease |
| Musculoskeletal / Rheumatology | Osteoporosis, RA, SLE, osteoarthritis, myopathy, spondylitis |
| Dermatology | Psoriasis, atopic dermatitis, melanoma, wound healing, alopecia |
| Ophthalmology | AMD, diabetic retinopathy, glaucoma, corneal disease, retinal dystrophy |
| Hematology | Sickle cell, thalassemia, thrombocytopenia, hemophilia, leukemia/lymphoma |
| Reproductive medicine | Infertility, endometriosis, preeclampsia, contraception, PCOS |
| Pediatrics / Neonatology | Congenital disease, pediatric oncology, neonatal intensive care |
| Geriatrics / Aging | Frailty, dementia, sarcopenia, polypharmacy, age-related diseases |
| Rare / Orphan disease | Lysosomal storage, Huntington's, SMA, inborn errors of metabolism |
| Dentistry / Oral health | Caries, periodontal disease, oral cancer, craniofacial anomalies |
| Veterinary medicine | Animal disease models, zoonoses, comparative medicine |
| Environmental / Occupational | Toxicology, environmental exposures, occupational lung disease |

---

### 2. Therapeutics & Drug Development [MeSH D / E]

| Sub-domain | Examples |
|---|---|
| Small molecule drug discovery | Target ID, HTS, hit-to-lead, ADMET, PK/PD, medicinal chemistry |
| Biologics (non-antibody) | Cytokines, growth factors, fusion proteins, peptide therapeutics |
| Antibody engineering | De novo design, humanization, VHH, bispecific, CMC, ADC |
| Gene therapy | CRISPR-Cas, base/prime editing, AAV/LV vectors, gene replacement |
| Cell therapy | CAR-T, TCR-T, NK, macrophage, iPSC-derived, TIL therapy |
| mRNA therapeutics | mRNA vaccines, LNP delivery, therapeutic mRNA, self-amplifying RNA |
| RNA-based therapy | siRNA, ASO, miRNA, splice-switching oligos, saRNA |
| Gene editing / Epigenetics | Epigenome editing, CRISPRa/i, chromatin remodeling, methylation |
| Vaccines | Subunit, live-attenuated, VLP, mRNA, adjuvants, challenge models |
| Drug delivery / Nanotechnology | LNP, polymeric NPs, liposomes, hydrogel, targeted delivery, BBB crossing |
| Pharmacology / Toxicology | PK/PD modeling, drug-drug interactions, adverse effects, safety assessment |
| Radiopharmaceuticals | Theranostics, PET tracers, targeted radionuclide therapy |
| Medical devices | Implants, diagnostics, wearables, biosensors, surgical devices |

---

### 3. Immunology [MeSH C20 / D23]

| Sub-domain | Examples |
|---|---|
| Innate immunity | Pattern recognition, inflammasome, complement, NK biology |
| Adaptive immunity | T cell / B cell biology, TCR/BCR repertoire, GC reactions |
| Autoimmunity | Tolerance, molecular mimicry, regulatory T cells, autoantibodies |
| Allergy / Hypersensitivity | IgE, mast cells, eosinophils, food allergy, anaphylaxis |
| Transplant immunology | Graft rejection, tolerance induction, HLA matching |
| Tumor immunology | Immune evasion, TME, antigen presentation, neoantigen |
| Mucosal immunology | Gut-associated lymphoid tissue, IgA, microbiome-immune axis |
| Neuroimmunology | Neuroinflammation, microglia, blood-brain barrier immunology |

---

### 4. Genetics / Genomics / Molecular Biology [MeSH G05 / G06]

| Sub-domain | Examples |
|---|---|
| Human genetics | GWAS, Mendelian disease, variant classification, polygenic risk |
| Functional genomics | RNA-seq, scRNA-seq, spatial transcriptomics, CRISPR screens |
| Epigenomics | ChIP-seq, ATAC-seq, DNA methylation, histone modification |
| Proteomics | Mass spectrometry, protein interactions, PTMs, protein complexes |
| Metabolomics | Metabolite profiling, flux analysis, metabolic networks |
| Microbiome / Metagenomics | 16S rRNA, shotgun metagenomics, virome, host-microbiome axis |
| Single-cell multi-omics | scRNA-seq, CITE-seq, scATAC-seq, spatial omics |
| Comparative / Evolutionary genomics | Phylogenomics, variant evolution, population genetics |

---

### 5. Structural Biology & Biochemistry [MeSH G02]

| Sub-domain | Examples |
|---|---|
| Protein structure | X-ray crystallography, cryo-EM, NMR, AlphaFold structure prediction |
| Protein-protein interactions | PPI networks, interface mapping, co-IP, proximity ligation |
| Enzyme biochemistry | Kinetics, mechanism, inhibition, cofactor biology |
| Lipid / Membrane biology | Lipid bilayers, membrane proteins, lipid signaling |
| Nucleic acid biochemistry | DNA repair, replication, G-quadruplex, RNA secondary structure |
| Glycobiology | Glycan synthesis, lectin biology, glycoprotein engineering |

---

### 6. Cell Biology & Physiology [MeSH G04 / G09]

| Sub-domain | Examples |
|---|---|
| Cell signaling | Kinase cascades, second messengers, receptor biology, autophagy |
| Cell cycle / Apoptosis | Cell death pathways, senescence, mitosis, checkpoints |
| Stem cell biology | Pluripotency, differentiation, organoids, tissue engineering |
| Developmental biology | Embryogenesis, morphogenesis, lineage tracing, pattern formation |
| Metabolism / Mitochondria | Oxidative phosphorylation, TCA, fatty acid oxidation, mitophagy |
| Extracellular matrix | Collagen, fibronectin, tissue remodeling, fibrosis |
| Neuroscience | Neural circuits, synaptic biology, glia, neuroplasticity |
| Cardiovascular physiology | Cardiac muscle, vascular biology, angiogenesis, thrombosis |

---

### 7. Computational Biology & Bioinformatics [MeSH L01]

| Sub-domain | Examples |
|---|---|
| Sequence analysis | Alignment, variant calling, assembly, annotation |
| Structural bioinformatics | Protein modeling, docking, MD simulation, binding prediction |
| Machine learning / AI in biology | Deep learning for genomics, protein LLMs, image classification |
| Network biology | Protein interaction networks, pathway enrichment, systems biology |
| Clinical bioinformatics | EHR mining, real-world data, clinical NLP |
| Benchmark / Methods papers | Tool comparison, software pipelines, reproducibility studies |
| Mathematical / Statistical modeling | Agent-based models, ODE systems, Bayesian inference in biology |

---

### 8. Epidemiology & Public Health [MeSH N]

| Sub-domain | Examples |
|---|---|
| Epidemiology | Cohort, case-control, cross-sectional, meta-analysis, systematic review |
| Infectious disease epidemiology | Outbreak, surveillance, transmission dynamics, vaccine effectiveness |
| Cancer epidemiology | Incidence, risk factors, screening, survivorship |
| Global health | NTDs, health equity, low/middle-income country studies |
| Health economics | Cost-effectiveness, budget impact, QALY, health technology assessment |
| Biostatistics | Clinical trial design, survival analysis, mixed models, propensity score |

---

### 9. Clinical Medicine & Translational Research [MeSH E05 / N02]

| Sub-domain | Examples |
|---|---|
| Clinical trials | Phase I–III design, adaptive trials, basket/umbrella, CONSORT reporting |
| Biomarker research | Liquid biopsy, companion diagnostics, surrogate endpoints |
| Translational oncology | PDX, patient-derived organoids, co-clinical trials |
| Precision medicine | Pharmacogenomics, molecular tumor boards, matched therapy |
| Radiology / Medical imaging | MRI, PET-CT, ultrasound, AI-assisted image analysis |
| Surgery / Minimally invasive | Laparoscopic, robotic, wound healing, perioperative outcomes |
| Emergency / Critical care | Sepsis, mechanical ventilation, hemodynamic monitoring |
| Anesthesiology / Pain medicine | Perioperative analgesia, regional blocks, chronic pain |
| Palliative / Supportive care | Symptom management, end-of-life, patient-reported outcomes |

---

### 10. Biomedical Engineering & Medical Technology [MeSH J]

| Sub-domain | Examples |
|---|---|
| Tissue engineering | Scaffolds, 3D bioprinting, organoids, decellularization |
| Biosensors & Diagnostics | Point-of-care, lab-on-chip, electrochemical sensors |
| Imaging technology | Optical coherence tomography, super-resolution, light-sheet microscopy |
| Neural engineering | Brain-machine interfaces, neural prosthetics, neuromodulation |
| Biomaterials | Hydrogels, polymers, implants, degradable materials |
| Wearables & Digital health | Continuous monitoring, digital biomarkers, mHealth |

---

### 11. Nutrition, Exercise & Sports Medicine [MeSH G07 / N02]

| Sub-domain | Examples |
|---|---|
| Nutrition science | Dietary interventions, micronutrients, gut-diet axis |
| Exercise physiology | Performance, recovery, muscle adaptation, VO₂max |
| Sports medicine / Rehabilitation | Injury, return-to-play, physical therapy outcomes |

---

### 12. Cross-Cutting / Methodological

| Sub-domain | Examples |
|---|---|
| Animal models | Rodent, NHP, zebrafish, organoid models for any disease |
| Histology / Pathology | IHC, ISH, FISH, digital pathology, spatial pathology |
| Flow cytometry & Cell sorting | Mass cytometry (CyTOF), spectral flow, cell phenotyping |
| CRISPR screens (functional) | Genome-wide KO/activation screens, arrayed vs. pooled |
| Proteomics / Mass spectrometry | DIA/DDA, PTM profiling, structural MS, cross-linking |
| Cryo-EM / single-particle | Structure determination, subtomogram averaging |
| Organoids & 3D culture | Patient-derived, assembloids, organ-on-chip |

---

## Domain Routing Rules

### Auto-Detection Signals

The router auto-detects domain from user message, manuscript title, target gene/protein, and keywords.
If ambiguous across major categories, ask in ONE line before routing.

| Key signal | Detected domain |
|---|---|
| "antibody", "VHH", "CDR", "humanization", "paratope" | Antibody engineering |
| "CAR-T", "checkpoint", "tumor", "PD-L1", "TME" | Immuno-oncology |
| "CRISPR", "base edit", "AAV", "prime editing", "gene therapy" | Gene therapy |
| "GWAS", "SNP", "polygenic", "variant", "linkage" | Human genetics |
| "scRNA-seq", "single-cell", "spatial transcriptomics" | Functional genomics |
| "cryo-EM", "crystal structure", "pLDDT", "AlphaFold" | Structural biology |
| "Phase I/II/III", "randomized", "CONSORT", "hazard ratio" | Clinical trials |
| "IC50", "ADMET", "medicinal chemistry", "lead compound" | Drug discovery |
| "16S rRNA", "metagenomics", "microbiome", "gut bacteria" | Microbiome |
| "mRNA vaccine", "LNP", "adjuvant", "neutralization titer" | Vaccines / mRNA |
| "siRNA", "ASO", "antisense", "splice-switching" | RNA therapeutics |
| "benchmark", "accuracy", "F1", "model", "dataset", "AUC" | Computational / AI |
| "meta-analysis", "systematic review", "incidence", "hazard" | Epidemiology |
| "EHR", "real-world data", "electronic health record" | Clinical bioinformatics |
| "scaffold", "hydrogel", "bioprint", "biomaterial" | Biomedical engineering |
| "biomarker", "liquid biopsy", "ctDNA", "companion diagnostic" | Translational / Precision |

### Domain-Invariant Rules

These never change regardless of domain:
- Pipeline order (literature → write → fact gate → submission bundle)
- Anti-hallucination gate (`insynbio-rigor` or `content-ssot-guard`)
- Citation verification (OpenAlex T3 + corpus verify)
- Figure format contract (`insynbio-figure`)
- Style Calibration (works for any domain)
- Material Passport JSON structure

### Domain-Specific Gates

| Domain | Extra gate / checklist |
|---|---|
| Antibody engineering | AbEngineCore CMC + `insynbio-rigor` |
| Clinical trials | CONSORT / STROBE / PRISMA checklist in bundle audit |
| Epidemiology / Systematic review | PRISMA, GRADE evidence level tagging |
| Computational methods | Code availability + reproducibility statement |
| Structural biology | PDB deposition accession confirmation |
| Gene therapy / Editing | Biosafety statement + off-target reporting |
| Vaccines / Infectious disease | Regulatory classification note |
| Animal studies | ARRIVE 2.0 / IACUC statement |
| Human studies | IRB/ethics statement + consent declaration |
| Omics datasets | GEO / dbGaP / ENA accession confirmation |
