# ============================================================
#  TRINETRA — Terminal B : FRONTEND
#  Is terminal mein aur kuch mat chalana. Bas ye khula chhod do.
# ============================================================
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $root "frontend")

if (-not (Test-Path "node_modules")) {
    Write-Host "node_modules nahi mila — install kar raha hoon (ek baar ka kaam)..." -ForegroundColor Yellow
    npm install
}

if (-not (Test-Path ".env.local")) {
    Write-Host "!! .env.local missing hai — frontend login nahi kar payega." -ForegroundColor Red
    Write-Host "   .env.local.example dekho aur Supabase URL + anon key bharo." -ForegroundColor Red
}

Write-Host ""
Write-Host "  TRINETRA FRONTEND  http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Band karne ke liye Ctrl+C" -ForegroundColor DarkGray
Write-Host ""

npm run dev
