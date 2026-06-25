# 📋 Complete Paper Organization Guide

**Project**: VHH Humanization Analysis for *Antibodies* Journal  
**Date**: January 27, 2026  
**Status**: Ready for final figure generation and submission

---

## 🗂️ Directory Structure Overview

```
paper/
├── Submission_Package/              #  (Main submission files)
│   ├── Manuscript_VHH_Humanization.md  # 
│   ├── Cover_Letter.md                  # 
│   ├── README_SUBMISSION.md             # 
│   ├── Figures/                         #  ( PNG)
│   └── Tables/                          # 
│       ├── Table1_Clinical_Landscape.csv
│       └── TableS1_Residue_Frequencies.csv
│
├── Supplementary_Materials/         #  (Supplementary data)
│   ├── README_SUPPLEMENTARY.md          # 
│   ├── Source_Data/                     # 19VHH
│   │   └── Publication_Source_Data.csv
│   ├── Sequences/                       # 
│   │   ├── Reference_Germlines.fasta    # 
│   │   ├── TheraSAbDab_19VHH_ANARCII_numbering_full.csv
│   │   ├── TheraSAbDab_19VHH_FR_sequences.csv
│   │   └── *.fasta                      # LogoFASTA
│   └── Analysis_Reports/                # 
│       ├── TheraSAbDab_19VHH_phylogeny_discrimination_analysis.txt
│       ├── TheraSAbDab_19VHH_clustering_comparison.txt
│       ├── TheraSAbDab_19VHH_New_Classification.txt
│       ├── *.newick                     # 
│       └── *_Vernier_Analysis.txt       # 
│
├── raw data/                        #  
│   ├── Logos/                           # Logo
│   ├── Phylogeny/                       # 
│   ├── MicroAnalysis/                   # 
│   └── ...
│
├── manuscript/                      #  
│   └── Draft_Manuscript.md
│
├── tables/                          # 
│   ├── Table1_Clinical_Landscape_Filled.csv
│   └── TableS1_Residue_Frequencies.csv
│
├── figures/                         # 
│
├── PAPER_ORGANIZATION_GUIDE.md      # 
├── SUBMISSION_CHECKLIST.md          # 
└── FINAL_COMPLETION_REPORT.md       # 
```

---

## 📦 Two-Package System Explanation

### ？

：
> "covet letter, figure, table，"

#### **Package 1: Submission_Package/** 
****: ""，：
- ✅ Cover Letter
- ✅ Manuscript
- ✅ Main Figures（：、Logo）
- ✅ Main Tables（：Table 1  Table S1）

****:
- 、
- MDPI
- （Figure1A, Table1）

---

#### **Package 2: Supplementary_Materials/** 
****: ""，：
- ✅ 19VHH
- ✅ ANARCI
- ✅ （、、）
- ✅ （Newick）
- ✅ （P）
- ✅ LogoFASTA
- ✅ Hallmark & Vernier Zone

****:
- 、
- 
- 、

---

## 🎯 

### 1: 
👉 ****: `Submission_Package/`
- 
- MarkdownDOCX
- 

### 2: 
👉 ****: `Supplementary_Materials/` ZIP
- 、、
- README
- 

### 3: 
👉 ****: `raw data/`  `scripts/`
- 
- 
- ，

---

## ✅ 

###  ✅
1. **** (100%)
   - Draft_Manuscript.md →  Submission_Package/Manuscript_VHH_Humanization.md
   -  (Background/Methods/Results/Conclusions)
   - 6Results，6Discussion，6Methods
   - 12
   - 

2. **** (100%)
   - Table 1: 19VHH（TBD）
   - Table S1: Hallmark & Vernier
   - : CSV → Word/Excel

3. **** (100%)
   - Publication_Source_Data.csv（19VHH）
   - Reference_Germlines.fasta（4）
   - FR_sequences.csv
   - ANARCI

4. **** (100%)
   - （P=0.00175, ρ=-0.604）
   - （CDR3 vs CDR2 fold）
   - （Class 1/2/3）
   - Hallmark & Vernier Zone
   - Newick

5. **** (100%)
   - Cover_Letter.md
   - README_SUBMISSION.md
   - README_SUPPLEMENTARY.md
   - SUBMISSION_CHECKLIST.md

---

###  ⏳

#### 🔴 HIGH PRIORITY

**1. ** (15)
```powershell
cd "d:\InSynBio-AI-Research\Antibody_Engineer_Suite"
python scripts\visualize_phylogeny_detailed_11_inclusive.py
```
****:
- TheraSAbDab_19VHH_FR2_detailed_11inclusive.png
- TheraSAbDab_19VHH_FR2_FR3_detailed_11inclusive.png

****: `Submission_Package\Figures\`  
****: `Figure1A_FR2_Phylogeny.png`, `Figure1B_FR2FR3_Phylogeny.png`

---

**2. Sequence Logo** (30)

**Option A: （8panel）**
- FR3/FR4FASTA
- WebLogo8PNG
- Figure 2

**Option B: **
- FR2Logo
- 2panel: Short CDR3 vs Long CDR3
- FASTA，PNG

**WebLogo** (http://weblogo.threeplusone.com/):
```bash
weblogo -f FR2_Short_CDR3_lt11.fasta -o Figure2A_FR2_Short.png -F png --resolution 300
weblogo -f FR2_long_CDR3_lt11.fasta -o Figure2B_FR2_Long.png -F png --resolution 300
```

---

**3. ** (10)

**Markdown → DOCX**:
```powershell
cd "d:\InSynBio-AI-Research\Antibody_Engineer_Suite\paper\Submission_Package"
pandoc Manuscript_VHH_Humanization.md -o Manuscript_VHH_Humanization.docx
```

WordMD。

---

#### 🟡 MEDIUM PRIORITY

**4. ** (10)
- 、、ORCID
- 
- 

**5. ** (5)
- Author Contributions（: "X.X. designed study; Y.Y. performed analysis..."）
- Acknowledgments（、）
- Conflicts of Interest（"The authors declare no conflict of interest."）

**6. ** (10)
```powershell
cd "d:\InSynBio-AI-Research\Antibody_Engineer_Suite\paper"
Compress-Archive -Path "Supplementary_Materials\*" -DestinationPath "Supplementary_Data.zip"
```

---

## 📊 

### ✅ 

|  |  |  |
|---|---|---|
| P = 0.00175 (CDR3 vs FR2) | `clustering_comparison.txt` Line 8 | ✅ |
| ρ = -0.604, P = 0.0062 | `phylogeny_discrimination_analysis.txt` Line 22 | ✅ |
| Class 1: 93.2% human identity | `New_Classification.txt` Line 6 | ✅ |
| Arg47: 13/14 (93%) | `Hallmark_Vernier_Analysis_Corrected.txt` | ✅ |
| Arg71: 100% conserved | Extended Vernier Analysis | ✅ |
| FR2 CDR3 correlation: ρ=-0.604 | `phylogeny_discrimination_analysis.txt` | ✅ |

### ✅ 

1. Hamers-Casterman, C., et al. (1993). *Nature*, 363, 446-448. ✅
2. Muyldermans, S. (2013). *Annu Rev Biochem*, 82, 775-797. ✅
3. Foote, J., & Winter, G. (1992). *JMB*, 224, 487-499. ✅
4. North, B., et al. (2011). *JMB*, 406, 228-256. ✅
5. Lefranc, M.P., et al. (2015). *NAR*, 43(D1), D413-D422. ✅
6. Dunbar, J., et al. (2014). *NAR*, 42(D1), D1140-D1146. ✅

**。**

---

## 🚀 

### **Step 1: ** (45)
1.  `visualize_phylogeny_detailed_11_inclusive.py` 
2. WebLogoLogo
3. PNG `Submission_Package/Figures/`
4. ≥300 DPI

### **Step 2: ** (30)
1. Manuscript.mdDOCX
2. 
3. Figure Legends
4. Word

### **Step 3: ** (20)
1. Cover Letter
2. Author Contributions
3. AcknowledgmentsFunding
4. Conflicts of Interest

### **Step 4: ** (15)
1.  `Supplementary_Materials/` 
2.  `Supplementary_Data.zip`
3. Supplementary Information PDF

### **Step 5: ** (30)
1.  https://susy.mdpi.com/user/manuscripts/upload?journal=antibodies
2. （、、、）
3. ：
   - Main Manuscript (DOCX/PDF)
   - Cover Letter (PDF)
   - Figure 1A (PNG)
   - Figure 1B (PNG)
   - Figure 2 (PNG, panel)
   - Table 1 (Excel)
   - Table S1 (Excel)
   - Supplementary Data (ZIP)
4. 

****: 2.5-3

---

## 📞 

### MDPI Support
- **Email**: antibodies@mdpi.com
- ****: https://www.mdpi.com/journal/antibodies/instructions
- **LaTeX**: https://www.mdpi.com/authors/latex 

### 
- **Pandoc** (Markdown): https://pandoc.org/
- **WebLogo** (Logo): http://weblogo.threeplusone.com/
- **FigTree** (Newick): http://tree.bio.ed.ac.uk/software/figtree/
- **Grammarly** : https://www.grammarly.com/

---

## 🎉 

✅ **19VHH** →   
✅ **** → CDR3FR2（P=0.00175）  
✅ **** → 3，BM/SR/Native  
✅ **** → Position 47""  
✅ **** → 5500，，  
✅ **** → 、、  
✅ **** →  + ，  

**、、！** 🎊

---

## 📋 Quick Checklist

- [x] 
- [x] 
- [x] 
- [x] 
- [x] 
- [x] Cover Letter
- [x] README
- [ ] **** ← ****
- [ ] **Sequence Logo** ← ****
- [ ] （Markdown→DOCX）
- [ ] 
- [ ] 
- [ ] 

---

****: 2026127 19:10  
****: AI Assistant  
****: 📊 95%，！
