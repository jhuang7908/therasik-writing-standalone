# 15 「no_linker_found」 Linker 

## 

|  |  |
|------|------|
| **Linker ？** | ****：15  **(G4S)₃**（`GGGGSGGGGSGGGGS`） |
| ** no_linker_found？** | Linker  **"na"**（2 ）， VL （≥85 aa）， |
| **** |  **VH-only / Single Domains (VH-VH')**， VL ； "na"  |

---

## 1. 

15 ：

```
…VH…WGQGTLVTVSS  GGGGSGGGGSGGGGS  na
                  ↑ (G4S)3  linker  ↑  2 aa
```

：**VH + (G4S)₃ + "na"**。Pipeline  `split_single_chain`  (G4S)₃， `len(linker) >= MIN_VL_LEN (85)`， `after = "na"`  `(None, None, None, None)`， `no_linker_found`。

---

## 2. 15  Format（Thera-SAbDab）

|  | Format |
|--------|----------------|
| Brivekimig1 | Trispecific Single Domains (VH-VH-VH'-VH''-VH'); Bispecific entry |
| Brivekimig2 | Trispecific Single Domains (VH-VH-VH'-VH''-VH'); Monospecific entry |
| Enristomig | Bispecific Single Domains (VH-VH'-G1(h-CH2-CH3) Dimer) |
| Erfonrilimab | Bispecific Single Domains (VH-VH'-CH) |
| Gefurulimab | Bispecific Single Domains (VH-VH') |
| Gocatamig2 | Trispecific Mixed scFv and Single Domains (scFvhl-VH-VH'); Monospecific |
| Gontivimab | Bispecific Single Domains (VH-VH'-VH') |
| Isecarosmab | Bispecific Single Domains (VH-VH') |
| Lofacimig | Bispecific Tandem VH Domains fused to G1 Constant Domain |
| Ozoralizumab | Bispecific Single Domains (VH-VH'-VH) |
| Podentamig1 | Trispecific Mixed scFv and Single Domains (VH-VH'-scFvhl); Bispecific |
| Sonelokimab1 | Trispecific Single Domains (VH-VH'-VH''); Bispecific Entry |
| Sonelokimab2 | Trispecific Single Domains (VH-VH'-VH''); Monospecific Entry |
| Tarperprumig | Bispecific Single Domains (VH-VH') |
| Vobarilizumab | Bispecific Single Domains (VH-VH') |

：** Single Domains / Tandem VH**， VH-linker-VL  VL。 Heavy  G4S3+“na”，Light 。

---

## 3. “na” 

-  Thera-SAbDab ，**HeavySequence(ifbispec)**  **LightSequence(ifbispec)** “/”。
-  **"na"** ：**N/A**  **nanobody/single domain** ， VL 。

---

## 4.  Pipeline 

- ****：「linker  ≥ 90 aa  linker  ≥ 85 aa」， no_linker_found， 2 aa  VL。
- ****：「 (G4S)₃  VL」， `linker_found_short_tail`， linker  before/after ，「 linker」「linker 、」。

---

## 5. 

- **Linker**：15  **(G4S)₃**（`GGGGSGGGGSGGGGS`）， 84  split_ok 。
- ****：linker  "na"（2 aa）， VL 。
- ****：VH-only / VH-VH' / Tandem VH  VH ， VH-linker-VL scFv。
