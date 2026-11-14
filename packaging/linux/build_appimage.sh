#!/usr/bin/env bash
# Gera dist/Calculadora3D-<versão>-x86_64.AppImage. Roda no Linux, na raiz do
# repositório, com o ambiente do projeto instalado (pip install -e ".[dev]").
# Uso: bash packaging/linux/build_appimage.sh 0.2.0
# Depois: bash packaging/linux/smoke_appimage.sh dist/Calculadora3D-0.2.0-x86_64.AppImage
set -euo pipefail

VERSION="${1:?uso: build_appimage.sh <versão>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

APPDIR="build/AppDir"
BUNDLE="$APPDIR/usr/lib/Calculadora3D"
OUT="dist/Calculadora3D-$VERSION-x86_64.AppImage"
TOOL="build/appimagetool-x86_64.AppImage"
TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"

fail() { echo "ERRO: $*" >&2; exit 1; }

echo "== PyInstaller"
pyinstaller calculadora3d-linux.spec --noconfirm --clean

echo "== AppDir"
rm -rf "$APPDIR"
mkdir -p "$(dirname "$BUNDLE")"
cp -a dist/Calculadora3D "$BUNDLE"
install -m 755 packaging/linux/AppRun "$APPDIR/AppRun"
install -m 644 packaging/linux/calculadora3d.desktop "$APPDIR/calculadora3d.desktop"
install -m 644 calculadora3d/resources/icon.png "$APPDIR/calculadora3d.png"

echo "== Conferindo o conteúdo"
# Sem libxcb-cursor o Qt não abre janela em várias distros (Ubuntu, Mint).
# Ela vai junto, na mesma pasta do plugin do Qt que a usa (libQt6XcbQpa),
# que está no RUNPATH ($ORIGIN) dele — assim é achada sem LD_LIBRARY_PATH.
XCBQPA="$(find "$BUNDLE" -name 'libQt6XcbQpa.so*' -print -quit)"
[ -n "$XCBQPA" ] || fail "libQt6XcbQpa não foi empacotada (plugin xcb do Qt)"
QTLIB="$(dirname "$XCBQPA")"
CURSOR="$(find "$BUNDLE" -name 'libxcb-cursor.so.0*' -print -quit)"
if [ -z "$CURSOR" ]; then
    CURSOR="$(ldconfig -p | awk '/libxcb-cursor\.so\.0 / && !f {print $NF; f=1}')"
    [ -n "$CURSOR" ] || fail "libxcb-cursor.so.0 não está no sistema de build (apt install libxcb-cursor0)"
fi
if [ ! -e "$QTLIB/libxcb-cursor.so.0" ]; then
    echo "Copiando $CURSOR para $QTLIB"
    cp -L "$CURSOR" "$QTLIB/libxcb-cursor.so.0"
fi
[ -n "$(find "$BUNDLE" -path '*calculadora3d/resources/icon.png' -print -quit)" ]     || fail "recursos do app (icon.png) não foram empacotados"

echo "== appimagetool"
if [ ! -x "$TOOL" ]; then
    curl -fsSL -o "$TOOL" "$TOOL_URL"
    chmod +x "$TOOL"
fi
rm -f "$OUT"
APPIMAGE_EXTRACT_AND_RUN=1 ARCH=x86_64 "$TOOL" "$APPDIR" "$OUT"
chmod +x "$OUT"

echo "OK: $OUT"
