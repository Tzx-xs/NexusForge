# NexusForge Windows 桌面应用打包脚本
#
# 使用方法：
#   1. 安装前置依赖（见下方注释）
#   2. 在 PowerShell 中执行：  .\scripts\build_windows.ps1
#   3. 产物在 frontend\src-tauri\target\release\bundle\nsis\*.exe
#
# 前置依赖（首次运行前安装）：
#   - Python 3.14:  https://www.python.org/downloads/
#   - Node.js 20+:  https://nodejs.org/
#   - Rust:         https://rustup.rs/
#   - Microsoft C++ Build Tools (VS Installer 中勾选"使用 C++ 的桌面开发")
#   - WebView2 Runtime (Win11 自带，Win10 需安装): https://developer.microsoft.com/microsoft-edge/webview2/
#
# 本脚本会自动安装：pip 依赖、PyInstaller、npm 依赖

[CmdletBinding()]
param(
    [switch]$SkipFrontendBuild,  # 跳过前端构建（已构建过时使用）
    [switch]$SkipBackendBuild    # 跳过后端打包（已打包过时使用）
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$OutDir = Join-Path $ProjectRoot "out\tauri"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NexusForge Windows 桌面应用打包" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "项目根目录: $ProjectRoot"
Write-Host ""

# ─── 0. 环境检查 ───────────────────────────────────────────────
Write-Host "[0/6] 检查环境..." -ForegroundColor Yellow

function Test-Command($cmd) {
    $null = Get-Command $cmd -ErrorAction SilentlyContinue
    return $?
}

$checks = @(
    @{ Name = "Python 3.14"; Cmd = "python"; Check = { python --version 2>&1 | Select-String "3\.14" } },
    @{ Name = "Node.js"; Cmd = "node"; Check = { node --version } },
    @{ Name = "npm"; Cmd = "npm"; Check = { npm --version } },
    @{ Name = "Rust (cargo)"; Cmd = "cargo"; Check = { cargo --version } }
)

$failed = $false
foreach ($check in $checks) {
    if (Test-Command $check.Cmd) {
        $version = & $check.Check
        Write-Host "  ✓ $($check.Name): $version" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $($check.Name) 未安装" -ForegroundColor Red
        $failed = $true
    }
}

if ($failed) {
    Write-Host "`n请先安装缺失的依赖，参考脚本头部的注释说明。" -ForegroundColor Red
    exit 1
}

# ─── 1. 安装后端依赖 + PyInstaller ─────────────────────────────
Write-Host "`n[1/6] 安装后端 Python 依赖..." -ForegroundColor Yellow
Push-Location $BackendDir
try {
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install pyinstaller
    Write-Host "  ✓ 后端依赖安装完成" -ForegroundColor Green
} finally {
    Pop-Location
}

# ─── 2. 安装前端依赖 ───────────────────────────────────────────
Write-Host "`n[2/6] 安装前端依赖..." -ForegroundColor Yellow
Push-Location $FrontendDir
try {
    npm ci
    Write-Host "  ✓ 前端依赖安装完成" -ForegroundColor Green
} finally {
    Pop-Location
}

# ─── 3. 前端构建 ───────────────────────────────────────────────
if (-not $SkipFrontendBuild) {
    Write-Host "`n[3/6] 构建前端..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    try {
        $env:VITE_ENABLE_TIPTAP_EDITOR = "true"
        npm run build
        Write-Host "  ✓ 前端构建完成" -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host "`n[3/6] 跳过前端构建" -ForegroundColor Yellow
}

# ─── 4. PyInstaller 打包后端 ───────────────────────────────────
if (-not $SkipBackendBuild) {
    Write-Host "`n[4/6] PyInstaller 打包后端..." -ForegroundColor Yellow
    Push-Location $BackendDir
    try {
        # 清理旧的打包产物
        if (Test-Path $OutDir) {
            Remove-Item -Recurse -Force $OutDir
        }
        New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

        python -m PyInstaller `
            --name nexusforge-backend `
            --onedir `
            --distpath $OutDir `
            --workpath (Join-Path $OutDir "build") `
            --specpath $OutDir `
            --add-data "config;config" `
            --add-data "migrations;migrations" `
            --add-data "infrastructure\ai\prompt_packages;infrastructure\ai\prompt_packages" `
            --add-data "infrastructure\persistence\schema.sql;infrastructure\persistence" `
            --add-data "alembic.ini;." `
            --add-data "alembic;alembic" `
            --hidden-import uvicorn.logging `
            --hidden-import uvicorn.protocols `
            --hidden-import uvicorn.protocols.http `
            --hidden-import uvicorn.protocols.http.auto `
            --hidden-import uvicorn.protocols.websockets `
            --hidden-import uvicorn.protocols.websockets.auto `
            --hidden-import uvicorn.lifespan `
            --hidden-import uvicorn.lifespan.on `
            --hidden-import sqlalchemy.dialects.sqlite `
            --hidden-import apscheduler.schedulers.asyncio `
            --collect-submodules interfaces `
            --collect-submodules application `
            --collect-submodules domain `
            --collect-submodules infrastructure `
            --collect-submodules engine `
            --collect-submodules agents `
            --collect-submodules config `
            --noconfirm `
            backend_entry.py

        $backendExe = Join-Path $OutDir "nexusforge-backend\nexusforge-backend.exe"
        if (Test-Path $backendExe) {
            $size = (Get-Item $backendExe).Length / 1MB
            Write-Host ("  ✓ 后端打包完成: {0:N1} MB" -f $size) -ForegroundColor Green
        } else {
            Write-Host "  ✗ 后端打包失败：可执行文件未生成" -ForegroundColor Red
            exit 1
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "`n[4/6] 跳过后端打包" -ForegroundColor Yellow
}

# ─── 5. Tauri 打包桌面应用 ─────────────────────────────────────
Write-Host "`n[5/6] Tauri 打包桌面应用（首次编译较慢，约 10-20 分钟）..." -ForegroundColor Yellow
Push-Location $FrontendDir
try {
    $env:VITE_ENABLE_TIPTAP_EDITOR = "true"
    npx tauri build --bundles nsis
    Write-Host "  ✓ Tauri 打包完成" -ForegroundColor Green
} finally {
    Pop-Location
}

# ─── 6. 显示产物路径 ───────────────────────────────────────────
Write-Host "`n[6/6] 打包产物:" -ForegroundColor Yellow
$nsisDir = Join-Path $FrontendDir "src-tauri\target\release\bundle\nsis"
if (Test-Path $nsisDir) {
    Get-ChildItem $nsisDir -Filter "*.exe" | ForEach-Object {
        $size = $_.Length / 1MB
        Write-Host ("  ✓ {0} ({1:N1} MB)" -f $_.FullName, $size) -ForegroundColor Green
    }
} else {
    Write-Host "  ✗ NSIS 安装包未生成，请检查上方日志" -ForegroundColor Red
}

$exePath = Join-Path $FrontendDir "src-tauri\target\release\nexusforge.exe"
if (Test-Path $exePath) {
    $size = (Get-Item $exePath).Length / 1MB
    Write-Host ("  ✓ 便携版: {0} ({1:N1} MB)" -f $exePath, $size) -ForegroundColor Green
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  打包完成！" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n安装方法：" -ForegroundColor White
Write-Host "  1. 双击 NSIS .exe 安装包，按提示安装" -ForegroundColor White
Write-Host "  2. 或直接运行便携版 nexusforge.exe" -ForegroundColor White
Write-Host "`n首次运行时应用会自动启动后端，无需额外配置。" -ForegroundColor White
