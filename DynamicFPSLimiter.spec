# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Source\\DFL_v4.py'],
    pathex=[],
    binaries=[],
    datas=[('Source\\DynamicFPSLimiter.ico', '.'), ('Source\\rtss-cli.exe', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DynamicFPSLimiter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='Source\\version.txt',
    uac_admin=True,
    icon=['Source\\DynamicFPSLimiter.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DynamicFPSLimiter',
)
