# PyInstaller spec for headcleaner.
#
# Build the static binary:
#   pip install pyinstaller
#   pyinstaller packaging/pyinstaller/headcleaner.spec --clean
#
# Output: dist/headcleaner/headcleaner.exe (Windows) or
#         dist/headcleaner/headcleaner (Linux/macOS)
#
# Size: ~30 MB compressed (single file), ~80 MB extracted.

# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Resolve paths relative to repo root
ROOT = Path(SPECPATH).resolve().parent.parent.parent

a = Analysis(
    [str(ROOT / "src" / "headcleaner" / "cli.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        # include the theme module, all engines, all emitters
        (str(ROOT / "src" / "headcleaner"), "headcleaner"),
    ],
    hiddenimports=[
        # textual / rich dynamically import many submodules
        "textual.widgets._data_table",
        "textual.widgets._tabbed_content",
        "textual._ansi_theme",
        # adapters that load lazily
        "headcleaner.engines.officecli",
        "headcleaner.engines.pdf",
        "headcleaner.engines.html",
        "headcleaner.engines.txt",
        "headcleaner.engines.md",
        "headcleaner.engines.csv_json",
        "headcleaner.engines.eml",
        "headcleaner.engines.pst",
        "headcleaner.engines.legacy_office",
        # watchfiles Rust binding
        "watchfiles._rust_notify",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # trim Python stdlib we don't need
        "tkinter",
        "unittest",
        "pydoc_data",
        "xml.etree",
        "test",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="headcleaner",
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
    icon=str(ROOT / "assets" / "icon.ico") if (ROOT / "assets" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="headcleaner",
)
