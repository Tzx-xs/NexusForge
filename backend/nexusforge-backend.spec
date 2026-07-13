# -*- mode: python ; coding: utf-8 -*-
"""NexusForge 后端 PyInstaller 打包配置

跨平台 spec 文件（Windows / Linux / macOS 通用）
用法：
    cd backend
    pyinstaller --distpath ../out/tauri --workpath ../out/tauri/build nexusforge-backend.spec
"""
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# 后端根目录（spec 文件位于 backend/ 下）
backend_dir = os.path.dirname(os.path.abspath(SPEC))

hiddenimports = [
    'uvicorn.logging',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'sqlalchemy.dialects.sqlite',
    'apscheduler.schedulers.asyncio',
]
hiddenimports += collect_submodules('interfaces')
hiddenimports += collect_submodules('application')
hiddenimports += collect_submodules('domain')
hiddenimports += collect_submodules('infrastructure')
hiddenimports += collect_submodules('engine')
hiddenimports += collect_submodules('agents')
hiddenimports += collect_submodules('config')

a = Analysis(
    ['backend_entry.py'],
    pathex=[backend_dir],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('migrations', 'migrations'),
        ('alembic', 'alembic'),
        ('alembic.ini', '.'),
        ('infrastructure/ai/prompt_packages', 'infrastructure/ai/prompt_packages'),
        ('infrastructure/persistence/schema.sql', 'infrastructure/persistence'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='nexusforge-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='nexusforge-backend',
    strip=False,
    upx=True,
    upx_exclude=[],
    upx_include=[],
)
