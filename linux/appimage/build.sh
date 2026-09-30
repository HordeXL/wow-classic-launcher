#!/bin/bash
# Monta dist/ClassicForever-x86_64.AppImage: Python 3.12 portable con Tk (python-appimage), umu-launcher (Proton sin
# Steam), la ventana (classic_forever.py) y el parcheador (../classic-forever-linux.py). Lo mismo corre en GitHub Actions.
# Requiere: bash, curl, sha256sum, tar, file. Todo lo descargado se comprueba por SHA-256 salvo appimagetool (herramienta
# de empaquetado, solo existe como "continuous"; su hash queda en el registro).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
work="${WORK:-$here/.build}"
out="$repo/dist"

PY_URL=https://github.com/niess/python-appimage/releases/download/python3.12/python3.12.14-cp312-cp312-manylinux2014_x86_64.AppImage
PY_SHA=fd6b81d037c786608c7407dd752a2b59381bf172b9c84bc8f0166d9f34cd53c4
UMU_URL=https://github.com/Open-Wine-Components/umu-launcher/releases/download/1.4.4/umu-launcher-1.4.4-zipapp.tar
UMU_SHA=eb590691841f7fad3fc3ad8fd5db4ccb87849fe7948e62b28ece7a4ee48cc851
TOOL_URL=https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage

# La version de la AppImage es la del launcher de Windows (se publican juntas con el mismo tag).
ver_py=$(sed -n "s/^APP_VERSION = '\([0-9.]*\)'.*/\1/p" "$here/classic_forever.py")
ver_cs=$(sed -n 's/.*public const string Version = "\([0-9.]*\)".*/\1/p' "$repo/src/App.cs")
[ "$ver_py" = "$ver_cs" ] || { echo "APP_VERSION ($ver_py) no coincide con App.Version ($ver_cs)"; exit 1; }

fetch() {   # url destino [sha256]
    if [ ! -f "$2" ]; then curl -fsSL -o "$2.part" "$1"; mv "$2.part" "$2"; fi
    if [ -n "${3:-}" ]; then echo "$3  $2" | sha256sum -c --quiet - || { rm -f "$2"; exit 1; }; fi
}

mkdir -p "$work" "$out"
cd "$work"
fetch "$PY_URL" python.AppImage "$PY_SHA"
fetch "$UMU_URL" umu.tar "$UMU_SHA"
fetch "$TOOL_URL" appimagetool.AppImage
sha256sum appimagetool.AppImage
chmod +x python.AppImage appimagetool.AppImage

rm -rf squashfs-root
./python.AppImage --appimage-extract >/dev/null
app=squashfs-root
# lo que no hace falta de Python (pip, IDLE, ensurepip). certifi se queda: opt/_internal/certs.pem apunta a el.
lib="$app/opt/python3.12/lib/python3.12"
rm -rf "$lib"/{idlelib,ensurepip,lib2to3,turtledemo} "$lib"/site-packages/pip "$lib"/site-packages/pip-* "$app"/usr/bin/pip* "$app"/opt/python3.12/bin/pip*
[ -f "$app/opt/_internal/certs.pem" ] || { echo "falta opt/_internal/certs.pem"; exit 1; }
rm -f "$app"/*.desktop "$app"/python.png "$app"/.DirIcon
rm -rf "$app"/usr/share/metainfo

dest="$app/opt/classic-forever"
mkdir -p "$dest/umu"
cp "$here/classic_forever.py" "$dest/"
cp "$repo/linux/classic-forever-linux.py" "$dest/cfpatch.py"
cp -r "$here/img" "$dest/"
tar -xf umu.tar -C "$dest/umu" --strip-components=1 umu/umu-run
chmod +x "$dest/umu/umu-run"

cp "$here/classic-forever.desktop" "$app/"
cp "$here/img/icon.png" "$app/classic-forever.png"
ln -s classic-forever.png "$app/.DirIcon"
rm -f "$app/AppRun"   # era un enlace a usr/bin/python3.12
cat > "$app/AppRun" <<'EOF'
#!/bin/bash
# Classic Forever (AppImage): Python y Tk de dentro de la imagen; la ventana es opt/classic-forever/classic_forever.py
if [ -z "${APPDIR:-}" ]; then
    APPDIR="$(dirname "$(readlink -f -- "$0")")"
    export APPDIR
fi
export TCL_LIBRARY="$APPDIR/usr/share/tcltk/tcl8.6"
export TK_LIBRARY="$APPDIR/usr/share/tcltk/tk8.6"
export TKPATH="$TK_LIBRARY"
export SSL_CERT_FILE="${SSL_CERT_FILE:-$APPDIR/opt/_internal/certs.pem}"
exec "$APPDIR/opt/python3.12/bin/python3.12" -s "$APPDIR/opt/classic-forever/classic_forever.py" "$@"
EOF
chmod +x "$app/AppRun"

ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 ./appimagetool.AppImage --no-appstream "$app" "$out/ClassicForever-x86_64.AppImage" >/dev/null
chmod +x "$out/ClassicForever-x86_64.AppImage"
ls -la "$out/ClassicForever-x86_64.AppImage"
sha256sum "$out/ClassicForever-x86_64.AppImage"
