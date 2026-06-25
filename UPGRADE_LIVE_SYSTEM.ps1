# InSynBio System Upgrade & Sync Script
# This script promotes the current DEV state to the PROD directory for external evaluation.

$ErrorActionPreference = "Stop"
$src = "D:\InSynBio-AI-Research\Antibody_Engineer_Suite"
$dest = "D:\InSynBio-AI-Research\Antibody_Engineer_Suite_PROD"
$vfile = "$src\config\version_control.json"

echo "`n--- STARTING SYSTEM UPGRADE ---"

# 1. Update Version Info in DEV
if (Test-Path $vfile) {
    $v = Get-Content $vfile | ConvertFrom-Json
    $oldBuild = $v.build_id
    $date = Get-Date -Format "yyyyMMdd"
    # Increment build suffix
    $suffix = 1
    if ($oldBuild -match "$date-(\d+)") { $suffix = [int]$matches[1] + 1 }
    $v.build_id = "$date-$( "{0:D3}" -f $suffix )"
    $v.environment = "PROD"
    $v | ConvertTo-Json | Set-Content $vfile
    echo "[1] Version updated to $($v.analysis_version) (Build $($v.build_id))"
}

# 2. Mirror to PROD directory
echo "[2] Mirroring files to PROD directory..."
if (!(Test-Path $dest)) { New-Item -ItemType Directory -Path $dest | Out-Null }

# Use robocopy for efficient mirroring, excluding dev-only and temp folders
# XD = Exclude Directories, XF = Exclude Files
robocopy $src $dest /MIR /XD .git .job_storage .venv __pycache__ .cursor .agent /XF *.log *.tmp .tmp_* /R:2 /W:5 /NFL /NDL /NJH /NJS

# 3. Reset DEV environment tag (so DEV stays DEV)
if (Test-Path $vfile) {
    $v = Get-Content $vfile | ConvertFrom-Json
    $v.environment = "DEV"
    $v | ConvertTo-Json | Set-Content $vfile
}

# 4. Kill old LIVE API processes on Port 8001
echo "[3] Stopping old LIVE API (Port 8001)..."
$netLines = netstat -ano | findstr ":8001" | findstr "LISTENING"
foreach ($line in $netLines) {
    if ($line -match "\s+(\d+)$") {
        $found_pid = $matches[1]
        echo "Killing old LIVE process (PID $found_pid)..."
        taskkill /F /PID $found_pid /T 2>$null
    }
}
Start-Sleep -Seconds 2

# 5. Start new LIVE API in a new window
echo "[4] Starting new LIVE API (Port 8001)..."
$conda_activate = "d:\Users\NextVivo\miniconda3\Scripts\activate.bat"
$start_cmd = "call `"$conda_activate`" anarcii && set KMP_DUPLICATE_LIB_OK=TRUE && cd /d `"$dest`" && python -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --workers 1"
Start-Process cmd -ArgumentList "/k", $start_cmd -WindowStyle Normal
Start-Sleep -Seconds 5

# Verify
$check = netstat -ano | findstr ":8001" | findstr "LISTENING"
if ($check) {
    echo "[OK] LIVE API is UP on port 8001"
} else {
    echo "[WARN] Port 8001 may still be starting — check the LIVE API window"
}

echo "`n==============================================="
echo " UPGRADE COMPLETE  (Build $($v.build_id))"
echo " DEV  : http://localhost:8000  (remains at $src)"
echo " PROD : http://localhost:8001  (now active at $dest)"
echo "===============================================`n"
