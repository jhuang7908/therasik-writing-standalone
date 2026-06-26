# setup_immunotools.ps1
# ─────────────────────────────────────────────────────────────────────────────
#  ImmunogenNN  HuMAtch  conda 
#
# （ Antibody_Engineer_Suite ）：
#   .\scripts\setup_immunotools.ps1
#
# （）：
#   $IMMUNOGENN_ENV  : ImmunogenNN  env（ anarcii，）
#   $HUMATCH_ENV     : HuMAtch  env （ humatch，）
#   $TOOLS_DIR       : 
# ─────────────────────────────────────────────────────────────────────────────
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT        = "$PSScriptRoot\.."
$TOOLS_DIR   = "$ROOT\tools\immunotools"
$CONDA       = "d:\Users\NextVivo\miniconda3\Scripts\conda.exe"

$IMMUNOGENN_ENV = "anarcii"
$HUMATCH_ENV    = "humatch"

# ── helpers ──────────────────────────────────────────────────────────────────
function Step([string]$msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }

# ── 1. ImmunogenNN ────────────────────────────────────────────────────────────
Step "Cloning ImmunoGeNN (Novo Nordisk)"
$ig_dir = "$TOOLS_DIR\ImmunoGeNN"
if (-not (Test-Path "$ig_dir\.git")) {
    git clone https://github.com/novonordisk-research/ImmunoGeNN.git "$ig_dir"
} else {
    Write-Host "  already cloned, pulling latest"
    git -C "$ig_dir" pull --ff-only
}

# Unzip data_record.zip if not yet done
$data_zip = "$ig_dir\data_record.zip"
$data_dir  = "$ig_dir\data"
if ((Test-Path $data_zip) -and -not (Test-Path "$data_dir\input.fasta")) {
    Step "Unzipping data_record.zip"
    Expand-Archive -Path $data_zip -DestinationPath "$ig_dir" -Force
}

Step "Installing ImmunogenNN into conda env: $IMMUNOGENN_ENV"
& $CONDA run -n $IMMUNOGENN_ENV pip install -r "$ig_dir\requirements.txt" --quiet
& $CONDA run -n $IMMUNOGENN_ENV pip install -e "$ig_dir" --quiet 2>&1 | Where-Object { $_ -notmatch "^WARNING" }
Write-Host "  ImmunogenNN installed OK"

# ── 2. HuMAtch ───────────────────────────────────────────────────────────────
$hm_dir = "$TOOLS_DIR\Humatch"
Step "Cloning Humatch (OPIG)"
if (-not (Test-Path "$hm_dir\.git")) {
    git clone https://github.com/oxpig/Humatch.git "$hm_dir"
} else {
    Write-Host "  already cloned, pulling latest"
    git -C "$hm_dir" pull --ff-only
}

$humatch_installed = & $CONDA env list | Select-String "^$HUMATCH_ENV\s"
if (-not $humatch_installed) {
    Step "Creating conda env: $HUMATCH_ENV (Python 3.9 — required by Humatch)"
    & $CONDA create -n $HUMATCH_ENV python=3.9 -y --quiet
}

Step "Installing HuMAtch dependencies into conda env: $HUMATCH_ENV"
# hmmer via conda (ANARCI requirement)
& $CONDA install -n $HUMATCH_ENV -c bioconda hmmer=3.4 -y --quiet
& $CONDA run -n $HUMATCH_ENV pip install "tensorflow>=2.17.0" scikit-learn pandas "numpy>=1.26.4" biopython pyyaml seaborn matplotlib ipykernel --quiet
# ANARCI (required, as noted in Humatch README)
& $CONDA run -n $HUMATCH_ENV pip install git+https://github.com/oxpig/ANARCI.git --quiet 2>&1 | Where-Object { $_ -notmatch "^WARNING" }
& $CONDA run -n $HUMATCH_ENV pip install -e "$hm_dir" --quiet 2>&1 | Where-Object { $_ -notmatch "^WARNING" }
# CNN weights + germline arrays auto-download on first run from zenodo.org/records/13764770
# If auto-download fails, manually download .h5 (x3) and .npy (x24) files to:
#   Humatch/Humatch/trained_models/  and  Humatch/Humatch/germline_likeness_lookup_arrays/
# then re-run: pip install -e "$hm_dir"
Write-Host "  HuMAtch installed OK"

# ── 3. Smoke tests ────────────────────────────────────────────────────────────
Step "Smoke testing ImmunogenNN"
& $CONDA run -n $IMMUNOGENN_ENV python -c "import immunogenn; print('  immunogenn import OK')" 2>&1

Step "Smoke testing HuMAtch"
& $CONDA run -n $HUMATCH_ENV python -c "from Humatch.classify import predict_from_list_of_seq_strs; print('  Humatch import OK')" 2>&1

Write-Host "`n=== All done ===" -ForegroundColor Green
Write-Host "Run the triple evaluation script:"
Write-Host "  conda run -n anarcii python projects\clinical_ref_mAbs_smart_cmc\run_triple_immunotools.py" -ForegroundColor Yellow
