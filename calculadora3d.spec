# -*- mode: python ; coding: utf-8 -*-
# Build (no Windows): pyinstaller calculadora3d.spec
a = Analysis(
    ["calculadora3d/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[("calculadora3d/resources", "calculadora3d/resources")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Calculadora3D",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="calculadora3d/resources/icon.ico",
)
