# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

import platform
from mpf._version import __version__ as mpf_version

datas = [('mpf/config_spec.yaml', 'config_spec.yaml'), ('mpf/mpfconfig.yaml', 'mpfconfig.yaml')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('mpf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

filename = "_".join([
    f"mpf-{mpf_version}",
    f"{platform.python_implementation().lower()}-{platform.python_version()}",
    platform.system().lower(),
    platform.machine().lower()
])

a = Analysis(
    ['mpf/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['mpf.tests', 'mpf.wire', 'mpf.platforms.p_roc', 'mpf.platforms.p3_roc', 'mpf.platforms.pinproc'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=filename,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
