# Therasik / InSynBio 

****: V1.0 · 2026-04-09  
****: InSynBio Web Team

---

## 1. 

|  | Therasik | InSynBio|
|---|---|---|
|  | `https://www.therasik.com` | `https://www.insynbio.com` |
|  | `Antibody_Engineer_Suite/therasik-web-source/` | `Antibody_Engineer_Suite/insynbio-web-source/` |
|  Git  | `github.com/jhuang7908/therasik-web` (main) | `github.com/jhuang7908/insynbio-website` (master) |
|  | `deploy_therasik.ps1` | `deploy_insynbio.ps1` |
|  |  `git push origin main` |  `git push origin master` |
|  | `python scripts\validate_website.py --site therasik` | `python scripts\validate_website.py --site insynbio` |

> **⚠  — **
>
> `Antibody_Engineer_Suite/docs/`  **GitHub Actions → GitHub Pages** ，  
>  `https://jhuang7908.github.io/InSynBio-AI-Research/`，  
> ** www.therasik.com  www.insynbio.com**。
>
>  `docs/`  push ， **** 。  
>  `*-web-source/` ，。

---

## 2. 

，：

- [ ] （therasik / insynbio / ）
- [ ] （`therasik-web-source/`  `insynbio-web-source/`）
- [ ] ，
- [ ] ，：
  ```powershell
  python scripts\validate_website.py --file "therasik-web-source\Therasik_XXX.html"
  ```
- [ ]  +  + 
- [ ] （>200 ），

---

## 3. 

### 3.1 

```
: 、、
: *-web-source/Therasik_XXX.html
:
  - ， window.PAGE_TEXT  JS 
  - （HTML  + JS ）
  -  data-* （/）
```

### 3.2 

```
: <nav class="top-header-nav"> ... </nav>
:
  - 
  -  HTML 
  - : python scripts\validate_website.py --site therasik
  - 
```

### 3.3  / 

```
: KB 、JSON 
: *-web-source/Therasik_*_KB.html    *_db_data.json
:
  - ，data-search 
  - （class="kb-card" ）
  - toggleCard ， onclick="toggleCard(this)"
  - JSON ， HTML 
  -  KB 9 （ 6 ）
```

### 3.4 

```
: images/ 
:
  -  *-web-source/images/ 
  - ， kebab-case
  - HTML : images/xxx.jpg
  - ， HTML 
  - : python scripts\validate_website.py --file ... （R4 ）
```

---

## 4. HTML （ADC Database ）

**（2026-03）**: `Therasik_ADC_Database.html`  AI ，  
 ~4000 ， JS ，  
，tab 、。

****: ，AI 。

### 

1. ** HTML ，**：
   ```powershell
   (Get-Content "therasik-web-source\Therasik_ADC_Database.html" | Select-Object -Last 3) -join "`n"
   #  </body>  </html>
   ```

2. **>3000 ， R1 **：
   ```powershell
   python scripts\validate_website.py --file "therasik-web-source\Therasik_ADC_Database.html"
   ```

3. ****（ heredoc ）；  
   （`StrReplace`）。

4. **<script> / </script> **（R2 ）。

5. **，**：  
    >100 ， >500 。

---

## 5. Commit Message 

：`<>(<>): <>`

|  |  |  |
|---|---|---|
| `feat` | 、、 | `feat(vaccine-kb): add IEDB search panel` |
| `update` | （ bug ） | `update(adc-db): enrich 5 payload entries` |
| `fix` |  bug、、 | `fix(adc-db): restore truncated JS tab logic` |
| `style` |  | `style(nav): tighten mobile header spacing` |
| `sync` |  | `sync(therasik→insynbio): KB anti-copy protection` |
| `chore` | 、 | `chore(deploy): update validate_website rules` |

****：
- ：`update website`、`fix things`、`2026-04-09`
- （/，）
- Commit message  72 

---

## 6.  9 

：`Therasik_Vaccine_KB.html`、`Therasik_CAR_KB.html`、  
`Therasik_ADC_Database.html`、`Therasik_ADA_Database.html`

， 9 （ `[auto]`）：

| # |  |  |  |
|---|---|---|---|
| K1 | `<meta name="robots" content="noindex">`  | `[auto]` |  |
| K2 |  meta （`<meta name="copyright">`） | `[auto]` |  |
| K3 |  CSS：`.kb-protected`  `user-select:none`  | `[auto]` |  |
| K4 |  JS：`contextmenu`  `copy`  | `[auto]` |  |
| K5 | ：`@media print`  `display:none`  | `[auto]` |  |
| K6 |  honeypot （`display:none` ） | `[auto]` |  |
| K7 | Tab （`tab-btn`  + `tab-panel` ） | `[auto]` via R3 | Tab  |
| K8 | /（filter  + `data-search` ） | `[auto]` via R3+R5 |  |
| K9 |  | `[auto]` | / |

 KB ：
```powershell
python scripts\validate_website.py --file "therasik-web-source\Therasik_Vaccine_KB.html" --kb
python scripts\validate_website.py --site therasik --kb
```

---

## 7. 

### Therasik 

```powershell
#  1: 
python scripts\validate_website.py --site therasik

#  2:  FATAL 
python scripts\validate_website.py --site therasik --deploy -m "feat: "
# : .\deploy_therasik.ps1 -Message "feat: "

#  3:  1-2 （: Ctrl+Shift+R）
# https://www.therasik.com/Therasik_Vaccine_KB.html

#  4: （ K7/K8）
# - Tab 
# - /
# - 
```

### InSynBio 

```powershell
python scripts\validate_website.py --site insynbio --deploy -m "feat: "
# https://www.insynbio.com/...
```

### GitHub Pages（，）

```powershell
cd "D:\InSynBio-AI-Research"
git add Antibody_Engineer_Suite/docs/Therasik_XXX.html
git commit -m "docs: "
git push origin compact-layout-v2
# : https://jhuang7908.github.io/InSynBio-AI-Research/Therasik_XXX.html
```

---

## 8. 

### Therasik 

```powershell
# 
cd "D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source"
git log --oneline -10

# 
git revert HEAD --no-edit
git push origin main

#  commit（，）
# git reset --hard <commit-hash>
# git push origin main --force
```

### InSynBio 

```powershell
cd "D:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source"
git log --oneline -10
git revert HEAD --no-edit
git push origin master
```

### 

```powershell
#  git 
cd "D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source"
git checkout -- Therasik_ADC_Database.html
```

---

## 9. 

：

```powershell
#  Therasik KB  InSynBio
$src = "therasik-web-source\Therasik_Vaccine_KB.html"
$dst = "insynbio-web-source\Therasik_Vaccine_KB.html"
Copy-Item $src $dst

# 
python scripts\validate_website.py --file $src
python scripts\validate_website.py --file $dst

# 
.\deploy_therasik.ps1 -Message "sync: vaccine KB protection + IEDB panel"
.\deploy_insynbio.ps1 -Message "sync: vaccine KB protection + IEDB panel"
```

> ：（/、），。

---

## 10. 

```
:

:  python scripts\validate_website.py --file "therasik-web-source\XXX.html"
:    python scripts\validate_website.py --site therasik
+:   python scripts\validate_website.py --site therasik --deploy -m "feat: ..."
KB:  python scripts\validate_website.py --site therasik --kb

:
  Therasik :    Antibody_Engineer_Suite\therasik-web-source\
  InSynBio :    Antibody_Engineer_Suite\insynbio-web-source\
  GitHub Pages:     Antibody_Engineer_Suite\docs\  
  :         Antibody_Engineer_Suite\deploy_therasik.ps1
                    Antibody_Engineer_Suite\deploy_insynbio.ps1

: https://github.com/jhuang7908/therasik-web/commits/main
```
