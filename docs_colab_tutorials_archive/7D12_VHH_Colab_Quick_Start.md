# 7D12 VHH  - Google Colab 

## 📋 

```
QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS
```

- ****: 117 aa
- ****: EGFR
- ****:  (Alpaca)

## 🚀 

###  1: IgFold（，）⭐⭐

**：**
- ✅ 
- ✅ （1-2 ）
- ✅ 
- ✅  IMGT 

**：**

1. ** Google Colab**
   - ：https://colab.research.google.com/
   -  notebook

2. ** IgFold**
   ```python
   !pip install -q igfold
   !pip install -q py3Dmol
   ```

3. ****
   ```python
   from igfold import IgFoldRunner
   import py3Dmol
   
   # 
   igfold = IgFoldRunner
   
   # 7D12 VHH 
   sequence = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
   
   # 
   pred = igfold.fold(
       "7D12_VHH",
       sequences={"H": sequence},
       do_refine=True,
       do_renum=True
   )
   
   # 
   pred.to_pdb("7d12_igfold.pdb")
   print(f": {pred.plddt.mean:.2f}")
   ```

4. ****
   ```python
   with open("7d12_igfold.pdb", 'r') as f:
       pdb_str = f.read
   
   view = py3Dmol.view(width=800, height=600)
   view.addModel(pdb_str, 'pdb')
   view.setStyle({'cartoon': {'color': 'spectrum'}})
   
   #  CDR
   view.addStyle({'resi': '25-31'}, {'stick': {'colorscheme': 'greenCarbon'}})  # CDR1
   view.addStyle({'resi': '48-56'}, {'stick': {'colorscheme': 'orangeCarbon'}})  # CDR2
   view.addStyle({'resi': '94-106'}, {'stick': {'colorscheme': 'redCarbon'}})  # CDR3
   
   view.zoomTo
   view.show
   ```

###  2: ColabFold (AlphaFold2)⭐

**：**
- ✅ 
- ✅ 
- ✅ 

**：**
- ⚠️ （10-30 ）

**：**

1. ** ColabFold**
   ```python
   !pip install -q "colabfold[alphafold] @ git+https://github.com/sokrypton/ColabFold.git"
   !pip install -q py3Dmol
   ```

2. ****
   ```python
   from colabfold.batch import batch_predict
   from colabfold.utils import setup_environment
   
   setup_environment(use_templates=False, use_amber=False)
   
   sequence = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
   
   queries = [("7D12_VHH", sequence)]
   
   batch_predict(
       queries,
       result_dir="7d12_alphafold_results",
       use_templates=False,
       use_amber=False,
       num_recycles=3,
       num_models=5
   )
   ```

3. ****
   -  `7d12_alphafold_results/` 
   - 

###  3: ESMFold

**：**
- ✅ （1-2 ）
- ✅  GPU

**：**

1. ** ESMFold**
   ```python
   !pip install -q fair-esm
   !pip install -q py3Dmol
   ```

2. ****
   ```python
   import torch
   import esm
   
   model = esm.pretrained.esmfold_v1
   model = model.eval.cuda
   
   sequence = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
   
   with torch.no_grad:
       output = model.infer_pdb(sequence)
   
   with open("7d12_esmfold.pdb", "w") as f:
       f.write(output)
   ```

## 📊 

|  |  |  |  |  |
|------|------|--------|-----------|--------|
| **IgFold** | ⚡⚡⚡  | ⭐⭐⭐⭐  | ✅  | ⭐⭐⭐⭐⭐ |
| **AlphaFold2** | ⏱️  | ⭐⭐⭐⭐⭐  | ❌  | ⭐⭐⭐⭐ |
| **ESMFold** | ⚡⚡⚡  | ⭐⭐⭐  | ❌  | ⭐⭐⭐ |

## 🎯 

1. ****:  ESMFold（1-2 ）
2. ****:  IgFold（1-2 ，）
3. ****:  AlphaFold2（10-30 ）

## 📥 

， PDB ：

```python
from google.colab import files

#  PDB 
files.download("7d12_igfold.pdb")
# 
files.download("7d12_esmfold.pdb")
```

## 🔍 CDR 

 IMGT ：

- **CDR1**:  25-31， `GFWYNH`
- **CDR2**:  48-56， `ITADSGST`
- **CDR3**:  94-106， `AAGGVGWPYFDY`

## 💡 

1. ****:  IgFold，
2. ****:  AlphaFold2
3. ****:  ESMFold
4. ****:  IgFold

## 📝  Notebook

 Jupyter Notebook：`7D12_VHH_Colab_Structure_Prediction.ipynb`

 Google Colab ！
