# FR3 NCDR2

****: 2026-01-27  
****: 🔴 **High - **

---

## 🎯 ****

FR3 N**CDR2 canonical class**，CDR3：

- **CDR2**: 75%，P=0.0133 ⭐ ****
- **CDR3**: 37%，P=0.0657

---

## 📊 ****

### **CDR2 Canonical Class**

| CDR2 Class |  |  |
|-----------|------|------|
| **H2-10-1** | 12 | CDR2 (~10 aa) |
| **H2-9-1** | 6 | CDR2 (~9 aa) |
| unknown | 1 |  |

### **FR31（CDR2）**

#### **CDR2 (H2-10-1, N=12)**:
- **Tyr (Y): 9/12 (75.0%)** ← 
- Ser (S): 1/12 (8.3%)
- Leu (L): 1/12 (8.3%)
- Lys (K): 1/12 (8.3%)

#### **CDR2 (H2-9-1, N=6)**:
- **Thr (T): 3/6 (50.0%)** ← 
- Asn (N): 1/6 (16.7%)
- Val (V): 1/6 (16.7%)
- Ser (S): 1/6 (16.7%)
- **Tyr (Y): 0/6 (0%)** ← 

****: TyrCDR275%，CDR20% → **75%**

---

### **：CDR2 × CDR3**

| CDR2 | CDR3 | N | FR31 |  |
|------|------|---|--------------------|-----------|
| **long** | **long** | **9** | **Y: 88.9%** | ，Tyr |
| short | long | 4 | T: 75.0% | CDR2（YT）|
| long | short | 3 | Y/L/K: 33% | CDR2 |
| short | short | 2 | N/V: 50% | ，Tyr |

****:
- **CDR2 + CDR3**: Tyr88.9%
- **CDR2 + CDR3**: Thr75%（**Tyr**！）
  - **CDR2**，CDR3，CDR2，Tyr

---

## 🔬 ****

### **CDR2 Canonical Class**

#### **H2-10-1 (CDR2)**:
- 10
- loop
- FR3 N
- **Tyr**：
  - π-π stacking
  - 
  - 

#### **H2-9-1 (CDR2)**:
- 9
- loop
- FR3 N、
- **Thr/Asn/Val**：
  - 
  - （steric clash）
  - 

### **CDR2CDR3？**

1. ****:
   - FR3 N****CDR2 C
   - CDR3
   - ** > **

2. ****:
   - CDR2FR3 N
   - CDR3loop packing
   - ** > **

3. ****:
   - CDR2-FR3
   - VHH fold
   - ** > **

---

## 📝 ****

### **Results 3.X - Position-specific analysis**

FR4，FR3：

```markdown
**FR3 N-terminus** (first position following CDR2) exhibited strong positional 
constraints associated with CDR2 canonical class rather than CDR3 length 
(χ² = 25.33, P = 0.0133). VHHs with long CDR2 loops (H2-10-1, N=12) showed a 
strong preference for Tyr at the first FR3 position (9/12, 75%), whereas VHHs 
with short CDR2 loops (H2-9-1, N=6) uniformly avoided Tyr at this position 
(0/6, 0%) and instead favored Thr (3/6, 50%) or other small polar residues 
(Asn, Val, Ser). This 75% frequency difference indicates that the CDR2-FR3 
junction residue is under strong structural constraint from the immediately 
adjacent CDR2 loop geometry.

Cross-analysis of CDR2 type and CDR3 length revealed that CDR2 canonical class 
is the dominant determinant: among VHHs with long CDR3 (>11aa, N=14), those 
with long CDR2 (H2-10-1) retained high Tyr frequency at FR3 position 1 (8/9, 
88.9%), whereas those with short CDR2 (H2-9-1) predominantly carried Thr at 
this position (3/4, 75%) rather than Tyr. This pattern demonstrates that 
framework-CDR junction constraints are imposed primarily by the immediately 
adjacent CDR loop, with more distant CDRs exerting secondary modulatory effects.

In contrast to FR3 N-terminus, the association between CDR3 length and FR3 
position 1 was weaker and did not reach statistical significance (χ² = 11.84, 
P = 0.0657), supporting the primacy of CDR2 geometry in determining this 
junction residue.
```

---

### **Discussion 4.3 - CDR2**

IMGT 118，：

```markdown
**CDR2 canonical class as the primary determinant of FR3 N-terminus**

While CDR3 length dictates the sequence requirements at the CDR3-FR4 junction 
(IMGT 118), the CDR2-FR3 junction is predominantly governed by CDR2 canonical 
class. The first residue of FR3 showed a 75% frequency difference between long 
CDR2 (H2-10-1: 75% Tyr) and short CDR2 (H2-9-1: 0% Tyr), compared to only 37% 
difference between long and short CDR3 groups. Statistical testing confirmed 
CDR2 canonical class as the significant predictor (P = 0.0133) over CDR3 length 
(P = 0.0657).

This pattern reflects the principle that **framework-CDR junction constraints 
are imposed primarily by the immediately adjacent CDR loop**. The CDR2-FR3 
junction must accommodate the geometric demands of CDR2 loop conformations: 
long CDR2 loops (H2-10-1) require a bulky aromatic residue (Tyr) at the FR3 
N-terminus to provide structural support and favorable stacking interactions, 
whereas short CDR2 loops (H2-9-1) favor smaller polar residues (Thr, Asn, Val) 
that minimize steric clashes and provide backbone flexibility. Cross-analysis 
revealed that VHHs with short CDR2 avoided Tyr at FR3 position 1 even when 
CDR3 was long (Thr: 75% in short-CDR2/long-CDR3 subset), confirming the 
dominance of local over distal CDR effects.

This modular constraint architecture has practical implications for VHH 
humanization: each framework-CDR junction must be optimized according to the 
geometry of its immediately adjacent CDR loop, rather than applying uniform 
humanization rules across all junctions. Specifically, the FR3 N-terminus should 
be engineered based on CDR2 canonical class (Tyr for H2-10-1, Thr/Asn/Val for 
H2-9-1), whereas the FR4 N-terminus (IMGT 118) should be optimized based on 
CDR3 length (Trp for long CDR3).
```

---

## 📊 **Table/Figure**

### **Table S2 - CDR2**

| Position | Junction | CDR2 short | CDR2 long | Freq Diff | CDR3 ≤11aa | CDR3 >11aa | Freq Diff | Primary Driver |
|----------|----------|-----------|-----------|-----------|-----------|-----------|-----------|---------------|
| **FR3-1** | **CDR2-FR3** | **T:50%, N/V/S:17%** | **Y:75%, S/L/K:8%** | **75%** | Y/K/L/N/V:20% | Y:57%, T:21% | 37% | **CDR2 (P=0.013)** |
| **IMGT 118** | **CDR3-FR4** | ** | ** | ** | W:40%, R:40%, S:20% | W:100% | 60% | **CDR3** |

---

## 🔍 **：IMGT 118CDR2**

：
- IMGT 118CDR3（60%）
- FR3-1CDR2（75%）

****：
- IMGT 118CDR2？
- ，""

...

---

## 🎯 ****

### **Framework-CDR Junction""**:

```
CDR1 → [FR2] → CDR2 → [FR3-N] → ... → [FR3-C] → CDR3 → [FR4-N]
                         ↑                         ↑
                    CDR2              CDR3
                    (75%)               (60%)
```

****:
1. **junctionCDR**
2. CDR/
3. ****，

---

## ✅ ****

### ****:

- [ ] **Results 3.X** - FR3-CDR2（75%，P=0.013）
- [ ] **Discussion 4.3** - ""CDR2
- [ ] **Table S2** - CDR2
- [ ] **** - IMGT 118CDR2

### ****:

- [ ] **Figure** - CDR2-FR3-CDR3-FR4
- [ ] **Panel** - Logo plotsCDR2
- [ ] **Abstract** - CDR2CDR3junction

---

## 📌 **（Abstract）**

> "Position-specific analysis revealed localized structural constraints at 
> framework-CDR junctions governed by the immediately adjacent CDR loop: 
> FR3 N-terminus is determined by CDR2 canonical class (75% frequency 
> difference, P=0.013), whereas FR4 N-terminus (IMGT 118) is constrained 
> by CDR3 length (60% frequency difference). This 'neighbor dominance' 
> principle indicates that humanization strategies must respect junction-
> specific requirements rather than applying uniform framework modifications."

---

****: 2026-01-27  
****: ，
