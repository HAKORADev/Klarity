# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/klarity.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src/logo.png', '.')],
    hiddenimports=['model_downloader', 'gui', 'nafnet_arch', 'hat_gan_arch', 'sr_arch', 'rife_arch'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='klarity',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='klarity',
)
