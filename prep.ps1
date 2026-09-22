# Run before the live demo: clean memory (no substitution decision on record), fresh graphs, tabs open.
# Usage:  powershell -ExecutionPolicy Bypass -File .\prep.ps1     (~70 s)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $root ".venv\Scripts\python.exe"

docker info *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "Docker engine is not running - start Docker Desktop first (sandbox falls back to UNSANDBOXED otherwise)." -ForegroundColor Yellow }

& $py (Join-Path $root "seed.py") --reset --visualize
foreach ($name in "personal", "office", "public") {
    $html = Join-Path $root "graph\$name.html"
    if (Test-Path $html) { Start-Process $html }
}
Write-Host ""
Write-Host "Memory is clean. Start the demo with:  .venv\Scripts\python.exe cli.py" -ForegroundColor Green
Write-Host "Then: /before  ->  inbox question  ->  substitute question  ->  send  ->  /before" -ForegroundColor Green
