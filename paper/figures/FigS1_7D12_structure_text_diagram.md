# S1: 7D12

## 7D12 (PDB 4KRL)  - SR

****：
- **[S]** = SR (relSASA ≥0.25)
- **[B]** = SR (relSASA <0.25)
- **[C]** = CDR
- **[.]** = 

---

## IMGTSR

### FR1 (1-26)
```
:  1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20  21  22  23  24  25  26
:  Q   V   K   L   E   E   S   G   G   G   S   S   V   Q   T   G   G   S   L   R   L   T   C   A   A   S
: [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [S] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.]
:                                                      ↑ IMGT12 (S→L, )
```

### CDR1 (27-38)
```
: 27  28  29  30  31  32  33  34  35  36  37  38
:  G   R   T   S   R   S   Y   G   M   G   W   -
: [C] [C] [C] [C] [C] [C] [C] [C] [C] [C] [C] [C]
: CDR1 - 
```

### FR2 (39-55)
```
: 39  40  41  42  43  44  45  46  47  48  49  50  51  52  53  54  55
:  F   G   R   F   Q   A   P   G   K   E   R   E   F   V   S   G   I
: [.] [B] [.] [B] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.]
:      ↑ IMGT40 (G→S, )  ↑ IMGT42 (F→V, )
```

### CDR2 (56-65)
```
: 56  57  58  59  60  61  62  63  64  65
:  S   W   R   G   D   S   T   G   Y   A
: [C] [C] [C] [C] [C] [C] [C] [C] [C] [C]
: CDR2 - 
```

### FR3 (66-104)
```
: 66  67  68  69  70  71  72  73  74  75  76  77  78  79  80  81  82  83  84  85  86  87  88  89  90  91  92  93  94  95  96  97  98  99 100 101 102 103 104
:  D   S   V   K   G   R   F   T   I   S   R   D   N   A   K   N   T   V   D   L   Q   M   N   S   L   K   P   E   D   T   A   I   Y   Y   C   A   A   A   A
: [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.] [.]
:                                                                                                                                    ↑ IMGT83 (A→S, )
                                                                                                                                                              ↑ IMGT96 (P→A, )
                                                                                                                                                                                      ↑ IMGT101 (I→V, )
```

### CDR3 (105-117)
```
: 105 106 107 108 109 110 111 112 113 114 115 116 117
:  T   L   Y   E   Y   D   Y   W   G   Q   G   T   -
: [C] [C] [C] [C] [C] [C] [C] [C] [C] [C] [C] [C] [C]
: CDR3 - 
```

### FR4 (118-128)
```
: 118 119 120 121 122 123 124 125 126 127 128
:  Q   V   T   V   S   S   A   L   E   -   -
: [.] [.] [.] [.] [.] [.] [.] [.] [.]
: FR4 - 
```

---

## SR

| IMGT | Native | SR |  | relSASA |  |  |
|---------|--------|----|----|---------|---------|---------|
| 12 | S | L | FR1 | 0.71 |  | SR+BM |
| 40 | G | S | FR2 | 0.01 |  | SR+BM |
| 42 | F | V | FR2 | 0.01 |  | SR+BM |
| 83 | A | S | FR3 | 0.78 |  | SR+BM |
| 96 | P | A | FR3 | 0.45 |  | SR+BM |
| 101 | I | V | FR3 | 0.27 |  | SR+BM |

****：
- 6SR4（67%），SR
- 2（IMGT 40、42）
- CDR，

---

## 3D

3D，：

### PyMOL
```
load output/7D12/4KRL.pdb, 7d12
select surface_muts, resi 12+83+96+101 and chain B
select buried_muts, resi 40+42 and chain B
select cdrs, resi 27-38+56-65+105-117 and chain B
color blue, surface_muts
color red, buried_muts
color green, cdrs
show surface
ray
save output/7D12/7d12_4krl_structure_with_sr_mutations.png
```

### ChimeraX
```
open output/7D12/4KRL.pdb
color #0000ff :12,83,96,101  # ：
color #ff0000 :40,42          # ：
color #00ff00 :27-38,56-65,105-117  # ：CDR
surface
save output/7D12/7d12_4krl_structure_with_sr_mutations.png
```

---

****：SR。3D。
