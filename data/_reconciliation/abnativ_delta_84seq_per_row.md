# AbNatiV Δ Per-Row Scatter — 84-Sequence Validation

**Generated:** 2026-05-08  
**Layer version:** `V1.7.1-2026-05-08`  
**Source:** `core/vh2vhh/abnativ_naturalness_layer.py`  
**Validation script:** `.tmp_validate_v17_layer.py`  

## 5-tier thresholds (V1.7.1)

| Tier | Δ range | Anchor |
|---|---|---|
| EXCELLENT | Δ ≥ +0.085 | Clinical VHH median |
| GOOD      | +0.050 ≤ Δ < +0.085 | LIKELY lower bound |
| PASS      | +0.013 ≤ Δ < +0.050 | Atlas-24 median |
| WARN      | -0.050 ≤ Δ < +0.013 | toward IgG VH |
| FAIL      | Δ < -0.050 | regular IgG VH territory |

## Group summary (re-tiered under V1.7.1)

| Group | n | Δ median | Δ mean | Δ min | Δ max | %EXCELLENT | %GOOD | %PASS | %WARN | %FAIL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Clinical VHH (positive) | 20 | +0.085 | +0.075 | -0.065 | +0.214 | 50% | 10% | 0% | 15% | 25% |
| DB-B humanized camelid VHH (positive) | 16 | +0.038 | -0.020 | -0.527 | +0.386 | 44% | 6% | 6% | 6% | 38% |
| Atlas-24 engineered human VH | 24 | +0.013 | +0.041 | -0.184 | +0.273 | 33% | 4% | 12% | 33% | 17% |
| Murine humanized regular IgG VH | 2 | -0.147 | -0.147 | -0.286 | -0.008 | 0% | 0% | 0% | 50% | 50% |
| Lofacimig tandem VH-Fc (humanized camelid) | 2 | +0.193 | +0.193 | +0.183 | +0.203 | 100% | 0% | 0% | 0% | 0% |
| Fully human IgG VH (negative) | 15 | -0.167 | -0.248 | -0.573 | -0.028 | 0% | 0% | 0% | 13% | 87% |
| Chimeric IgG VH (negative) | 3 | +0.072 | -0.076 | -0.377 | +0.075 | 0% | 67% | 0% | 0% | 33% |
| Naive murine IgG VH (negative) | 2 | -0.210 | -0.210 | -0.229 | -0.192 | 0% | 0% | 0% | 0% | 100% |

## Per-row detail (sorted by Δ within each group, descending)

### Clinical VHH (positive)  (n=20)

| ID | VH2 | VHH2 | Δ | Tier (V1.7.1) |
|---|---:|---:|---:|---|
| ALX-0171 | 0.461 | 0.675 | +0.214 | EXCELLENT |
| Gontivimab | 0.461 | 0.675 | +0.214 | EXCELLENT |
| Ciltacabtagene_autoleucel_cilta-cel | 0.611 | 0.822 | +0.211 | EXCELLENT |
| LCAR-B38M | 0.611 | 0.822 | +0.211 | EXCELLENT |
| Caplacizumab | 0.572 | 0.764 | +0.192 | EXCELLENT |
| Envafolimab | 0.511 | 0.685 | +0.174 | EXCELLENT |
| Erfonrilimab | 0.511 | 0.685 | +0.174 | EXCELLENT |
| Gocatamig2 | 0.592 | 0.731 | +0.139 | EXCELLENT |
| Gefurulimab | 0.629 | 0.753 | +0.124 | EXCELLENT |
| Isecarosmab | 0.629 | 0.739 | +0.110 | EXCELLENT |
| Brivekimig1 | 0.694 | 0.753 | +0.060 | GOOD |
| Enristomig | 0.651 | 0.709 | +0.058 | GOOD |
| Brivekimig2 | 0.805 | 0.811 | +0.006 | WARN |
| Letolizumab | 0.754 | 0.725 | -0.028 | WARN |
| Gocatamig1 | 0.717 | 0.673 | -0.043 | WARN |
| 131I-GMIB-Anti-HER2-VHH1 | 0.915 | 0.850 | -0.065 | FAIL |
| 68-GaNOTA-Anti-HER2_VHH1 | 0.915 | 0.850 | -0.065 | FAIL |
| CD20_VHH_CAR-T | 0.915 | 0.850 | -0.065 | FAIL |
| CD33_VHH_CAR-T | 0.915 | 0.850 | -0.065 | FAIL |
| HER2_VHH_CAR-T | 0.915 | 0.850 | -0.065 | FAIL |

### DB-B humanized camelid VHH (positive)  (n=16)

| ID | VH2 | VHH2 | Δ | Tier (V1.7.1) |
|---|---:|---:|---:|---|
| 3dwt_A | 0.372 | 0.758 | +0.386 | EXCELLENT |
| 3eba_A | 0.554 | 0.823 | +0.270 | EXCELLENT |
| 9jqt_D | 0.618 | 0.849 | +0.231 | EXCELLENT |
| 7q6c_K | 0.618 | 0.849 | +0.231 | EXCELLENT |
| 6z10_B | 0.520 | 0.747 | +0.228 | EXCELLENT |
| 1yzz_A | 0.594 | 0.765 | +0.171 | EXCELLENT |
| 3eak_A | 0.532 | 0.677 | +0.145 | EXCELLENT |
| 5do2_H | 0.731 | 0.786 | +0.055 | GOOD |
| 6cnw_A | 0.827 | 0.849 | +0.022 | PASS |
| 6xli_A | 0.687 | 0.658 | -0.029 | WARN |
| 6xdg_B | 0.923 | 0.797 | -0.127 | FAIL |
| 1i9r_H | 0.700 | 0.383 | -0.317 | FAIL |
| 6w9g_H | 0.700 | 0.383 | -0.317 | FAIL |
| 8wz5_H | 0.711 | 0.382 | -0.329 | FAIL |
| 2hwz_H | 0.725 | 0.308 | -0.417 | FAIL |
| 8elj_S | 0.859 | 0.332 | -0.527 | FAIL |

### Atlas-24 engineered human VH  (n=24)

| ID | VH2 | VHH2 | Δ | Tier (V1.7.1) |
|---|---:|---:|---:|---|
| 2x89 | 0.456 | 0.728 | +0.273 | EXCELLENT |
| 6sge | 0.491 | 0.689 | +0.199 | EXCELLENT |
| 7eow | 0.572 | 0.764 | +0.192 | EXCELLENT |
| 7d5u | 0.742 | 0.894 | +0.153 | EXCELLENT |
| 7f1g | 0.742 | 0.894 | +0.153 | EXCELLENT |
| 7d5b | 0.742 | 0.894 | +0.153 | EXCELLENT |
| 6jsz | 0.764 | 0.872 | +0.107 | EXCELLENT |
| 7nfr | 0.712 | 0.818 | +0.106 | EXCELLENT |
| 7azb | 0.582 | 0.662 | +0.080 | GOOD |
| 3p9w | 0.578 | 0.624 | +0.047 | PASS |
| 8di5 | 0.666 | 0.683 | +0.017 | PASS |
| 3zhd | 0.813 | 0.827 | +0.014 | PASS |
| 7ooi | 0.627 | 0.639 | +0.012 | WARN |
| 7whi | 0.604 | 0.617 | +0.012 | WARN |
| 7vnd | 0.660 | 0.670 | +0.010 | WARN |
| 7jwb | 0.645 | 0.640 | -0.005 | WARN |
| 7omn | 0.663 | 0.657 | -0.006 | WARN |
| 1ol0 | 0.822 | 0.806 | -0.016 | WARN |
| 3b9v | 0.716 | 0.698 | -0.018 | WARN |
| 7vne | 0.673 | 0.631 | -0.043 | WARN |
| 6j7w | 0.846 | 0.779 | -0.067 | FAIL |
| 5dmj | 0.844 | 0.749 | -0.095 | FAIL |
| 7vke | 0.824 | 0.715 | -0.109 | FAIL |
| 7zf4 | 0.872 | 0.688 | -0.184 | FAIL |

### Murine humanized regular IgG VH  (n=2)

| ID | VH2 | VHH2 | Δ | Tier (V1.7.1) |
|---|---:|---:|---:|---|
| Ocrelizumab | 0.703 | 0.695 | -0.008 | WARN |
| Obinutuzumab | 0.718 | 0.432 | -0.286 | FAIL |

### Lofacimig tandem VH-Fc (humanized camelid)  (n=2)

| ID | VH2 | VHH2 | Δ | Tier (V1.7.1) |
|---|---:|---:|---:|---|
| Lofacimig_VH2 | 0.598 | 0.801 | +0.203 | EXCELLENT |
| Lofacimig_VH1 | 0.557 | 0.740 | +0.183 | EXCELLENT |

### Fully human IgG VH (negative)  (n=15)

| ID | VH2 | VHH2 | Δ | Tier (V1.7.1) |
|---|---:|---:|---:|---|
| Efalizumab | 0.682 | 0.654 | -0.028 | WARN |
| Adalimumab | 0.845 | 0.794 | -0.050 | WARN |
| Cemiplimab | 0.870 | 0.811 | -0.059 | FAIL |
| Canakinumab | 0.870 | 0.762 | -0.108 | FAIL |
| Denosumab | 0.937 | 0.803 | -0.133 | FAIL |
| Enfortumab | 0.947 | 0.811 | -0.135 | FAIL |
| Cilgavimab | 0.810 | 0.658 | -0.152 | FAIL |
| Golimumab | 0.858 | 0.690 | -0.167 | FAIL |
| Durvalumab | 0.965 | 0.794 | -0.171 | FAIL |
| Erenumab | 0.849 | 0.653 | -0.196 | FAIL |
| Bezlotoxumab | 0.880 | 0.415 | -0.465 | FAIL |
| Brodalumab | 0.935 | 0.444 | -0.491 | FAIL |
| Astegolimab | 0.884 | 0.390 | -0.494 | FAIL |
| Anifrolumab | 0.887 | 0.384 | -0.503 | FAIL |
| Burosumab | 0.908 | 0.336 | -0.573 | FAIL |

### Chimeric IgG VH (negative)  (n=3)

| ID | VH2 | VHH2 | Δ | Tier (V1.7.1) |
|---|---:|---:|---:|---|
| Girentuximab | 0.647 | 0.722 | +0.075 | GOOD |
| Andecaliximab | 0.517 | 0.589 | +0.072 | GOOD |
| Vadastuximab | 0.747 | 0.370 | -0.377 | FAIL |

### Naive murine IgG VH (negative)  (n=2)

| ID | VH2 | VHH2 | Δ | Tier (V1.7.1) |
|---|---:|---:|---:|---|
| Abagovomab | 0.559 | 0.367 | -0.192 | FAIL |
| Naptumomab | 0.572 | 0.344 | -0.229 | FAIL |

## Algorithm-target reference

| Target | Δ median | Source |
|---|---:|---|
| **PASS Target** (must reach) | ≥ +0.013 | Atlas-24 engineered human VH median |
| **GOOD Target** (recommended) | ≥ +0.050 | LIKELY band; ≥50% of candidates above this |
| **EXCELLENT Target** (stretch) | ≥ +0.085 | Clinical VHH median (overlap with native VHH distribution) |