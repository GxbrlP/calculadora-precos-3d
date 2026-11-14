# -*- mode: python ; coding: utf-8 -*-
# Build (no Linux): pyinstaller calculadora3d-linux.spec
# Gera uma pasta (onedir) em dist/Calculadora3D, empacotada depois como
# AppImage por packaging/linux/build_appimage.sh.
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
    [],
    exclude_binaries=True,
    name="Calculadora3D",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Calculadora3D",
)
