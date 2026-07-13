# 星渊笔后端统一代码检查脚本（PowerShell）
# 依次执行：ruff format --check、ruff check、mypy、pytest、api_check

$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot ".." "backend"

function Step-Header($msg) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host $msg -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Invoke-Step($name, $cmd) {
    Step-Header $name
    try {
        Invoke-Expression $cmd
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FAILED: $name (exit code $LASTEXITCODE)" -ForegroundColor Red
            exit $LASTEXITCODE
        }
        Write-Host "PASSED: $name" -ForegroundColor Green
    }
    catch {
        Write-Host "FAILED: $name - $_" -ForegroundColor Red
        exit 1
    }
}

Set-Location $backend

Invoke-Step "ruff format --check" "ruff format --check ."
Invoke-Step "ruff check" "ruff check ."
Invoke-Step "mypy" "mypy ."
Invoke-Step "pytest" "pytest"

Step-Header "api_check (requires running server)"
python api_check.py --create-fixtures
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: api_check" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "PASSED: api_check" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "All backend checks passed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
