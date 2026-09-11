# ============================================================
#  TRINETRA — naye UI ko purane frontend ke upar lagao
#  Ye sirf EK BAAR chalana hai. Terminal C mein.
#  .env.local aur node_modules ko haath nahi lagta.
# ============================================================
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$zip  = Join-Path $HOME "Downloads\trinetra-ui.zip"

if (-not (Test-Path $zip)) {
    Write-Host "trinetra-ui.zip Downloads mein nahi mila." -ForegroundColor Red
    Write-Host "Chat se dobara download karo, phir ye script chalao." -ForegroundColor Red
    exit 1
}

# purane frontend ka backup — agar kuch tootey toh wapas la sakte ho
$stamp  = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $root "frontend-backup-$stamp"
Write-Host "Backup ban raha hai -> $backup" -ForegroundColor DarkGray
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item (Join-Path $root "frontend\app")        $backup -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $root "frontend\components") $backup -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $root "frontend\tailwind.config.ts") $backup -Force -ErrorAction SilentlyContinue

Write-Host "Naya UI extract ho raha hai..." -ForegroundColor Cyan
Expand-Archive -Path $zip -DestinationPath $root -Force

# next ka cache saaf — purane CSS ke bache-khuche hisse hata do
$next = Join-Path $root "frontend\.next"
if (Test-Path $next) { Remove-Item $next -Recurse -Force -ErrorAction SilentlyContinue }

Write-Host ""
Write-Host "  Ho gaya." -ForegroundColor Green
Write-Host "  Ab Terminal B mein Ctrl+C karke 2-START-FRONTEND.ps1 dobara chalao." -ForegroundColor Green
Write-Host ""
