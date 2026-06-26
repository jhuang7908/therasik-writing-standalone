#!/usr/bin/env bash
# setup_humatch_wsl.sh  — run inside WSL2 Ubuntu-22.04  (no-sudo, conda-based)
# ─────────────────────────────────────────────────────────────────────────────
# Strategy: install Miniconda in WSL user home → conda install hmmer → venv
# No sudo required at any step.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CONDA_PREFIX="$HOME/miniconda3"
CONDA_BIN="$CONDA_PREFIX/bin/conda"
VENV_NAME="humatch"
WIN_TOOLS="/mnt/d/InSynBio-AI-Research/Antibody_Engineer_Suite/tools/immunotools"
HM_DIR="$WIN_TOOLS/Humatch"

# ── 1. Miniconda (if not present) ────────────────────────────────────────────
echo ">>> [1/7] Check / install Miniconda in WSL"
if [ -f "$CONDA_BIN" ]; then
    echo "  Miniconda already at $CONDA_PREFIX"
else
    echo "  Downloading Miniconda3..."
    curl -fsSL "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" \
        -o /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p "$CONDA_PREFIX"
    rm /tmp/miniconda.sh
    echo "  Miniconda installed OK"
fi

# Ensure conda is usable in this shell
source "$CONDA_PREFIX/etc/profile.d/conda.sh"

# ── 2. hmmer via bioconda ─────────────────────────────────────────────────────
echo ">>> [2/7] Install hmmer via bioconda"
if ! "$CONDA_BIN" run -n base hmmbuild -h &>/dev/null 2>&1; then
    # Use only conda-forge + bioconda (no Anaconda default channels requiring ToS re-confirmation)
    "$CONDA_BIN" install -n base hmmer=3.4 \
        --override-channels -c conda-forge -c bioconda \
        -y --quiet
    echo "  hmmer installed"
else
    echo "  hmmer already available"
fi
"$CONDA_BIN" run -n base hmmbuild -h 2>&1 | grep "^# HMMER" || true

# ── 3. Clone Humatch ──────────────────────────────────────────────────────────
echo ">>> [3/7] Clone Humatch (OPIG)"
mkdir -p "$WIN_TOOLS"
if [ ! -d "$HM_DIR/.git" ]; then
    git clone https://github.com/oxpig/Humatch.git "$HM_DIR"
else
    echo "  already cloned, pulling latest"
    git -C "$HM_DIR" pull --ff-only
fi

# ── 4. Create conda env (Python 3.9) ─────────────────────────────────────────
echo ">>> [4/7] Create conda env: $VENV_NAME (Python 3.9)"
if "$CONDA_BIN" env list | grep -q "^${VENV_NAME}\s"; then
    echo "  env already exists"
else
    "$CONDA_BIN" create -n "$VENV_NAME" python=3.9 -y --quiet
fi
conda activate "$VENV_NAME"

# ── 5. Core Python deps ───────────────────────────────────────────────────────
echo ">>> [5/7] Install Python deps"
pip install --upgrade pip --quiet
pip install "tensorflow>=2.17.0" scikit-learn pandas "numpy>=1.26.4" \
    biopython pyyaml seaborn matplotlib --quiet

# ── 6. ANARCI ─────────────────────────────────────────────────────────────────
echo ">>> [6/7] Install ANARCI"
# Expose hmmer binaries from conda base during ANARCI install and runtime
export PATH="$CONDA_PREFIX/bin:$PATH"
pip install git+https://github.com/oxpig/ANARCI.git --quiet

# ── 7. HuMAtch ────────────────────────────────────────────────────────────────
echo ">>> [7/7] Install HuMAtch"
pip install -e "$HM_DIR" --quiet

# ── Smoke test ────────────────────────────────────────────────────────────────
echo ""
echo "=== Smoke tests ==="
python -c "from Humatch.classify import predict_from_list_of_seq_strs; print('  Humatch Python import OK')"
Humatch-classify --help 2>&1 | head -2 || true

echo ""
echo "=== HuMAtch WSL install complete ==="
echo "Conda env : $CONDA_PREFIX/envs/$VENV_NAME"
echo "Humatch-classify: $CONDA_PREFIX/envs/$VENV_NAME/bin/Humatch-classify"
echo ""
echo "CNN weights (~50 MB) auto-download from zenodo.org/records/13764770 on first run."
