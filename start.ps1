#requires -Version 7.0
param([switch]$OpenBrowser)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe') -or -not (Test-Path -LiteralPath 'frontend\dist\index.html')) {
    throw '环境或前端产物不存在，请先运行 pwsh -NoProfile -File .\setup.ps1。'
}
Write-Host 'sqlmap 中文工作台：http://127.0.0.1:9955 （Ctrl+C 关闭服务）' -ForegroundColor Cyan
if ($OpenBrowser) { Start-Process 'http://127.0.0.1:9955' }
& '.\.venv\Scripts\python.exe' -m backend
exit $LASTEXITCODE
