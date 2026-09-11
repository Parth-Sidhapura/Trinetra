# ============================================================
#  TRINETRA — Terminal A : BACKEND
#  Is terminal mein aur kuch mat chalana. Bas ye khula chhod do.
# ============================================================
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $root "backend")

# venv dhundo (.venv ya venv)
$act = $null
foreach ($v in @(".venv", "venv", "env")) {
    $p = Join-Path (Get-Location) "$v\Scripts\Activate.ps1"
    if (Test-Path $p) { $act = $p; break }
}
if (-not $act) {
    Write-Host "venv nahi mila — bana raha hoon (ek baar ka kaam, 2-3 min)..." -ForegroundColor Yellow
    py -3.12 -m venv .venv
    $act = Join-Path (Get-Location) ".venv\Scripts\Activate.ps1"
    & $act
    python -m pip install --upgrade pip
    pip install -r requirements.txt
} else {
    & $act
}

Write-Host ""
Write-Host "  TRINETRA BACKEND   http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API docs           http://localhost:8000/docs" -ForegroundColor DarkCyan
Write-Host "  Band karne ke liye Ctrl+C" -ForegroundColor DarkGray
Write-Host ""

uvicorn app.main:app --reload --port 8000
