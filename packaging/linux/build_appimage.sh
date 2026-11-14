#!/usr/bin/env bash
# Gera dist/Calculadora3D-<versão>-x86_64.AppImage. Roda no Linux, na raiz do
# repositório, com o ambiente do projeto instalado (pip install -e ".[dev]").
# Uso: bash packaging/linux/build_appimage.sh 0.2.0
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
if [ -z "$(find "$BUNDLE" -name 'libxcb-cursor.so.0*' -print -quit)" ]; then
    SYSLIB="$(ldconfig -p | awk '/libxcb-cursor\.so\.0 / {print $NF; exit}')"
    [ -n "$SYSLIB" ] || fail "libxcb-cursor.so.0 não está no sistema de build (apt install libxcb-cursor0)"
    echo "PyInstaller não incluiu libxcb-cursor; copiando $SYSLIB"
    cp -L "$SYSLIB" "$BUNDLE/_internal/libxcb-cursor.so.0"
fi
[ -n "$(find "$BUNDLE" -path '*calculadora3d/resources/icon.png' -print -quit)" ] \
    || fail "recursos do app (icon.png) não foram empacotados"

echo "== appimagetool"
if [ ! -x "$TOOL" ]; then
    curl -fsSL -o "$TOOL" "$TOOL_URL"
    chmod +x "$TOOL"
fi
rm -f "$OUT"
APPIMAGE_EXTRACT_AND_RUN=1 ARCH=x86_64 "$TOOL" "$APPDIR" "$OUT"
chmod +x "$OUT"

echo "== Teste de fumaça (15 s)"
DATA="$(mktemp -d)"
set +e
XDG_DATA_HOME="$DATA" APPIMAGE_EXTRACT_AND_RUN=1 \
    xvfb-run -a timeout 15 "./$OUT"
CODE=$?
set -e
[ "$CODE" -eq 124 ] || fail "o app fechou antes do tempo (código $CODE)"
[ -f "$DATA/calculadora3d/dados.db" ] || fail "o app abriu mas não criou o banco de dados"

echo "OK: $OUT"
