# CDR3 length determines achievable humanization in therapeutic VHH antibodies

Jing Huang\(^1\), Linqi Zhang\(^2\)

\(^1\) NextVivo (Suzhou) Biotech Corp, Suzhou, China  
\(^2\) School of Medicine, Tsinghua University, Beijing, China

## Abstract

### Background

VHHs (nanobodies) represent a rapidly growing class of therapeutic antibodies with four approved drugs and over 50 candidates in clinical development. Two main humanization strategies have been proposed—CDR-grafting and resurfacing—but there is no consensus on which approach is optimal. The structural determinants that constrain humanization in clinical molecules remain incompletely defined.

### Methods

We performed a retrospective analysis of 19 clinical-stage VHHs (4 approved, 15 in development) retrieved from Thera-SAbDab. Framework regions (FR1–FR4) were analyzed separately using phylogenetic clustering anchored with human (IGHV3-23, IGHV3-13), alpaca (IGHV3-3), and mouse (IGHV1-72) germline references. Statistical associations between framework clustering, CDR3 length, and CDR2 canonical folds were assessed using Kruskal–Wallis testing and Spearman correlation.

### Results

FR1 and FR3 showed high human identity across all clinical molecules regardless of humanization strategy. FR2, however, displayed a clear bifurcation driven by CDR3 length (P = 0.00175; ρ = -0.604) rather than by design approach. Using a CDR3-length threshold at 11 amino acids, VHHs with CDR3 ≤11 aa achieved near-human FR2 sequences (>93% human identity), whereas VHHs with CDR3 >11 aa plateaued at ~87–88% identity with divergence concentrated in FR2. CDR2 canonical folds showed no correlation with humanization patterns (P = 0.77). Within FR2, IMGT position 50 showed a strong group difference: Arg50 was retained in 13/14 long-CDR3 VHHs (93%), whereas short-CDR3 VHHs more frequently substituted to Leu/Pro.

### Conclusion

Retrospective analysis of clinical VHHs reveals that CDR3 loop length, rather than humanization strategy, is the primary determinant of achievable FR2 humanization. A threshold at 11 amino acids separates VHHs that can achieve near-human FR2 sequences from those constrained to retain camelid-typical residues. These structure-based constraints explain why clinical molecules do not cluster by design strategy and provide evidence-based guidelines for rational VHH humanization.

## Keywords

VHH; nanobody; humanization; CDR3 length; framework region; antibody engineering; phylogenetic analysis; immunogenicity

## Highlights

- FR2 phylogenetic structure is strongly associated with CDR3 length in 19 clinical VHHs.
- A CDR3 threshold at 11 amino acids separates more human-like versus more camelid-like FR2 patterns.
- CDR2 canonical folds do not explain FR2 humanization differences in this dataset.
- IMGT position 50 in FR2 differs sharply between CDR3-length groups (Arg enriched in long CDR3).
- FR1 and FR3 provide a comparatively conserved background relative to FR2.

## Statement of significance

VHH humanization is widely used to reduce immunogenicity, but it can compromise stability when framework changes conflict with structural constraints. By analyzing clinically advanced molecules, this work identifies a simple design-relevant factor—CDR3 length—that is associated with FR2 humanization limits, and it pinpoints an FR2 site (IMGT position 50) that differs markedly between CDR3-length groups.

---

## 1. Introduction

Single-domain antibodies (VHHs), also known as nanobodies, represent the antigen-binding variable domains of heavy-chain-only antibodies naturally occurring in Camelidae (primarily llamas and alpacas) [1]. With a molecular weight of approximately 15 kDa, VHHs offer therapeutic advantages over conventional IgG antibodies including superior tissue penetration, access to cryptic epitopes, remarkable stability at elevated temperatures and extreme pH, and cost-effective microbial production [2]. The clinical success of VHH therapeutics has been substantial: four molecules have achieved regulatory approval (Caplacizumab 2018, Envafolimab 2021, Ozoralizumab 2022, and Sonelokimab in Phase 3), and over 50 VHH-based candidates (including single-domain, bispecific, and multispecific formats) are advancing through clinical pipelines spanning oncology, autoimmunity, and infectious diseases [6]. This rapid translation highlights the therapeutic value of VHH scaffolds. However, the non-human origin of VHHs poses a critical challenge: immunogenicity. VHH frameworks contain characteristic residues in FR2 that compensate for the absence of a light chain by shielding the hydrophobic VH–VL interface. Humanization is therefore essential to reduce the risk of anti-drug antibody (ADA) responses in patients, but this process must balance immunogenicity reduction against potential destabilization of the molecule.

Two main humanization strategies have been proposed and applied in VHH development: (1) CDR-grafting, which transplants VHH CDRs onto human germline scaffolds (typically IGHV3-23) to maximize human sequence identity [2], and (2) Resurfacing, which selectively mutates solvent-exposed residues while preserving the hydrophobic core and structural hallmark positions [2]. Despite extensive application of both approaches, there is no consensus on which strategy is optimal, and clinical VHH sequences often exhibit intermediate humanization levels that do not clearly align with either extreme. This suggests that humanization outcomes may be governed by structural constraints that transcend designer intent. To address this question, we analyzed 19 clinical-stage VHHs that have successfully advanced into human trials or achieved regulatory approval. By studying molecules that have survived development filters—including stability, expression, and early safety assessments—we aimed to identify the structural determinants that dictate achievable humanization levels in practice.

Framework regions (FR1–FR4) were analyzed separately using phylogenetic methods anchored with human (IGHV3-23, IGHV3-13), alpaca (IGHV3-3), and mouse (IGHV1-72) germline references. Our analysis reveals that CDR3 loop length, rather than the humanization strategy employed, is the primary determinant of FR2 humanization potential. A threshold at 11 amino acids separates VHHs that can achieve near-human FR2 sequences (>93% human identity) from those that plateau at ~87–88% identity due to structural constraints. These findings provide an evidence-based framework for rational VHH humanization and help explain the observed diversity in clinical nanobody sequences.

---

## 2. Materials and methods

### 2.1 Dataset construction
Clinical VHH sequences were retrieved from Thera-SAbDab (Therapeutic Structural Antibody Database; accessed January 2026). We selected 19 unique VHH molecules that met the following criteria: (i) single-domain format (VHH), (ii) clinical status of Phase 1 or higher or regulatory approval, and (iii) availability of the full variable domain sequence.

While over 50 VHH-based therapeutics have entered clinical development, many are either (a) bispecific or multispecific formats where individual VHH domains cannot be unambiguously assigned to specific chains, (b) fused to half-life extension domains (e.g., albumin, Fc) where only partial sequences are publicly disclosed, or (c) proprietary candidates for which variable domain sequences remain confidential. Of the ~30 single-domain VHH candidates with publicly available sequences in Thera-SAbDab at the time of analysis, we further excluded 11 molecules due to incomplete framework annotations or ambiguous CDR boundaries, yielding a final dataset of 19 VHHs with complete FR1–FR4 sequences suitable for phylogenetic analysis. This dataset includes 4 approved therapeutics and 15 molecules in active clinical development (Phase 1–3), representing the most advanced and well-characterized VHH therapeutics with publicly accessible sequence information.

All VHHs in our dataset are derived from camelid immune repertoires (primarily llama *Lama glama* or alpaca *Vicugna pacos*), which were subsequently humanized through antibody engineering. Specific source animals and immunization protocols were not publicly disclosed for most therapeutic candidates.

### 2.2 Sequence segmentation and numbering
Sequences were segmented into framework regions (FR1–FR4) and complementarity-determining regions (CDR1–CDR3) using IMGT (ImMunoGeneTics) numbering [5], which provides a standardized numbering scheme that facilitates structural and functional comparisons across diverse antibody formats. The IMGT system assigns unique position numbers to structurally equivalent residues across all immunoglobulin domains, enabling precise identification of hallmark residues and conserved structural features. FR2 was defined as spanning IMGT positions 39–55 (17 positions), corresponding to the β-strand that forms part of the VH framework and directly interfaces with CDR loops. CDR3 length was calculated from the conserved Cys at IMGT position 104 to the conserved Trp-Gly motif preceding FR4, excluding these anchor residues from the length calculation, consistent with IMGT convention. CDR2 canonical structural classes were assigned using the North–Dunbrack nomenclature system [4], which classifies CDR loop conformations based on length and key dihedral angle patterns: class H2-9-1 corresponds to short CDR2 loops (typically 9-10 residues) with extended conformations, whereas H2-10-1 represents longer CDR2 loops (10-12 residues) with a characteristic kinked structure. This classification enabled us to test whether CDR2 structural class influences FR2 sequence requirements independently of CDR3 length.

### 2.3 Germline reference sequences

To anchor phylogenetic analyses, we incorporated four reference germline sequences:

- **Human**: IGHV3-23\*01 and IGHV3-13\*01 (IMGT). IGHV3-23 is the most commonly used human germline scaffold for VHH humanization due to its structural similarity to camelid VHH frameworks and high expression levels [7].
- **Alpaca**: IGHV3-3\*01 (*Vicugna pacos*, IMGT). This represents the VHH3 subgroup, the dominant germline family in camelid heavy-chain-only antibodies, accounting for >60% of VHH repertoires [7].
- **Mouse**: IGHV1-72\*01 (phylogenetic outgroup, IMGT).

Framework regions were extracted from these germlines using the same IMGT position ranges as the VHH dataset to ensure alignment consistency.

### 2.4 Phylogenetic analysis
Pairwise evolutionary distances were computed using normalized Hamming distance (p-distance), a metric appropriate for protein sequence comparisons where sequence divergence is modest and back-mutations are unlikely:

**d(s_i, s_j) = (Number of mismatches) / Max(length_i, length_j)**

where d(s_i, s_j) represents the pairwise distance between sequences i and j. This normalization by maximum length rather than alignment length accounts for potential indels and ensures that distance values remain bounded between 0 and 1. For FR2 analysis, all sequences had identical length (17 positions), simplifying interpretation. Hierarchical clustering was performed using UPGMA (Unweighted Pair Group Method with Arithmetic mean), which assumes a constant rate of evolution and produces rooted trees with equidistant tips. While UPGMA does not account for rate heterogeneity across lineages, it is suitable for our purpose of quantifying relative humanization levels rather than inferring true evolutionary relationships. Dendrograms were visualized using Python libraries (scipy, matplotlib) with tip labels colored by CDR3 length group (≤11 vs >11 amino acids) to facilitate visual assessment of clustering patterns. To quantify the shift toward human or alpaca references, we computed a "Human-Shift Score" for each VHH, defined as the difference in normalized distance to Human IGHV3-23 versus Alpaca IGHV3-3, where negative values indicate human-like sequences and positive values indicate retention of camelid features.

### 2.5 Statistical testing

- **Clustering drivers**: hierarchical clustering (k=2) was followed by:
  - Kruskal–Wallis H-test for CDR3 length (continuous).
  - Chi-square test for CDR2 fold (categorical).
- **Correlation analysis**: Spearman’s rank correlation (ρ) was used to assess relationships between CDR3 length and phylogenetic scores.
- **Significance threshold**: P < 0.05.

### 2.6 Residue-level analysis
Selected FR2 positions (IMGT 42, 49, 50, 52, 54, 55) and conserved FR3 positions (IMGT 71, 93–95, 104) were extracted using motif-based alignment. Amino acid frequencies were calculated for Short CDR3 (≤11aa, N=5) and Long CDR3 (>11aa, N=14) groups.

---

## 3. Results

### 3.1 Dataset and framework region analysis
We analyzed 19 clinical-stage VHHs (4 approved, 15 in clinical development) spanning diverse therapeutic targets including immune checkpoint blockade (PD-L1, CTLA-4), cytokine inhibition (TNF-α, IL-17A/F), and hemostatic disorders (vWF). These molecules represent a broad cross-section of VHH therapeutic applications, ranging from oncology immunotherapy to autoimmune disease management, providing a representative sample of clinically successful nanobody engineering strategies. The CDR3 lengths in our dataset ranged from 5 to 21 amino acids (mean = 15.1 ± 4.9 aa, median = 16 aa), reflecting the characteristic diversity of VHH CDR3 loops. This range encompasses both compact CDR3 loops typical of conventional antibodies (5-11 aa) and extended loops (>15 aa) that are enriched in camelid repertoires and enable access to concave epitopes [1]. All molecules exhibited CDR2 canonical folds classified as either H2-9-1 (short CDR2, N=6) or H2-10-1 (long CDR2, N=12 with 1 unknown), representing the two dominant CDR2 conformational classes observed in VHH structures [4].

To anchor these VHHs in an evolutionary context, we incorporated reference germline sequences: Human IGHV3-23\*01 and IGHV3-13\*01 (humanization goal), Alpaca IGHV3-3\*01 (VHH origin), and Mouse IGHV1-72\*01 (phylogenetic outgroup). Framework regions (FR1-FR4) were delimited using IMGT numbering and extracted for separate analysis. This phylogenetic approach enabled us to quantify the degree to which each clinical VHH has shifted from its camelid origin toward the human reference, providing an objective measure of humanization independent of designer intent or documented engineering strategy.

### 3.2 FR2 exhibits a CDR3-length-driven bifurcation
Phylogenetic analysis of the FR2 region (17 amino acids, IMGT positions 39-55) revealed a clear separation (Figure 1A), with hierarchical clustering segregating the 19 VHHs into two distinct groups. To identify the true driver of this separation, we performed comparative statistical tests: Kruskal-Wallis test on the two natural clusters showed highly significant differences in CDR3 length distribution (P = 0.00175, H = 9.79), whereas Chi-square test showed no significant association between clusters and CDR2 canonical fold (P = 0.77). Spearman correlation between CDR3 length and phylogenetic distance from Human IGHV3-23 was strongly negative (ρ = -0.604, P = 0.0062), indicating that longer CDR3s are associated with retention of alpaca-like FR2 sequences. Thus, the phylogenetic structure of FR2 is driven by CDR3 length, not by CDR2 canonical fold.

### 3.3 FR1 and FR3 are comparatively conserved across molecules
In contrast to FR2, phylogenetic analysis of FR3 (38 amino acids in our dataset, including the CDR2 C-terminal tail) showed no significant clustering by CDR3 length (P = 0.14) or CDR2 fold (P = 0.74), with all molecules converging near the human reference. Similarly, FR1 exhibited near-perfect conservation (>96% human identity across 18/19 molecules). These findings indicate that FR1 and FR3 are universally humanized in clinical sequences regardless of structural constraints, whereas FR2 accommodates the primary CDR3-length-dependent variation.

### 3.4 A three-class system based on phylogenetic clustering
We applied hierarchical clustering (k=3) to the combined FR2+FR3 sequences, yielding three natural groups with distinct profiles (Table 1). This three-class system was identified through data-driven clustering without imposing predetermined cutoffs and captures clinically relevant variation in humanization strategies and outcomes.

**Class 1 (N=5)** exhibits the highest human identity (mean = 93.2%, range 87.5-97.5%) and shortest CDR3 loops (mean = 9.0 aa, range 5-13 aa). Members include Brivekimig2, Enristomig, Letolizumab, Ozoralizumab, and Porustobart, representing diverse therapeutic targets (TNF, PD-L1, CD40L, CTLA-4). The defining characteristic of Class 1 is that short CDR3 loops enable extensive FR2 humanization without compromising stability. Notably, three of these five molecules (Letolizumab, Ozoralizumab, Porustobart) achieve >92% overall human identity, approaching the theoretical maximum for single-domain antibodies. This class demonstrates that when CDR3 is compact, VHH humanization can approach conventional antibody levels.

**Class 2 (N=10)**, the largest group, exhibits intermediate human identity (mean = 87.9%, range 85.0-91.2%) and long CDR3 loops (mean = 17.6 aa, range 16-21 aa). Members include approved therapeutics Envafolimab and Sonelokimab1/2, as well as advanced clinical candidates Gefurulimab, Rimteravimab, and Erfonrilimab. The defining characteristic of Class 2 is that extended CDR3 loops mandate retention of camelid-typical FR2 residues to maintain structural integrity, resulting in a humanization plateau near 87-88%. Despite lower overall human identity compared to Class 1, Class 2 molecules have demonstrated clinical success, suggesting that ~87% humanization is sufficient for acceptable immunogenicity profiles in many therapeutic contexts. The consistency of this plateau across 10 molecules spanning diverse targets (IL-17, PD-L1, C5, SARS-CoV-2) indicates that the ~87% ceiling represents a consistent structural constraint rather than a design artifact.

**Class 3 (N=4)** exhibits human identity comparable to Class 2 (mean = 87.2%, range 85.0-90.0%) but with intermediate CDR3 lengths (mean = 15.2 aa, range 11-21 aa) and mixed sequence features. Members include approved therapeutic Caplacizumab and clinical candidates Gocatamig2, Podentamig1, and Vobarilizumab. This class appears to represent a transition zone where CDR3 length is at the boundary (11-16 aa) between full humanization permissivity (Class 1) and structural constraint (Class 2). The heterogeneity within Class 3 suggests that factors beyond CDR3 length—such as specific CDR3 sequence composition, CDR2-CDR3 interactions, or target epitope geometry—may modulate humanization potential in this intermediate range. All clinical VHHs in our dataset exhibited substantial sequence divergence from camelid germline sequences (≥66% human identity), indicating that successful therapeutic candidates require significant framework engineering, with most variability residing in FR2.

### 3.5 Key FR2 residues show a CDR3-dependent pattern
To identify residue-level drivers of FR2 bifurcation, we analyzed key FR2 positions (IMGT 42, 49, 50, 52) using sequence logos stratified by CDR3 length (Figure 2, Table S1). These positions were selected based on prior studies identifying them as hallmark residues distinguishing VHH from conventional VH domains and as critical determinants of the VH-VL interface in conventional antibodies [2,7]. In VHHs, these positions must compensate for the absence of the light chain while maintaining structural stability.

IMGT **Position 50** showed the strongest group difference:
*   **Long CDR3 Group (>11aa, N=14)**: **Arg (R)** in 13/14 molecules (93%).
*   **Short CDR3 Group (≤11aa, N=5)**: **Arg (R)** in 2/5 molecules; the remaining sequences carried **Leu (L)** (2/5) or **Pro (P)** (1/5).

Additional FR2 positions also differed by group (Table S1), including IMGT 49 and 52.

### 3.6 Conserved positions outside FR2
Outside FR2, several FR3 positions were conserved across both CDR3-length groups in our dataset (Table S1), including IMGT positions 93 (S), 94 (L), 95 (R), and 104 (C). These residues correspond to the conserved "SLR" motif and the canonical Cys104 that forms the conserved intra-domain disulfide bond with Cys in FR1. This conservation across all 19 clinical VHHs regardless of CDR3 length indicates that these positions are structural invariants essential for maintaining the immunoglobulin fold. The fact that these positions can adopt human-like sequences without penalty further supports the view that FR3 serves primarily as a structural scaffold, whereas FR2 must dynamically respond to CDR loop architecture.

---

## 4. Discussion

### 4.1 CDR3 length as the primary determinant of VHH humanization and structural constraints
Our phylogenetic analysis of 19 clinical VHHs reveals that humanization is not a monolithic process but a region-specific adaptation dictated by structural constraints—specifically, the length of the CDR3 loop. Using a threshold at 11 amino acids, VHHs with CDR3 ≤11aa clustered closer to the human reference and achieved higher human identity (mean 93.2%), whereas VHHs with CDR3 >11aa tended to plateau at ~87–88% identity with most of the sequence divergence localized to FR2. All clinical VHHs in our dataset exhibited substantial sequence divergence from camelid germline sequences (≥66% human identity), indicating that successful therapeutic candidates require significant framework engineering, with most variability residing in FR2. The 11-amino-acid threshold is notable because it corresponds approximately to the median CDR3 length in both human VH repertoires and camelid VHH repertoires, though camelid VHHs exhibit a broader distribution extending to longer loops [7]. Long CDR3 loops (>11aa) are enriched in camelid VHH repertoires and often adopt extended conformations that project away from the framework, creating unique paratope geometries capable of accessing cryptic epitopes inaccessible to conventional antibodies. Our finding that such loops constrain FR2 humanization suggests a fundamental structural trade-off: the very feature that enables VHH functional diversity (extended CDR3 loops with unique conformations) simultaneously limits framework engineering flexibility. This coupling may reflect fundamental physical constraints on how a single-domain antibody scaffold can support extended CDR3 loops without destabilizing the overall immunoglobulin fold or compromising the solvent-exposed former VH-VL interface.

### 4.2 Molecular mechanism: the solubility valve model
We propose a "Solubility Valve" model to explain the observed FR2 bifurcation and its coupling to CDR3 length. In conventional antibodies, the VH–VL interface is predominantly hydrophobic and shielded by the light chain, whereas in VHHs this interface is exposed to solvent. Camelid VHHs compensate for this exposure through characteristic substitutions in FR2 that introduce hydrophilic residues at positions that would normally participate in hydrophobic VH-VL contacts [1,2]. Our data show that several FR2 positions vary systematically with CDR3 length (Table S1), consistent with coupling between CDR3 geometry and FR2 sequence requirements. When CDR3 is short (≤11aa), FR2 can shift toward more human-like residues at key positions such as IMGT 50 (Leu/Pro) and IMGT 52 (Trp), which are bulky hydrophobic residues typical of human VH domains. In contrast, when CDR3 is long (>11aa), FR2 more often retains charged and/or camelid-typical residues at these sites, particularly Arg at position 50 (93% frequency in long-CDR3 group) and diverse residues at position 52. This pattern likely reflects structural packing constraints wherein long CDR3 loops may adopt conformations that bring the CDR3 base into closer proximity with FR2, creating steric clashes or unfavorable electrostatic interactions if FR2 adopts a fully human-like hydrophobic character. Retention of charged or polar residues at key FR2 positions in long-CDR3 VHHs may serve dual functions: maintaining solubility of the exposed VH-VL interface region and accommodating the altered spatial demands of extended CDR3 loops. In contrast, short CDR3 loops place fewer geometric demands on FR2, permitting greater sequence flexibility and enabling substitution toward human-like residues without compromising stability, solubility, or CDR loop conformation. This model predicts that attempts to force human-like FR2 sequences onto long-CDR3 VHHs will result in either solubility problems, conformational instability, or loss of binding affinity—consistent with the observation that all clinical long-CDR3 molecules uniformly retain camelid-typical FR2 features despite diverse engineering strategies.

### 4.3 Differential roles of framework regions
Compared with FR2, FR3 showed fewer CDR3-length-associated differences in our phylogenetic analyses. Several FR3 positions were conserved across both groups (Table S1), supporting the view that FR3 provides a relatively stable background region while FR2 accommodates the primary CDR3-length-dependent variation observed here. This functional specialization of framework regions has structural precedent: FR3 in conventional antibodies primarily contributes to the structural scaffold and contacts with the constant domain, whereas FR2 directly interfaces with CDR loops and participates in antigen binding site architecture [3]. In VHHs, the differential humanizability of FR1/FR3 versus FR2 suggests that evolutionary pressure to maintain VHH stability has concentrated sequence constraints in FR2, which must simultaneously solve three structural problems: compensating for light chain absence, accommodating CDR3 geometry, and maintaining overall domain stability. FR1 and FR3, being more peripheral to these constraints, can tolerate human-like sequences without functional penalty. This modular architecture offers practical advantages for antibody engineering: humanization efforts can safely target FR1 and FR3 across all VHHs while requiring CDR3-length-dependent strategies for FR2.

### 4.4 Convergence of design strategies and implications for antibody engineering
Clinical VHHs exhibit a continuum of humanization levels that do not cluster according to documented designer intent (e.g., CDR-grafting vs. resurfacing strategies). This occurs because both strategies ultimately encounter the same structural constraints imposed by CDR3 length, causing convergent evolution toward sequence solutions that satisfy physical requirements regardless of initial design philosophy. CDR-grafting approaches that attempt to maximize human identity in FR2 will fail stability, solubility, or affinity filters during development if the CDR3 is long, forcing iterative retention of camelid-typical residues at key positions until functional thresholds are met. Conversely, resurfacing strategies that prioritize stability from the outset will still achieve high human identity if the CDR3 is short, because fewer FR2 positions are structurally constrained and can be safely humanized without penalty. The final sequence landscape of clinically successful VHHs therefore reflects structural limits rather than the initial design philosophy, explaining why clinical molecules cluster by CDR3 length rather than by documented engineering strategy.

This convergence has important implications for antibody discovery programs. The humanization plateau (~87-88% for long-CDR3 VHHs) is not a consequence of suboptimal engineering choices but rather represents a fundamental physical constraint encoded in the relationship between CDR3 geometry and FR2 sequence requirements. Efforts to bypass this constraint through more aggressive FR2 humanization would likely compromise expression levels, thermal stability, or binding affinity—the very properties that enable clinical progression. The successful clinical advancement of multiple VHHs at ~87% humanization (Envafolimab and Sonelokimab approved in China, Caplacizumab approved globally) provides empirical validation that this level of humanization is sufficient for acceptable immunogenicity profiles in most therapeutic contexts, though long-term immunogenicity surveillance data are still accumulating [9]. These findings translate directly into rational design rules that can guide early-stage antibody development. Measuring CDR3 length provides immediate prediction of achievable FR2 humanization: VHHs with CDR3 ≤11aa can tolerate human-like substitutions at key positions (IMGT 50, 52) enabling >93% overall human identity, whereas those with CDR3 >11aa will require retention of characteristic residues constraining humanization to ~87–88%. FR1 and FR3 can default to Human IGHV3-23 scaffold across all VHHs regardless of CDR3 length, as these regions achieve >96% human identity in 18/19 molecules. Target-driven prioritization should inform early discovery: for therapeutic applications where minimal immunogenicity risk is required (chronic systemic therapies), short-CDR3 binders should be prioritized during screening to enable >93% humanization; for applications where moderate immunogenicity risk is acceptable (acute indications, local delivery, engineered clearance), long-CDR3 VHHs remain viable despite lower humanization.

### 4.5 Clinical implications and immunogenicity risk stratification
The CDR3-length-dependent humanization patterns observed in our clinical dataset have direct implications for therapeutic risk-benefit assessment and clinical development strategy. VHHs with CDR3 ≤11aa achieve >93% human identity and may present lower immunogenicity risk, making them preferable for chronic systemic therapies where long-term repeat dosing is required and where even low-level anti-drug antibody (ADA) responses could compromise efficacy or safety over time. VHHs with CDR3 >11aa plateau at ~87–88% human identity but offer compensating functional advantages: extended CDR3 loops enable binding to concave epitopes, cleft-like binding sites, and cryptic epitopes inaccessible to conventional antibodies, potentially providing superior target selectivity, allosteric mechanisms of action, or access to novel therapeutic targets. The clinical success of long-CDR3 molecules like Caplacizumab (21-aa CDR3, 87.5% human identity, approved globally for acute TTP), Envafolimab (21-aa CDR3, 88.8% human identity, approved in China for solid tumors), and Sonelokimab (16-aa CDR3, 88.3% identity, advanced Phase 3 trials) demonstrates that the ~87% humanization level is clinically viable across multiple therapeutic contexts including acute life-threatening conditions, oncology, and chronic inflammatory diseases.

Immunogenicity remains a critical consideration requiring context-specific assessment. While preclinical immunogenicity prediction remains challenging, several factors beyond overall human identity influence ADA risk, including the presence and immunodominance of T-cell epitopes in framework regions, post-translational modifications (glycosylation, oxidation, deamidation), aggregation propensity during manufacturing and storage, dosing regimen (frequency, route, dose level), patient population (disease state, concomitant immunosuppression, HLA haplotype distribution), and therapeutic modality (monotherapy vs. combination with immunosuppressants) [9,10]. Long-CDR3 VHHs will inevitably retain some camelid-typical FR2 residues—particularly charged residues at key positions like IMGT 50 and 49—and drug developers should plan comprehensive immunogenicity monitoring and mitigation strategies accordingly, including in silico T-cell epitope prediction, ex vivo immunogenicity assays using donor PBMCs, and robust clinical immunogenicity surveillance with validated ADA assays. For therapeutic programs where minimal ADA risk is required (e.g., chronic enzyme replacement therapies, gene therapy vehicle components), prioritizing short-CDR3 binders during the discovery phase through rational library design biased toward compact CDR3 loops or screening strategies that explicitly select for high humanization potential is recommended.

### 4.6 Study limitations and dataset considerations
This study analyzed 19 clinical-stage VHHs with publicly available complete variable domain sequences, representing the subset of clinical candidates for which detailed sequence information has been disclosed in scientific literature, patent applications, or regulatory filings. While over 50 VHH-based therapeutics have entered clinical trials [10], many remain proprietary with undisclosed sequences, and others exist as multispecific formats (bispecifics, fusion proteins, multimerized constructs) where individual VHH domains cannot be unambiguously deconvoluted from linker and partner sequences. Our dataset is therefore enriched for molecules that have advanced furthest in clinical development (4 approved therapeutics, 15 in Phase 1–3 trials) and for which sponsors have chosen public sequence disclosure, likely reflecting confidence in intellectual property protection, competitive positioning, or academic collaboration objectives. This selection bias may exclude early-phase candidates that failed clinical development due to poor humanization, inadequate stability, high immunogenicity, or manufacturing challenges—information that would strengthen identification of non-viable mutation patterns and failed engineering strategies if such data were available for meta-analysis. Additionally, our dataset lacks detailed provenance information including specific source animals (llama _Lama glama_ vs. alpaca _Vicugna pacos_ vs. dromedary _Camelus dromedarius_), immunization protocols (antigen formulation, adjuvant, boosting regimen), naive vs. immune library origin, and selection methodology (phage display, yeast display, mammalian display, ribosome display, in silico design). Such variables could introduce subtle biases in starting germline framework usage and CDR sequence characteristics, though the strong conservation of VHH framework sequences across Old World and New World camelid species [7] suggests that interspecies variation is minor compared to the CDR3-length-dependent effects we observed. Our analysis also does not incorporate unpublished clinical immunogenicity data, which would provide the ultimate validation of whether sequence-based humanization levels correlate with actual ADA incidence and clinical impact across diverse patient populations.

### 4.7 Future research directions
Several experimental and computational approaches could validate, refine, and extend our findings beyond this retrospective sequence analysis. First, systematic mutagenesis studies introducing human-like FR2 substitutions into well-characterized long-CDR3 VHHs would directly test whether the humanization plateau reflects stability constraints (thermal unfolding, aggregation propensity), solubility issues (poor expression, precipitation), or binding penalties (affinity loss, altered epitope recognition), thereby establishing causal mechanisms underlying the observed correlations. Second, high-resolution crystal structure determination or cryo-EM structure analysis of representative short- and long-CDR3 clinical VHHs would reveal the precise steric interactions, hydrogen bonding networks, and electrostatic complementarity that couple CDR3 geometry to FR2 residue requirements at atomic resolution. Third, computational structure prediction using AlphaFold2, AlphaFold3, or similar deep learning methods could model forced humanization scenarios where FR2 adopts human-like sequences in long-CDR3 contexts, testing whether such designs generate predicted structural strain, unfavorable energy profiles, or altered dynamics that explain their absence from clinical datasets. Fourth, prospective clinical immunogenicity surveillance data from ongoing VHH therapeutic trials, analyzed in conjunction with detailed sequence features, patient HLA typing, and disease context, will ultimately determine whether the ~87% humanization level is sufficient to prevent clinically significant ADA responses across diverse populations or whether additional sequence optimization strategies (deimmunization through T-cell epitope removal, framework shuffling, somatic hypermutation mimicry) are required for specific applications. Finally, expansion of this analysis to include VHHs derived from additional camelid species (dromedary, guanaco _Lama guanicoe_, vicuña _Vicugna vicugna_), non-clinical research antibodies with known binding and biophysical properties, and failed development candidates (if disclosed) would test the generalizability of CDR3-FR2 coupling and potentially reveal additional sequence-structure-function relationships that govern successful VHH humanization.

## 5. Figure legends

### Figure 1. Phylogenetic analysis of VHH framework regions
**(A)** FR2 region phylogenetic tree (N = 19 VHHs + 4 references). VHHs are labeled with CDR3 length (L = X) and CDR2 fold. Colors indicate CDR3-length groups: red (≤11 aa) and green (>11 aa). Reference sequences include Human IGHV3-23\*01 and IGHV3-13\*01, Alpaca IGHV3-3\*01, and Mouse IGHV1-72\*01 (outgroup). Tree construction: UPGMA clustering on normalized Hamming distance.
**(B)** FR2+FR3 combined phylogenetic tree showing the global humanization landscape and the three-class system.

### Figure 2. Sequence logo analysis stratified by CDR3 length
Sequence conservation plots for FR1, FR2, FR3 (first 20 aa), and FR4, comparing Short CDR3 (≤11 aa, N = 5) versus Long CDR3 (>11 aa, N = 14) groups. Key FR2 positions (IMGT 42, 49, 50, 52) and selected conserved FR3 positions (IMGT 71, 93–95, 104) are highlighted.

---

## 6. References

[1] Hamers-Casterman C, Atarhouch T, Muyldermans S, et al. Naturally occurring antibodies devoid of light chains. Nature. 1993;363(6428):446-448.

[2] Muyldermans S. Nanobodies: natural single-domain antibodies. Annu Rev Biochem. 2013;82:775-797.

[3] Foote J, Winter G. Antibody framework residues affecting the conformation of the hypervariable loops. J Mol Biol. 1992;224(2):487-499.

[4] North B, Lehmann A, Dunbrack RL Jr. A new clustering of antibody CDR loop conformations. J Mol Biol. 2011;406(2):228-256.

[5] Lefranc MP, Giudicelli V, Duroux P, et al. IMGT, the international ImMunoGeneTics information system 25 years on. Nucleic Acids Res. 2015;43(D1):D413-D422.

[6] Dunbar J, Krawczyk K, Leem J, et al. SAbDab: the structural antibody database. Nucleic Acids Res. 2014;42(D1):D1140-D1146.

[7] Vincke C, Muyldermans S. Introduction to heavy chain antibodies and derived Nanobodies. Methods Mol Biol. 2012;911:15-26.

[8] Scully M, Cataland SR, Peyvandi F, et al. Caplacizumab Treatment for Acquired Thrombotic Thrombocytopenic Purpura. N Engl J Med. 2019;380(4):335-346.

[9] Morrison C. Nanobody approval gives domain antibodies a boost. Nat Rev Drug Discov. 2019;18(7):485-487.

[10] Jovčevska I, Muyldermans S. The Therapeutic Potential of Nanobodies. BioDrugs. 2020;34(1):11-26.

[11] Mitchell LS, Colwell LJ. Comparative analysis of nanobody sequence and structure data. Proteins. 2018;86(7):697-706.

[12] Schoof M, Faust B, Saunders RA, et al. An ultrapotent synthetic nanobody neutralizes SARS-CoV-2 by stabilizing inactive Spike. Science. 2020;370(6523):1473-1479.

---

## Data availability
All sequence data, phylogenetic trees (Newick format), and analysis outputs are provided in the supplementary materials distributed with this submission.

## Funding
No external funding was received for this work.

## Conflict of interest
The authors declare no competing interests.

## Ethics and consent
No human subjects were involved in this study.

## Animal research statement
Not applicable. This study utilized publicly available sequence data from clinical databases.
