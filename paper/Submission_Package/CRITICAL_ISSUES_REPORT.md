# 

****: 2026-01-27  
****: 🚨 **Critical - **

---

## 🚨 

### **1: FR2CDR3**

#### **** (Line 104):
> "Spearman correlation between CDR3 length and phylogenetic distance from Human IGHV3-23 was strongly negative (ρ = -0.604, P = 0.0062), indicating that longer CDR3s are associated with retention of alpaca-like FR2 sequences."

#### ****:

|  | Spearman ρ | P |  |
|------|-----------|-----|--------|
| **FR2** | 0.092 | 0.7076 | ❌  |
| **FR2 Delta (Human-Vicugna)** | 0.251 | 0.3009 | ❌  |
| **Global** | -0.265 | 0.2723 | ❌  |

****: ❌ **，FR2CDR3（P>0.20）**

---

### **2: FR1/FR3**

#### **** (Line 106-107):
> "phylogenetic analysis of FR3... showed no significant clustering by CDR3 length (P = 0.14)"  
> "Similarly, FR1 exhibited near-perfect conservation (>96% human identity across 18/19 molecules)."

#### ****:

| Framework | Spearman ρ | P | Mann-Whitney U | P |  |
|-----------|-----------|-----|----------------|-----|----------|
| **FR1** | -0.079 | 0.7493 | U=43.5 | 0.3871 | ✅  |
| **FR2** | 0.092 | 0.7076 | U=39.0 | 0.6485 | ❌ ρ=-0.604, P=0.0062 |
| **FR3** | 0.080 | 0.7446 | U=32.5 | 0.8109 | ✅ P=0.14 |
| **FR4** | 0.326 | 0.1737 | U=28.0 | 0.1202 | ❌ **** |

****: 
- ✅ FR1/FR3CDR3
- ❌ 
- ❌ FR2

---

### **3: FR4**

#### ****:
- Abstract: "Framework regions (FR1–FR4) were analyzed separately"
- Results/Discussion **FR4**

#### **FR4**:

```
FR4 :
  : 8.61% ± 2.09% (N=19)
  CDR3 (≤11aa): 7.27% ± 4.07%
  CDR3 (>11aa): 9.09% ± 0.00%
  
  :
    Mann-Whitney U: P=0.1202 
    Spearman: ρ=0.326, P=0.1737 
```

**FR4**:
- 6
- : WGQGTLVTVSS (57.9%)
- FR4（>90%9.1%）

****: ❌ **FR4，CDR3**

---

## 🔍 

### **1: **

：
- **Phylogenetic tree**
- ****

：
1. （"phylogenetic distance"？）
2. （Results）

### **2: **

P=0.00175ρ=-0.604，：
1. FR2%、FR2 delta、Global identity，P>0.20
2. （ρ=-0.604，FR2%ρ=+0.092）

### **3: **

"Kruskal-Wallis test on the two natural clusters"，：
1. phylogenetic clustering
2. clusterCDR3

**circular reasoning**：
- FR2clustering → 2cluster
- 2clusterCDR3
- ：FR2CDR3

****: clusteringFR2，！

---

## 📋 

### **1: FR2-CDR3**

：
1. ？（%? phylogenetic distance? delta?）
2. phylogenetic distance，
3. P，

### **2: FR4**

：
```markdown
### 3.X FR4 shows high conservation independent of CDR3 length

FR4 (11 amino acids, IMGT positions 118-128) exhibited uniformly high 
conservation across all clinical VHHs (mean human identity = 8.61% ± 2.09%), 
with no significant difference between short-CDR3 (7.27% ± 4.07%) and 
long-CDR3 (9.09% ± 0.00%) groups (Mann-Whitney U test, P = 0.12). 

The most common FR4 sequence was WGQGTLVTVSS (11/19, 57.9%), which is 
nearly identical to the canonical J-region sequence. FR4 variability was 
minimal (only 6 unique sequences observed), and showed no correlation 
with CDR3 length (Spearman ρ = 0.326, P = 0.17). These findings indicate 
that FR4, as part of the conserved J-region, is not subject to the same 
CDR3-length-dependent constraints observed in FR2, likely due to its 
structural position distant from the CDR loops.
```

### **3: FR1/FR3**

3.3：
```markdown
Quantitative analysis showed:
- FR1: Spearman ρ = -0.079, P = 0.75; Mann-Whitney U test P = 0.39
- FR3: Spearman ρ = 0.080, P = 0.74; Mann-Whitney U test P = 0.81
```

### **4: Discussion**

4.3"Differential roles of framework regions"：
```markdown
FR4, as part of the conserved J-region sequence, showed uniformly high 
conservation (mean 8.6% human identity) with no CDR3-length-dependent 
variation (P = 0.17), consistent with its structural position distant 
from the CDR loops and its role in constant domain interface formation.
```

---

## ⚠️ 

|  |  |  |
|------|---------|------|
| **FR2** | 🔴 **Critical** |  |
| **FR4** | 🟡 **Major** | Abstract， |
| **FR1/FR3** | 🟡 **Major** |  |

---

## 💡 

### **A: **

1. ****:
   - ？
   - phylogenetic distance？
   
2. ****:
   - P>0.05，
   - "trend""significant"
   
3. **FR4**

### **B: **

FR2，**（global identity）**：
- CDR3: 91.00% ± 4.09%
- CDR3: 88.48% ± 3.40%
- P = 0.21 (，)

：
> "Clinical VHHs with shorter CDR3 loops (≤11aa) tended to achieve higher 
> overall humanization (91.0% vs 88.5%), though this difference did not 
> reach statistical significance in our dataset of 19 molecules (P = 0.21)."

### **C: categorical**

，categorical：
- Class 1 (CDR3): 93.2% human identity
- Class 2/3 (CDR3): 87-88% human identity
- class？

---

## 🎯 

****：

1. ✅ **"FR4"** - ，FR4
2. ✅ **"FR1/FR3CDR3？"** - ，

，**FR2**。

---

## 📊 

### **Framework RegionsCDR3**:

```
  FR1: ρ=-0.079, P=0.7493 (ns)
  FR2: ρ= 0.092, P=0.7076 (ns)  ← ρ=-0.604, P=0.0062 ❌
  FR3: ρ= 0.080, P=0.7446 (ns)
  FR4: ρ= 0.326, P=0.1737 (ns)
```

****: **Framework RegionCDR3！**

---

## ⚡ 

### ****:

1. [ ] **FR2-CDR3**
   - 
   - P，ResultsDiscussion
   
2. [ ] **FR4**
   - Results 3.XFR4section
   - Discussion 4.3FR4
   
3. [ ] **FR1/FR3**
   - Results 3.3P
   
4. [ ] ****
   - FR2，"CDR3FR2"
   - "CDR3"

---

## 📄 ：

### **CDR3**:

| Framework | CDR3 (N=5) | CDR3 (N=14) | Mann-Whitney P | Spearman ρ | Spearman P |
|-----------|-------------|--------------|---------------|-----------|-----------|
| **FR1** | 98.40 ± 2.19% | 97.43 ± 1.99% | 0.3871 | -0.079 | 0.7493 |
| **FR2** | 17.65 ± 4.16% | 16.81 ± 2.14% | 0.6485 | 0.092 | 0.7076 |
| **FR3** | 14.59 ± 0.67% | 15.03 ± 1.90% | 0.8109 | 0.080 | 0.7446 |
| **FR4** | 7.27 ± 4.07% | 9.09 ± 0.00% | 0.1202 | 0.326 | 0.1737 |
| **Global** | 91.00 ± 4.09% | 88.48 ± 3.40% | 0.2071 | -0.265 | 0.2723 |

****: P < 0.05

---

****: 2026-01-27  
****: 🚨 ****
