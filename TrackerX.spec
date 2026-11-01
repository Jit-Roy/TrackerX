# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

runtime_bin = Path(sys.prefix) / "Library" / "bin"
runtime_dlls = [
    (runtime_bin / name, ".")
    for name in ("sqlite3.dll", "liblzma.dll", "libbz2.dll", "libmpdec.dll", "ffi.dll")
    if (runtime_bin / name).exists()
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[(str(source), target) for source, target in runtime_dlls],
    datas=[('assets', 'assets')],
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
    name='TrackerX',
    icon='assets/orbit.ico',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TrackerX',
)
