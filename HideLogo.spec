# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_dir = Path(SPECPATH)
graphics_dir = project_dir / "graphics"
hiddenimports = collect_submodules("PIL")

a = Analysis(
    [str(project_dir / "ImageEditor.py")],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[(str(graphics_dir), "graphics")],
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name="HideLogo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(graphics_dir / "logo_cajero_3.ico"),
)
