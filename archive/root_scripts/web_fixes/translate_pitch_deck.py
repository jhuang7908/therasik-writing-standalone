import sys

file_path = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read

translations = {
    # Slide 1
    "、 AI ，<br>——。": 
    "Integrating immunology expertise, clinical benchmarking libraries, and an expansive AI toolchain<br>to provide actionable decision support for biotherapeutic development—beyond isolated algorithm scoring.",
    
    # Slide 2
    "<span>\"\"</span>": "Three Major <span>\"Black Boxes\"</span> in Biologics Development",
    " AI 。，。": "Pure AI scoring does not equal decision making. Without clinical data as a baseline, all predictions are guesswork.",
    "CMC ": "Lagging CMC Developability Assessment",
    " IND /。<br><strong style=\"color:#fca5a5\">：6–18 </strong>": 
    "Aggregation and stability defects only fully exposed at the IND stage.<br><strong style=\"color:#fca5a5\">Cost: 6–18 months of rework</strong>",
    "": "Lack of Immunogenicity Baselines",
    " ADA 。<br><strong style=\"color:#fde68a\">：</strong>": 
    "Severe ADA reactions triggered during animal studies or Phase I trials.<br><strong style=\"color:#fde68a\">Cost: Entire pipeline scrapped</strong>",
    "": "Blind Trial & Error in Complex Modalities",
    "/ADC/CAR  Linker、Payload、。<br><strong style=\"color:#c4b5fd\">：</strong>": 
    "Heavy reliance on guesswork for Linkers, Payloads, and formatting in Bispecifics/ADC/CAR.<br><strong style=\"color:#c4b5fd\">Cost: Millions in trial and error</strong>",

    # Slide 3
    "，<span></span>": "We are not a tool vendor, but a <span>Decision System</span>",
    "：AI vs CRO vs InSynBio": "Comparison: Pure AI Tools vs. Traditional CROs vs. InSynBio",
    "<th> AI </th><th> CRO </th><th style=\"color:#5eead4\">InSynBio</th>": 
    "<th>Pure AI Tool Platforms</th><th>Traditional CROs</th><th style=\"color:#5eead4\">InSynBio</th>",
    "<tr><td style=\"color:rgba(255,255,255,0.4)\"></td><td> / CSV</td><td></td><td></td></tr>": 
    "<tr><td style=\"color:rgba(255,255,255,0.4)\">Output</td><td>Scores / CSV files</td><td>Experimental data</td><td>Actionable decision reports with expert interpretation</td></tr>",
    "<tr><td style=\"color:rgba(255,255,255,0.4)\"></td><td></td><td></td><td>1,142 </td></tr>": 
    "<tr><td style=\"color:rgba(255,255,255,0.4)\">Benchmark</td><td>No clinical control</td><td>Experience-based</td><td>Benchmarked against 1,142 clinical antibody sequences</td></tr>",
    "<tr><td style=\"color:rgba(255,255,255,0.4)\"></td><td></td><td></td><td>3–5  · </td></tr>": 
    "<tr><td style=\"color:rgba(255,255,255,0.4)\">Turnaround</td><td>Minutes (Unverified)</td><td>Months</td><td>3–5 business days · Expert panel reviewed</td></tr>",
    "<tr><td style=\"color:rgba(255,255,255,0.4)\"></td><td></td><td>NDA</td><td>NDA  · </td></tr>": 
    "<tr><td style=\"color:rgba(255,255,255,0.4)\">Data Security</td><td>Uncertain</td><td>NDA protected</td><td>NDA-first · Sequences isolated from public training</td></tr>",
    "<tr><td style=\"color:rgba(255,255,255,0.4)\"></td><td></td><td></td><td>30+ AI  × </td></tr>": 
    "<tr><td style=\"color:rgba(255,255,255,0.4)\">Methodology</td><td>Single models</td><td>Single assays</td><td>Scenario-based orchestration of 30+ AI tools</td></tr>",
    "\"，；，； AI ，。\"": 
    "\"Clinically traceable without synthetic databanks; Expert reviewed, lacking black-box outputs; Dozens of AI tools combined flexibly by scenario instead of relying blindly on a single model.\"",

    # Slide 4
    " — <span></span>": "Our Exclusive Moat — <span>Clinical Data Foundation</span>",
    " Baseline  AI 。，。": 
    "AI without a clinical baseline is mere simulation. Our judgments are grounded because hundreds of real-world drugs act as our foundational benchmark.",
    "": "Clinical Antibody<br>Sequences",
    "<br>(AbRef-458)": "Engineered Antibodies<br>(AbRef-458)",
    " ADA<br>": "Clinical ADA<br>Immunogenicity Records",
    "ADC <br>": "Clinical ADC<br>Project Data",
    "CAR-T <br>": "CAR-T Design<br>Components",
    " Germline<br>": "Clinical Germline<br>Database",
    " CMC<br>": "Bispecific CMC<br>Benchmarks",
    "MHC I/II<br>": "MHC I/II<br>Epitope Records",
    " VHH<br>": "Clinical VHH<br>Reference Molecules",
    " Fc<br>": "Clinical Fc<br>Engineering Records",

    # Slide 5
    "CMC  — <span>15  × 4 </span>": "CMC Firewall — <span>15 Dimensions × 4 Directions</span>",
    " IND ，。，。": 
    "Discovering physicochemical flaws at IND is the most expensive mistake. We establish safety margins directly at the sequence stage by benchmarking against actual clinical drugs.",
    "📊  CMC (5)": "📊 Sequence-Level CMC (5 Dimensions)",
    "pI  ( 5.5–8.5) · GRAVY  ·  · SAP  (9-mer , 7-mer ) ·  pH7": 
    "pI Isoelectric Point (Threshold 5.5–8.5) · GRAVY Hydrophobicity · Instability Index · SAP Aggregation Propensity (9-mer hydrophobic, 7-mer charge) · Net Charge at pH 7",
    "📋 TAP  (Raybould 2019)": "📋 TAP Guidelines (Raybould 2019)",
    "Total CDR Length · PSH  · PPC  · PNC  · SFvCSP  — <strong style=\"color:#fde68a\"></strong>": 
    "Total CDR Length · PSH (Hydrophobic Patches) · PPC/PNC (Charge Patches) · SFvCSP (Charge Asymmetry) — <strong style=\"color:#fde68a\">All paired with clinical benchmark thresholds</strong>",
    "🔬  13 ": "🔬 Structural Level (13 Parameters)",
    "VH-VL  ·  · Vernier SASA · CDR  (canonical) · pLDDT  — ": 
    "VH-VL Angle · Interfacial Contacts · Vernier SASA · CDR Canonical Formats · pLDDT Confidence — Checked against clinical distributions",
    "⚗️ ": "⚗️ Chemical Modification Scans",
    " (NG/NS) ·  (DG/DS) ·  (M/W) ·  (NxS/T) ·  Cys — ": 
    "Deamidation (NG/NS) · Isomerization (DG/DS) · Oxidation (M/W) · Glycosylation (NxS/T) · Free Cys — Intercepting manufacturing liabilities early on",
    "（ vs VHH vs ），。。": 
    "Different modalities (mAbs vs. VHH vs. Bispecifics) command distinct evaluation criteria to avoid a \"one-size-fits-all\" framework. All metrics meticulously benchmark real clinical precedents.",

    # Slide 6
    "ADA  — <span>，</span>": "ADA Immunogenicity — <span>Candid Confrontation, Multi-Dimensional Benchmarking</span>",
    "ADA —— 100% 。。": 
    "ADA is extremely difficult to accurately predict—we refuse to mislead you into expecting 100% foresight. A multi-dimensional horizontal comparison system targeting analogous molecules acts as the only reliable anchor.",
    "🧬 ": "🧬 Sequence Dimension",
    "MHC-II 27  T  ·  · Parker ": 
    "MHC-II 27 Alleles T-Cell Epitope Scanning · Risk Site Curating Clustering · Parker Hydrophilicity Filtering",
    "🔬  + Germline": "🔬 Structure + Germline Dimensions",
    " Germline  ADA  ·  (SASA) · ": 
    "Historical ADA rates comparing analogous germlines · Surface Immunogenicity (SASA) · Germline Tolerance Validation",
    "📋 ": "📋 Clinical Verification",
    " 138  ADA  · / · MOA ": 
    "Horizontal benchmarking against 138 curated, rare ADA records · Target & Disease Dimensionality · Mechanisms of Action Grouping",
    "\"，，。\"": 
    "\"We cannot guarantee absolute zero immunogenicity, but rigorously supported by the most comprehensive clinical data supply chain, we will undoubtedly minimize the relative risk to the industry's lowest achievable level.\"",

    # Slide 7
    "<span></span>": "Antibody Engineering <span>Core Services</span>",
    "🧬 ": "🧬 Intelligent Humanization",
    " Germline  (842 ) ·  · 100% CDR  · VH-VL / VHH  (29  QA)": 
    "Machine Learning-driven Germline Selection (842 profiles) · Structure-guided back-mutations · 100% CDR conservation · Flexible for VH-VL / VHH formats (29 strict QA endpoints)",
    "⚡  (VAM)": "⚡ Virtual Affinity Maturation (VAM)",
    " → 6  ΔΔG  (EvoEF2 · PRODIGY · ThermoMPNN) →  → 5D  · ": 
    "Hotspot Discovery → 6-Tool ΔΔG Consensus validation (EvoEF2 · PRODIGY · ThermoMPNN) → Epistatic Combinatorial Design → 5D Filtering · Readily optimizing small-molecule haptens",
    "🔄 CDR  ": "🔄 CDR Redesign (IP Circumvention)",
    "ProteinMPNN de novo  · ， · 55%+ CDR  → ": 
    "ProteinMPNN de novo sequence reconstruction · Preserves 3D structure and functions while radically shuffling raw sequences · 55%+ CDR polymorphism engineered to reliably evade patent landscapes",
    "🔬  Binning": "🔬 Epitope Analysis & Binning",
    "BSA · H  ·  · π-π  · SC  ·  vs  Epitope binning · /": 
    "Buried Surface Area (BSA) · H-bonds · Salt bridges · π-π stacking · Shape Complementarity Scores · Multi-antibody Epitope binning · Blocking vs. Non-blocking functional assessments",

    # Slide 8
    "<span></span>": "Complex Modality <span>Design Platforms</span>",
    "🎯 CAR-T / NK / M ": "🎯 CAR-T / NK / M Intelligent Design",
    "ACTES  · 237 ， binder / spacer / TM / costim / signal · ": 
    "ACTES Computation Engine · 237 validated modular components spanning binders / spacers / TM / costimulatory / signal sequences · ML-driven recommendations deeply grounded on clinical precedence",
    "🔗 ADC ": "🔗 ADC Intelligent Design",
    "8  ·  →  → Linker → Payload → DAR → CMC · 100  ADC ": 
    "Holistic 8-Step System Pipeline · Target → Antibody → Linker → Payload → DAR → Chemistry, Manufacturing & Controls (CMC) · Sturdy backing by 100 clinical ADC programs",
    "↔️ ": "↔️ Bispecific Antibody Formatting",
    "134+  ·  + CMC  +  · pI  · Linker ": 
    "Benchmarked directly against 134+ clinical bispecific formats · Architecture Selection + Firm CMC Benchmarking + Heavy/Light Chain-pairing Refinement · pI Control Adjustments · Linker Structural Tuning",
    "💉 ": "💉 Next-Generation Vaccine Architecting",
    " InSynBio  ·  +  + mRNA  · IEDB ": 
    "Harnessing multiple proprietary InSynBio R&D toolkits · Neoantigen Discovery + Heterologous Peptide Profiling + Precision mRNA Multi-epitope Topologies · Firmly anchored by IEDB immunovariation libraries",

    # Slide 9
    " — <span>，</span>": "Comprehensive Deliverables — <span>Beyond Raw Data: Actionable Realities</span>",
    "——。": 
    "Our definitive deliverables function as transparent structural diagnostic protocols radiating unequivocal directional advice—emphatically not an obscure spreadsheet dump.",
    "<strong></strong><span>VH/VL · VHH · PDB</span>": "<strong>Sequence Initialization</strong><span>VH/VL · VHH · PDB</span>",
    "<strong>ANARCI </strong><span>Kabat + IMGT </span>": "<strong>ANARCI Annotations</strong><span>Kabat & IMGT Standard</span>",
    "<strong></strong><span>ABodyBuilder2 / AF2</span>": "<strong>Precision Modeling</strong><span>ABodyBuilder2 / AF2</span>",
    "<strong></strong><span>CMC ·  · </span>": "<strong>Multimodal Evaluation</strong><span>CMC · Immunogenicity</span>",
    "<strong></strong><span>1,142 </span>": "<strong>Clinical Cross-Benchmarking</strong><span>1,142 Sequence Contexts</span>",
    "<strong></strong><span></span>": "<strong>Rigorous Expert Audit</strong><span>Immunologist Sign-offs</span>",
    "<strong>3-5</strong><span>PDF / Markdown</span>": "<strong>Rapid Turnaround Delivery</strong><span>PDF / Markdown Format</span>",
    "🐭 ": "🐭 Transgenic Murine Extracts",
    " +  +  + CMC + ": "Raw Sequences + 3D Structure + Contact Interfaces + CMC + Immunogenicity Analytics",
    "🔬 ": "🔬 Comprehensive Humanization",
    " ( Vernier +  + )": "Full-stack Services Matrix integrating Vernier refinements, Golden Pairing configurations, and detailed humanization modeling",
    "🧪 /": "🧪 Fully-Human / 3rd-Party Audits",
    " +  +  + CMC ": "Sequences + 3D Structural Mappings + Holistic Multi-mAb Panel Ranking + Conclusive CMC Guidance parameters",

    # Slide 10
    " — <span></span>": "Real-world Success Cases — <span>End-to-End Pipeline Executions</span>",
    "muMAb4D5 ": "muMAb4D5 Humanization",
    "4  · 100% CDR ": "4 Precise Back-Mutations · 100% CDR Fidelity",
    "IGHV3-23 + IGKV1-39 ": "IGHV3-23 + IGKV1-39 Precursor Pairings",
    "15  CMC ": "Successfully penetrated 15 intensive CMC strictures",
    "muMAb4D5 CMC ": "muMAb4D5 Deep CMC Assessment",
    "VH84 N→Q ": "Informed VH84 N→Q single mutation deployment",
    "Fv RMSD  0.28 Å": "Immaculate Fv RMSD constraint of just 0.28 Å",
    "VH → VHH ": "VH → VHH Nanobody Structural Transformation",
    "100% CDR  · SASA ": "Faultless 100% CDR Retention · SASA Resurfacing",
    "ADI 66.66 >  63.17": "Aggression Index ADI 66.66 > Competitor metric (63.17)",
    " RMSD 0.054 Å": "Overall geometric fidelity achieving RMSD 0.054 Å",
    " VGRW ": "Streamlined single-push VGRW synthetic adaptation",
    "VHH ": "Extensive VHH Affinity Maturation Solutions",
    "247  · 5D ": "Complete 247-Mutation Landscape Exhaustive Scan · 5D Filtrations",
    " G49A+F112L ": "Intricate Dual-mutation G49A+F112L Epistatic Enhancements",
    " +70%": "Drastic Interfacial contacts escalation +70%",
    "CDR ": "De novo CDR Structural Redesign",
    "55% CDR  · ": "55% Active CDR Polymorphisms · IP Freedom-to-Operate Expansion",
    "": "Advanced Physics-guided Polarity-focused mature engineering",
    "13×  3.75 nM": "Formidable 13× Affinity Recovery normalizing to 3.75 nM",
    " VHH ": "Tuning Bispecific VHH Assembly Parameters",
    "pI 8.2 → 6.8 ": "Crucial pI Shift optimization 8.2 → 6.8 ensuring Colloidal Stability",
    "4.8× IC90 ": "Measured 4.8× functional IC90 leap encompassing broad variants",
    "GS-8 linker ": "Calculated isolation of GS-8 linker topological configuration",

    # Slide 11
    "<span></span>": "Navigating Multimodal <span>Complex Scenarios</span>",
    "🦠 CAR-M ": "🦠 Macrophage CAR-M Cellular Therapy",
    "<strong style=\"color:#c4b5fd\"> Anti-CIDRα1</strong><br>CIDRα1.4 + CIDRα1.7  · TLR4  · M1  · ACTES 237 ": 
    "<strong style=\"color:#c4b5fd\">Parasitic Malaria Anti-CIDRα1 Defense</strong><br>CIDRα1.4 + CIDRα1.7 dual targeting models · Robust TLR4 intracellular signaling domains · Engineered M1 Polarization · Rigorous ACTES 237-Component Screenings",
    "💊  VAM": "💊 Synthetic Fentanyl Hapten Binding (VAM)",
    "<strong style=\"color:#fde68a\"></strong><br>ΔΔG −5.53 kcal/mol · HADDOCK3 −68.4 score · ΔTm +3.8°C · ": 
    "<strong style=\"color:#fde68a\">Precise Small Molecule Affinity Optimization</strong><br>Energy yield ΔΔG −5.53 kcal/mol · Compelling HADDOCK3 −68.4 structural scoring metric · Exceptional ΔTm +3.8°C augmentation · Clinically devoid of clustering risks",
    "🔍 PD-L1 ": "🔍 Granular PD-L1 Immuno-Epitope Analysis",
    "<strong style=\"color:#5eead4\"></strong><br>Ab1 (blocking) vs Ab2 (non-blocking) · PRODIGY ΔG −10.8 vs −7.3 · ": 
    "<strong style=\"color:#5eead4\">Intricate Competitive Relationship Mapping</strong><br>Differentiating profiles Ab1 (blocking functionality) vs Ab2 (non-blocking passivity) · Absolute PRODIGY ΔG distinction −10.8 vs −7.3 · Intimate Residue-level interfacial charting",
    " 800–1300 ，、、—— Demo。": 
    "Each linked case study portal embeds 800–1,300 lines of uncompromising technical rigor—complete with navigable 3D visualizations, unredacted structural sequences, and step-wise logical rationales tailored flawlessly for commanding live on-screen demonstrations.",

    # Slide 12
    "AbEngineCore — <span>30+ </span>": "AbEngineCore — <span>The 30+ Suite Decision Matrix Engine</span>",
    "><": ">Structural Prediction<",
    "><": ">Molecular Docking<",
    "><": ">Generative Sequence Design<",
    "> & <": ">Stability Profiles & Affinity Metrics<",
    "><": ">Immunogenicity Detection<",
    "><": ">Core Sequence Annotations<",
    "><": ">Overall Sequence Biological Fitness<",
    "><": ">Diffusion-based Modeling Output<",

    # Slide 13
    "<span></span>": "Transparent & Flexible <span>Partnership Structuring</span>",
    "📋 ": "📋 On-Demand Tactical Sprints",
    "、、。": "Specialized modules surgically aimed at individualized molecular assessments, extensive humanization drives, and direct affinity maturation maneuvers.",
    "→</span>  → NDA ": "→</span> Formally submit your query sequence via secure email → Institute a comprehensive Non-Disclosure Agreement (NDA)",
    "→</span> 3–5 ": "→</span> Confident 3–5 day delivery cadence of highly-detailed, expert-curated analytical manifests",
    "→</span> ": "→</span> Outstanding deliverables strictly backed by customer satisfaction—conditional balance waivers if rigorous standards fall materially short",
    "→</span>  50% ": "→</span> Fostering academic collaboration granting a solid 50% project cost refund upon prominent peer-reviewed publication attribution",
    "🤝  AI ": "🤝 Sustained Enterprise AI Consultants",
    "/，，\"\"。": "Secured through Monthly or Quarterly retainers actively immersing deeply into your organization's core pipeline progression, effectively serving as an integrated elite \"External Brain\".",
    "→</span> ": "→</span> Granted unchecked on-demand capitalization of our complete computational toolbox array and exclusive robust clincal database archives",
    "→</span>  R&D ": "→</span> Available explicit participation and expert input framing pivotal internal operational R&D strategic sessions",
    "→</span> ": "→</span> Representing unequivocally the most optimal strategic investment option guiding long-term sustained pipeline resilience",
    "→</span> NDA ，": "→</span> Operates heavily under NDA-first confidentiality guarantees rigidly ensuring your private assets perpetually bypass communal public AI training layers",

    # Slide 14
    "": "Your Next Step Begins With a Single Email",
    " AI ，。<br>\n      ，。": 
    "We remain decidedly distinct from a conventional AI software subscription—we are your dedicated, invested strategic biotherapeutic R&D decision partners.<br>\n      Our foremost directive is delivering clinical judgment alongside you; not merely computing background script operations.",
    "：AI De novo  — ，": 
    "Charting Future Horizons: Masterminding AI De novo Protein Conceptualization — Methodically severing dependencies on rigid natural scaffold parameters to pioneer entirely untethered, pristine binding interfaces."
}

for ch, en in translations.items:
    content = content.replace(ch, en)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Translation completed.")
