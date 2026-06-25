# Vernier Zone 

 458  Engineered ， Tier1-Tier3 Vernier Zone 
、PCA 、、。

- : **458**
- : **22** (VH 14 + VL 8)

---

## 1. Vernier 

![Correlation Matrix](vernier_packing_correlation.png)

###  (Top 10)

|  A |  B | Pearson r |  |
|:---|:---|---:|:---|
| VH_71 (T1) | VH_73 (T3) | 0.752 |  →  |
| VH_29 (T2) | VH_73 (T3) | 0.656 |  →  |
| VH_67 (T3) | VH_71 (T1) | 0.620 |  →  |
| VH_71 (T1) | VH_78 (T3) | 0.609 |  →  |
| VL_36 (T2) | VL_71 (T1) | 0.583 |  →  |
| VL_71 (T1) | VL_98 (T3) | 0.547 |  →  |
| VH_67 (T3) | VH_73 (T3) | 0.536 |  →  |
| VH_67 (T3) | VH_78 (T3) | 0.526 |  →  |
| VL_36 (T2) | VL_98 (T3) | 0.515 |  →  |
| VH_73 (T3) | VH_78 (T3) | 0.498 |  →  |

###  (Top 5)

|  A |  B | Pearson r |  |
|:---|:---|---:|:---|
| VH_48 (T3) | VH_67 (T3) | -0.454 | ： |
| VH_49 (T3) | VH_73 (T3) | -0.425 | ： |
| VH_29 (T2) | VH_49 (T3) | -0.388 | ： |
| VH_49 (T3) | VH_67 (T3) | -0.364 | ： |
| VH_48 (T3) | VH_78 (T3) | -0.362 | ： |

---

## 2. ：Vernier 

![Dendrogram](vernier_clustering_dendrogram.png)

###  (3 )

- **Cluster 1**: VH_29, VH_48, VH_49, VH_67, VH_71, VH_73, VH_78
  - Tier : {'T3': np.int64(5), 'T2': np.int64(1), 'T1': np.int64(1)}
- **Cluster 2**: VL_2, VL_36, VL_46, VL_49, VL_69, VL_71, VL_98
  - Tier : {'T3': np.int64(3), 'T2': np.int64(2), 'T1': np.int64(2)}
- **Cluster 3**: VH_2, VH_27, VH_28, VH_30, VH_69, VH_93, VH_94, VL_4
  - Tier : {'T2': np.int64(4), 'T3': np.int64(3), 'T1': np.int64(1)}

---

## 3. PCA ：Vernier Zone 

![PCA Loadings](vernier_pca_loadings.png)

- **PC1** (17.4%): ，
- **PC2** (12.7%): ， VH vs VL 
- **PC1+PC2** : 30.1%

### PC1 
  - VH_73 (T3): loading = 0.428
  - VH_71 (T1): loading = 0.421
  - VH_67 (T3): loading = 0.390
  - VH_78 (T3): loading = 0.382
  - VH_29 (T2): loading = 0.339

### PC2 
  - VL_71 (T1): loading = 0.498
  - VL_36 (T2): loading = 0.446
  - VL_98 (T3): loading = 0.421
  - VL_69 (T3): loading = 0.315
  - VL_2 (T3): loading = 0.304

---

## 4.  Vernier 

![Framework Boxplots](vernier_packing_by_framework.png)

 CDR ， Vernier ，
 Vernier 。

---

## 5. VH/VL  Vernier 

![Angle Scatter](vernier_angle_scatter.png)

---

## 6.  (Cross-Position RF R²)

![Cross R²](vernier_cross_position_r2.png)

###  (Top 10)

|  |  | RF R² |  |
|:---|:---|---:|:---|
| VH_71 | VH_73 | 0.694 |  VH_71  VH_73 |
| VH_78 | VH_71 | 0.622 |  VH_78  VH_71 |
| VH_73 | VH_71 | 0.621 |  VH_73  VH_71 |
| VH_29 | VH_73 | 0.593 |  VH_29  VH_73 |
| VL_36 | VL_71 | 0.567 |  VL_36  VL_71 |
| VH_78 | VH_73 | 0.547 |  VH_78  VH_73 |
| VH_71 | VH_29 | 0.541 |  VH_71  VH_29 |
| VH_67 | VH_73 | 0.537 |  VH_67  VH_73 |
| VH_67 | VH_71 | 0.513 |  VH_67  VH_71 |
| VL_71 | VL_36 | 0.512 |  VL_71  VL_36 |

---

## 7. 

1. **Vernier Zone **：。，。
2. ****：Vernier  2-3 ，。
3. **VH/VL **： Vernier 。
4. **L1 **： VL  Vernier （ VL 71）。
5. ****：VH  VL  Vernier ， VH/VL 。

* `ml_vernier_correlation_analysis.py` 。*