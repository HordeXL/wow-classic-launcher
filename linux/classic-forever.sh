#!/usr/bin/env bash
# Classic Forever en Linux (Wine / Proton): aplica la clave del servidor al cliente.
#
#   ./classic-forever.sh                 # si WowB.exe ya esta abierto se engancha (pide sudo); si no, lo abre con wine
#   ./classic-forever.sh --launch        # fuerza abrirlo con wine
#   ./classic-forever.sh --update        # vuelve a descargar el parcheador
#   GAME_DIR="/otra/ruta/_classic_beta_" ./classic-forever.sh
#
# Deja esta ventana abierta mientras juegas: el parche vive en la memoria del juego y se reaplica si hace falta.
# El aviso "reason 24" / volver a la pantalla de login nada mas conectar = el juego no tenia la clave.
set -euo pipefail

GAME_DIR="${GAME_DIR:-/run/media/kuroro/Juegos/Wow/World of Warcraft/_classic_beta_}"
EXE="$GAME_DIR/WowB.exe"
DIR="$HOME/.local/share/classic-forever"
PY="$DIR/classic-forever-linux.py"
URL="https://raw.githubusercontent.com/defexnicolas/wow-classic-launcher/main/linux/classic-forever-linux.py"

mkdir -p "$DIR"
if [ ! -s "$PY" ] || [ -n "$(find "$PY" -mmin +30 2>/dev/null)" ] || [ "${1:-}" = "--update" ]; then
    echo "Descargando el parcheador..."
    curl -fsSL "$URL" -o "$PY.tmp" && mv "$PY.tmp" "$PY" || { [ -s "$PY" ] && echo "(sin red: uso la copia local)" || { echo "No pude descargar $URL"; exit 1; }; }
fi
[ -f "$EXE" ] || { echo "No encuentro $EXE (ajusta GAME_DIR)"; exit 1; }

# PID del cliente: Wine pone WowB.exe en la linea de comandos del proceso
PID="$(pgrep -f 'WowB\.exe' | head -1 || true)"

if [ "${1:-}" != "--launch" ] && [ -n "$PID" ]; then
    echo "WowB.exe ya esta abierto (pid $PID): me engancho. Linux exige sudo para leer su memoria."
    exec sudo python3 "$PY" --pid "$PID" --game-dir "$GAME_DIR"
fi

if [ "$(id -u)" = 0 ]; then
    echo "No ejecutes el script entero con sudo: Wine arrancaria como root (otro prefijo) y el juego falla con BC_ASSERT."
    echo "Abre el juego como tu usuario (o ejecuta este script sin sudo) y vuelve a lanzarlo: el sudo lo pide solo para engancharse."
    exit 1
fi
echo "Abriendo el juego con wine y vigilando la conexion..."
exec python3 "$PY" wine "$EXE"
