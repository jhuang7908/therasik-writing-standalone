@echo off
REM === HER2 VHH De Novo Phase1 Full Pipeline ===
REM Runs independently of Cursor IDE
set KMP_DUPLICATE_LIB_OK=TRUE
set PYTHONUNBUFFERED=1
set PYTHONPATH=d:\InSynBio-AI-Research\Antibody_Engineer_Suite

set AFFMAT=d:\Users\NextVivo\miniconda3\envs\affmat\python.exe
set ANARCII=d:\Users\NextVivo\miniconda3\envs\anarcii\python.exe
set PROJ=projects\denovo_HER2_VGRW_SR_R2_v2
set PIPE=pipeline
set LOG=projects\denovo_HER2_VGRW_SR_R2_v2\phase1_generation\pipeline_run.log

cd /d d:\InSynBio-AI-Research\Antibody_Engineer_Suite

echo ============================================================ >> %LOG%
echo Phase1 pipeline started at %date% %time% >> %LOG%
echo ============================================================ >> %LOG%

echo [1/5] MPNN generation (300 x 4 temps) ...
echo [1/5] MPNN started at %time% >> %LOG%
%AFFMAT% %PIPE%\run_mpnn_v2.py --project_dir %PROJ% --n_seqs 300 --temps "0.2 0.3 0.35 0.4" --seed 42 --force_regen
if %errorlevel% neq 0 (
    echo [FAIL] MPNN failed with exit %errorlevel% >> %LOG%
    echo MPNN FAILED. See log.
    pause
    exit /b %errorlevel%
)
echo [1/5] MPNN done at %time% >> %LOG%

echo [2/5] T0 OASis scoring ...
echo [2/5] T0 started at %time% >> %LOG%
%ANARCII% %PIPE%\run_t0_t1_phase1.py --project_dir %PROJ% --step t0_oasis
if %errorlevel% neq 0 (
    echo [FAIL] T0 failed >> %LOG%
    echo T0 FAILED.
    pause
    exit /b %errorlevel%
)
echo [2/5] T0 done at %time% >> %LOG%

echo [3/5] T1 AbLang scoring ...
echo [3/5] T1 started at %time% >> %LOG%
%AFFMAT% %PIPE%\run_t0_t1_phase1.py --project_dir %PROJ% --step t1_ablang
if %errorlevel% neq 0 (
    echo [FAIL] T1 failed >> %LOG%
    echo T1 FAILED.
    pause
    exit /b %errorlevel%
)
echo [3/5] T1 done at %time% >> %LOG%

echo [4/5] T0.5 Clustering ...
echo [4/5] Cluster started at %time% >> %LOG%
%AFFMAT% %PIPE%\cluster_and_filter_v2.py --project_dir %PROJ% --max_survivors 80
if %errorlevel% neq 0 (
    echo [FAIL] Cluster failed >> %LOG%
    echo Cluster FAILED.
    pause
    exit /b %errorlevel%
)
echo [4/5] Cluster done at %time% >> %LOG%

echo [5/5] Rank for Phase 2 ...
echo [5/5] Rank started at %time% >> %LOG%
%AFFMAT% %PIPE%\rank_phase1_for_p2.py --project_dir %PROJ%
if %errorlevel% neq 0 (
    echo [FAIL] Rank failed >> %LOG%
    echo Rank FAILED.
    pause
    exit /b %errorlevel%
)
echo [5/5] Rank done at %time% >> %LOG%

echo ============================================================
echo   Phase1 pipeline COMPLETE at %time%
echo ============================================================
echo Phase1 pipeline COMPLETE at %time% >> %LOG%
echo.
echo Results in: %PROJ%\phase1_generation\
echo   mpnn_generation_report.json
echo   p2_input_topk.fasta
echo   p2_ranked_full.csv
echo.
pause
