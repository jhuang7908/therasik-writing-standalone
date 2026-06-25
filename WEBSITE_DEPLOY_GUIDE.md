#  | Dual-Site Deploy Guide

## 

|  |  |  | GitHub  |  |  |
|------|------|------|------------|------|-------------|
| www.insynbio.com | InSynBio |  | `jhuang7908/insynbio-website` | `master` | `insynbio-web-source/` |
| www.therasik.com | Therasik |  | `jhuang7908/therasik-web` | `main` | `therasik-web-source/` |

---

## 

###  AbEngineCore 

- ：`Antibody_Engineer_Suite`， `http://localhost:8000/`（ `START_DEMO.bat`  `uvicorn api.main:app --port 8000`）。
-  HTTP API  [`README.md`](README.md)  **Console UI ↔ API capability matrix**；`/health`  `git_sha`（ `ABENGINECORE_GIT_SHA`）。

###  www.insynbio.com

1.  `Antibody_Engineer_Suite\insynbio-web-source\`  HTML 
2. ：

```powershell
cd D:\InSynBio-AI-Research\Antibody_Engineer_Suite
.\deploy_insynbio.ps1
```

：

```powershell
.\deploy_insynbio.ps1 -Message "Update antibody service page"
```

###  www.therasik.com

1.  `Antibody_Engineer_Suite\therasik-web-source\`  HTML 
2. ：

```powershell
cd D:\InSynBio-AI-Research\Antibody_Engineer_Suite
.\deploy_therasik.ps1
```

：

```powershell
.\deploy_therasik.ps1 -Message ""
```

---

## 

###  `insynbio-web-source/`（www.insynbio.com）

|  |  |
|------|------|
| `index.html` |  |
| `InSynBio_Antibody_Developability_Assessment_Page.html` |  |
| `InSynBio_Bispecific_Antibody_Design_Page.html` |  |
| `InSynBio_CART_Design_Page.html` | CAR-T  |
| `case_mumab4d5_humanization_en.html` | ：muMAb4D5  |
| `thanks.html` | / |
| `CNAME` | `insynbio.com`|

###  `therasik-web-source/`（www.therasik.com）

|  |  |
|------|------|
| `index.html` |  |
| `Therasik_Antibody_Page.html` |  |
| `Therasik_Bispecific_Page.html` |  |
| `Therasik_CART_Page.html` | CAR-T  |
| `Therasik_CART_Design_Page.html` | CAR-T  |
| `thanks.html` | / |
| `CNAME` | `www.therasik.com`|

---

## 

### 
- `therasik-web-clone/` → **** InSynBio 
- `therasik-web-source/` → **** Therasik 

### 
- **** HTML  `therasik-web-clone/`
- **** HTML  `therasik-web-source/`
- **** `CNAME` 
- ****（.md、.py、.pdf ）

### 
- ：`<html lang="en">`
- ：`<html lang="zh">`

---

## 

### ？
GitHub Pages  1–2 。（Ctrl+Shift+R ）。

### ？
```powershell
#  insynbio.com
gh api repos/jhuang7908/insynbio-website/pages --jq '.status'

#  therasik.com
gh api repos/jhuang7908/therasik-web/pages --jq '.status'
```

### ？
```powershell
# 
cd insynbio-web-source
git log --oneline -5          # 
git reset --hard <commit_hash>
git push origin master --force

# 
cd therasik-web-source
git log --oneline -5
git reset --hard <commit_hash>
git push origin main --force
```

---

## 

|  |  |  |
|--------|------|------|
| `insynbio-web-source/` | **insynbio.com ** |  InSynBio  |
| `therasik-web-source/` | **therasik.com ** | ， |
| `therasik-web-deploy/` |  | ****， |
| `Web_Projects/insynbio_com/` |  | ， |
| `Web_Projects/therasik_com/` |  | ， |
