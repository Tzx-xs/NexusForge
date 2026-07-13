# 星渊笔前端统一代码检查脚本（PowerShell）
# 依次执行：prettier --check、eslint、vue-tsc、vitest run

$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot ".." "frontend"

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

Set-Location $frontend

Invoke-Step "prettier --check" "npm run format:check"
Invoke-Step "eslint" "npm run lint"
Invoke-Step "vue-tsc" "npm run type-check"
Invoke-Step "vitest" "npm run test"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "All frontend checks passed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
