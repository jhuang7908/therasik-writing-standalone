# 

****: 2026-01-28  
****: ✅ **Logo**

---

## 📊 ****

### **1.  (Phylogenetic Trees)** ✅

|  |  |  |
|------|------|------|
| `TheraSAbDab_19VHH_FR2_anchored.newick` | FR2 | FR2phylogenetic clustering |
| `TheraSAbDab_19VHH_FR3_anchored.newick` | FR3 | FR3 |
| `TheraSAbDab_19VHH_FR2_FR3_anchored.newick` | FR2+FR3 | Framework |

****: `Supplementary_Materials/Analysis_Reports/`

---

### **2. Logo（CDR3）** ✅

****:
- FR1 logo (CDR3)
- FR2 logo (CDR3)
- FR3 logo (CDR3)
- FR4 logo (CDR3)

****: FR1-FR4CDR3

---

## 🆕 ****

### **3. FR3Logo（CDR2）** ✅ ****

|  |  |  |
|------|------|---------|
| `FR3_Logo_short_H2-9-1.png` | CDR2 (H2-9-1, N=6) |  |
| `FR3_Logo_long_H2-10-1.png` | CDR2 (H2-10-1, N=12) |  |
| **`FR3_Logo_CDR2_Comparison.png`** | **** | **，** |

****: `Supplementary_Materials/Figures/`

****:
- 175%
- CDR2: T 50%, Tyr
- CDR2: Y 75%

---

### **4. FR4Logo（CDR3）** ✅ ****

|  |  |  |
|------|------|---------|
| **`FR4_Logo_CDR3_Comparison.png`** | **CDR3** | **，IMGT 118** |

****:
- IMGT 11860%
- CDR3: W 40%, R 40%, S 20%
- CDR3: W 100%

---

## 📋 ****

### **Main Figures **

#### **Figure 1**: Overview and FR2 Phylogenetic Clustering
- **Panel A**: 
- **Panel B**: FR2 phylogenetic tree (colored by CDR3 length)
- **Panel C**: CDR3 vs FR2 clustering

#### **Figure 2**: Position-specific Junction Constraints ⭐ ****
- **Panel A**: **FR3 N-terminus logo (CDR2)** 
  - : `FR3_Logo_CDR2_Comparison.png`
  - 175%
  
- **Panel B**: **FR4 N-terminus logo (CDR3)**
  - : `FR4_Logo_CDR3_Comparison.png`
  - IMGT 11860%

#### **Figure 3**: Clinical VHH Analysis
- **Panel A**: 
- **Panel B**: CDR2 × CDR3 
- **Panel C**: VHH

---

### **Supplementary Figures **

#### **Figure S1**: Framework Region Sequence Logos (CDR3)
- **Panel A**: FR1 logo
- **Panel B**: FR2 logo
- **Panel C**: FR3 logo 
- **Panel D**: FR4 logo 

#### **Figure S2**: FR3 Detailed Analysis (CDR2)
- **Panel A**: FR3logo (CDR2)
  - : `FR3_Logo_short_H2-9-1.png`
- **Panel B**: FR3logo (CDR2)
  - : `FR3_Logo_long_H2-10-1.png`
- **Panel C**: 

#### **Figure S3**: Phylogenetic Trees
- **Panel A**: FR2 tree
- **Panel B**: FR3 tree
- **Panel C**: Combined FR2+FR3 tree

---

## 🎯 ****

### **Figure 2  **:

#### **Panel A - FR3 N vs CDR2**:
```
:
- 175%（P=0.013）
- CDR2: Tyr 75% (，)
- CDR2: Thr 50% (，)
- CDR2FR3 N
```

#### **Panel B - FR4 N vs CDR3**:
```
:
- IMGT 11860%（P=0.007）
- CDR3: Trp 100% 
- CDR3: W/R/S (40%/40%/20%)
- CDR3FR4 N
```

---

## 📐 ****

### **** :
- **** (S,T,N,Q):  #33A02C
- **** (Y,F,W):  #FF7F00 ⭐ 
- **** (K,R,H):  #E31A1C
- **** (D,E):  #6A3D9A
- **** (A,V,L,I,M,P):  #1F78B4

### ****:
1. ✅ 1（FR3）
2. ✅ IMGT 118（FR4）
3. ✅  (N=X)
4. ✅ 

---

## 📊 ****

### **Table S3** : Position-specific analysis

| Junction | Position | Short Group | Long Group | Freq Diff | P-value | Primary Driver |
|----------|----------|-------------|------------|-----------|---------|----------------|
| FR3-CDR2 | FR3-1 | T:50%, N/V/S:17% | Y:75% | 75% | 0.013 | CDR2 canonical class |
| CDR3-FR4 | IMGT 118 | W:40%, R:40%, S:20% | W:100% | 60% | 0.007 | CDR3 length |

---

## ✅ ****

### **Logo**:

```
Supplementary_Materials/Figures/
├── FR3_Logo_short_H2-9-1.png          # CDR2FR3
├── FR3_Logo_long_H2-10-1.png          # CDR2FR3
├── FR3_Logo_CDR2_Comparison.png       # FR3 ⭐ 
└── FR4_Logo_CDR3_Comparison.png       # FR4 ⭐ 
```

### **** :

```
:
├── FR1_Logo_CDR3_groups.png           # FR1CDR3
├── FR2_Logo_CDR3_groups.png           # FR2CDR3
├── FR3_Logo_CDR3_groups.png           # FR3CDR3
└── FR4_Logo_CDR3_groups.png           # FR4CDR3
```

---

## 🔍 ****

- [x] FR3 logoCDR2
- [x] FR4 logoCDR3
- [x] 
- [x] 
- [x] 
- [ ] FR1-FR4CDR3logo
- [ ] logoFigure

---

## 💡 ****

### **Results**:

```markdown
### 3.X Position-specific constraints at framework-CDR junctions

To identify residue-level drivers of framework-CDR coupling, we performed 
position-specific amino acid frequency analysis at framework-CDR junctions 
(Figure 2).

**FR3 N-terminus exhibits strong CDR2-canonical-class dependence** (Figure 2A). 
The first residue of FR3, immediately following CDR2, showed a 75% frequency 
difference between CDR2 types (χ² = 25.33, P = 0.0133): VHHs with long CDR2 
(H2-10-1, N=12) predominantly carried Tyr at this position (9/12, 75%), 
whereas VHHs with short CDR2 (H2-9-1, N=6) uniformly avoided Tyr (0/6, 0%) 
and instead favored Thr (3/6, 50%).

**FR4 N-terminus (IMGT 118) exhibits strong CDR3-length dependence** (Figure 2B). 
This position showed a 60% frequency difference between CDR3-length groups: 
long-CDR3 VHHs (>11aa, N=14) uniformly retained Trp118 (14/14, 100%), whereas 
short-CDR3 VHHs (≤11aa, N=5) displayed variability (Trp: 2/5, 40%; Arg: 2/5, 
40%; Ser: 1/5, 20%).
```

---

## 📝 **Figure Legends**

### **Figure 2**: Position-specific constraints at framework-CDR junctions

**A.** Sequence logo of FR3 N-terminus (positions 1-15) stratified by CDR2 
canonical class. Top panel: short CDR2 (H2-9-1, N=6); bottom panel: long CDR2 
(H2-10-1, N=12). Red dashed line indicates position 1, which exhibits 75% 
frequency difference (P = 0.0133). Amino acids colored by type: polar (green), 
aromatic (orange), positive (red), negative (purple), hydrophobic (blue).

**B.** Sequence logo of FR4 (IMGT positions 118-128) stratified by CDR3 length. 
Top panel: short CDR3 (≤11aa, N=5); bottom panel: long CDR3 (>11aa, N=14). 
Red dashed line indicates IMGT position 118, which exhibits 60% frequency 
difference (P = 0.0068). Note the universal Trp retention in long-CDR3 VHHs.

---

## 🎯 ****

logo，：

1. **""** (Neighbor Dominance Principle):
   - FR3 NCDR2（75%）
   - FR4 NCDR3（60%）

2. ****:
   - （junction），Framework
   - %CDR

3. ****:
   - CDR2 → FR3-NTyr
   - CDR3 → IMGT 118Trp
   - junction

---

****: 2026-01-28  
****: ✅ **logo**
