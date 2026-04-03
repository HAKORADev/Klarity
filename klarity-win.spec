# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Klarity CPU-only Windows binary (onedir)

import os
import sys

block_cipher = None
src_dir = os.path.join(SPECPATH, 'src')

hiddenimports = [
    'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.sip',
    'torch', 'torch.nn', 'torch.nn.functional', 'torch.cuda',
    'numpy', 'cv2', 'tqdm', 'requests', 'urllib.request', 'urllib.error',
    'json', 'pathlib', 'model_downloader', 'nafnet_arch', 'rife_arch', 'sr_arch',
]

datas = [
    (os.path.join(src_dir, 'logo.png'), '.'),
    (os.path.join(SPECPATH, 'logo.ico'), '.'),
]

# Collect PyQt5 data files
from PyInstaller.utils.hooks import collect_data_files
datas += collect_data_files('PyQt5', include_py_files=False)

a = Analysis(
    [os.path.join(src_dir, 'klarity.py')],
    pathex=[src_dir],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        'matplotlib', 'scipy', 'scikit-learn', 'PIL', 'tkinter',
        'test', 'IPython', 'jupyter', 'notebook',
        'PySide2', 'PySide6', 'PyQt6',
    ],
    noarchive=False,
)

exe = EXE(
    name='klarity',
    console=True,               # Show console for CLI mode; GUI mode hides it via ctypes
    icon=os.path.join(SPECPATH, 'logo.ico'),
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    exclude_binaries=True,      # onedir mode
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,                # strip not supported on Windows
    upx=True,
    upx_exclude=[],
    name='klarity',
)
