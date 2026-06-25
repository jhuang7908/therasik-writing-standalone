@echo off
REM === Phase1 round 2: more sampling + different RNG seed ===
REM Run AFTER run_full_phase1.bat finishes. Overwrites phase1 outputs.
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
echo Phase1 ROUND2 started at %date% %time% >> %LOG%
echo ============================================================ >> %LOG%

echo [R2 1/5] MPNN 400 seqs x 4 temps, seed 43 ...
echo [R2 1/5] MPNN started at %time% >> %LOG%
%AFFMAT% %PIPE%\run_mpnn_v2.py --project_dir %PROJ% --n_seqs 400 --temps "0.2 0.3 0.35 0.4" --seed 43 --force_regen
if %errorlevel% neq 0 (
    echo [FAIL] R2 MPNN failed >> %LOG%
    echo MPNN FAILED.
    pause
    exit /b %errorlevel%
)
echo [R2 1/5] MPNN done at %time% >> %LOG%

echo [R2 2/5] T0 ...
echo [R2 2/5] T0 started at %time% >> %LOG%
%ANARCII% %PIPE%\run_t0_t1_phase1.py --project_dir %PROJ% --step t0_oasis
if %errorlevel% neq 0 ( echo [FAIL] T0 >> %LOG% & pause & exit /b %errorlevel% )
echo [R2 2/5] T0 done at %time% >> %LOG%

echo [R2 3/5] T1 ...
echo [R2 3/5] T1 started at %time% >> %LOG%
%AFFMAT% %PIPE%\run_t0_t1_phase1.py --project_dir %PROJ% --step t1_ablang
if %errorlevel% neq 0 ( echo [FAIL] T1 >> %LOG% & pause & exit /b %errorlevel% )
echo [R2 3/5] T1 done at %time% >> %LOG%

echo [R2 4/5] Cluster (max 80 survivors) ...
echo [R2 4/5] Cluster started at %time% >> %LOG%
%AFFMAT% %PIPE%\cluster_and_filter_v2.py --project_dir %PROJ% --max_survivors 80
if %errorlevel% neq 0 ( echo [FAIL] Cluster >> %LOG% & pause & exit /b %errorlevel% )
echo [R2 4/5] Cluster done at %time% >> %LOG%

echo [R2 5/5] Rank ...
echo [R2 5/5] Rank started at %time% >> %LOG%
%AFFMAT% %PIPE%\rank_phase1_for_p2.py --project_dir %PROJ% --top_k 80
if %errorlevel% neq 0 ( echo [FAIL] Rank >> %LOG% & pause & exit /b %errorlevel% )
echo [R2 5/5] Rank done at %time% >> %LOG%

echo Phase1 ROUND2 COMPLETE at %time% >> %LOG%
echo.
echo ROUND2 COMPLETE. See %PROJ%\phase1_generation\
pause
