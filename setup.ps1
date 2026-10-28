#requires -Version 7.0
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw '未找到 uv，请先安装 uv 并加入 PATH。' }
if (-not (Get-Command pnpm.cmd -ErrorAction SilentlyContinue)) { throw '未找到 pnpm，请先安装 Node.js 与 pnpm。' }
Write-Host '创建 Python 3.12 环境并安装锁定依赖…' -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & uv venv --python 3.12
    if ($LASTEXITCODE -ne 0) { throw '创建 uv 环境失败。' }
}
& uv sync --frozen
if ($LASTEXITCODE -ne 0) { throw 'Python 依赖安装失败。' }
Push-Location -LiteralPath (Join-Path $PSScriptRoot 'frontend')
try {
    & pnpm.cmd install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败。' }
    & pnpm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw '前端构建失败。' }
} finally { Pop-Location }
& uv run --frozen python -X utf8 -c "from backend.catalog import options; print('参数目录已就绪：', len(options()))"
if ($LASTEXITCODE -ne 0) { throw '参数目录核对失败。' }
Write-Host '安装完成。运行 pwsh -NoProfile -File .\start.ps1 启动。' -ForegroundColor Green
