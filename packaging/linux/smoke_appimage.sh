#!/usr/bin/env bash
# Abre o AppImage num X virtual (xvfb) por 15 s com uma pasta de dados vazia.
# Passa se o app ainda estiver aberto ao fim do tempo e tiver criado o banco.
# Uso: bash packaging/linux/smoke_appimage.sh dist/Calculadora3D-0.2.0-x86_64.AppImage
set -euo pipefail

APPIMAGE="$(readlink -f "${1:?uso: smoke_appimage.sh <arquivo.AppImage>}")"
fail() { echo "ERRO: $*" >&2; exit 1; }

DATA="$(mktemp -d)"
set +e
XDG_DATA_HOME="$DATA" APPIMAGE_EXTRACT_AND_RUN=1 \
    xvfb-run -a timeout -k 5 15 "$APPIMAGE"
CODE=$?
set -e
[ "$CODE" -eq 124 ] || fail "o app fechou antes do tempo (código $CODE)"
[ -f "$DATA/calculadora3d/dados.db" ] || fail "o app abriu mas não criou o banco de dados"
echo "OK: o app abriu e criou o banco"
