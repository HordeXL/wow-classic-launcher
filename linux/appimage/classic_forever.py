#!/usr/bin/env python3
"""Classic Forever para Linux: la ventana del launcher (Tkinter) sobre el parcheador de linux/classic-forever-linux.py.

Va dentro de ClassicForever-x86_64.AppImage (Python 3.12 con Tk, umu-launcher y este fichero; ver build.sh), pero
tambien se puede ejecutar suelto con `python3 classic_forever.py` si classic-forever-linux.py esta al lado o en ../.

Hace lo mismo que ClassicForever.exe: estado del reino, noticias y notas del parche (status.json), eleccion de la
carpeta _classic_beta_, y JUGAR: escribe WTF/BetaSuspendedTest.wtf, abre WowB.exe con Proton (umu-launcher, sin Steam)
o con el Wine del sistema, y pone la clave del servidor en la memoria del juego. Como el juego es hijo de este
proceso, Linux deja escribir en su memoria sin sudo.
"""
import importlib.util
import json
import mmap
import os
import queue
import re
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox

APP_VERSION = '1.2.1'   # igual que App.Version del launcher de Windows (build.sh lo comprueba)
RELEASES_URL = 'https://github.com/defexnicolas/wow-classic-launcher/releases/latest'
FEED_URL = 'https://raw.githubusercontent.com/defexnicolas/wow-classic-launcher/status/status.json'
LOGIN_PORT, WORLD_PORT = 1119, 8085
# Builds admitidos sin status.json (mismos que SupportedVersions de src/Patcher.cs); el servidor anuncia mas en clientBuilds.
SUPPORTED = ['1.60.1.69913', '1.60.1.69977', '1.60.1.70009', '1.60.1.70058']

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, 'img')
# 'classic-forever-launcher' y no 'classic-forever': en la maquina del servidor ese nombre ya es del portal
CONFIG_DIR = os.path.join(os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'), 'classic-forever-launcher')
DATA_DIR = os.path.join(os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share'), 'classic-forever-launcher')
SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.json')


def load_patcher():
    """El parcheador es linux/classic-forever-linux.py (tambien se usa solo, con Steam): se carga como modulo."""
    for p in (os.path.join(HERE, 'cfpatch.py'), os.path.join(HERE, 'classic-forever-linux.py'),
              os.path.join(HERE, '..', 'classic-forever-linux.py')):
        if os.path.isfile(p):
            spec = importlib.util.spec_from_file_location('cfpatch', p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit('No encuentro classic-forever-linux.py')


P = load_patcher()

# ----------------------------------------------------------------------------------------------------------- textos
T = {
    'status.checking':    ('COMPROBANDO…', 'CHECKING…'),
    'status.online':      ('EN LÍNEA', 'ONLINE'),
    'status.worlddown':   ('MUNDO NO DISPONIBLE', 'WORLD UNAVAILABLE'),
    'status.unreachable': ('NO LLEGO DESDE TU RED', 'UNREACHABLE FROM YOUR NETWORK'),
    'status.maintenance': ('MANTENIMIENTO', 'MAINTENANCE'),
    'status.offline':     ('FUERA DE LÍNEA', 'OFFLINE'),
    'status.noresponse':  ('El servidor no responde.', 'The server is not responding.'),
    'ui.discord':         ('Únete a nuestro Discord', 'Join our Discord'),
    'ui.subtitle':        ('Servidor para el cliente beta 1.60.1 · Linux', 'Server for the 1.60.1 beta client · Linux'),
    'ui.news':            ('NOVEDADES', 'NEWS'),
    'ui.patchnotes':      ('NOTAS DEL PARCHE', 'PATCH NOTES'),
    'ui.nonews':          ('Sin novedades.', 'No news.'),
    'ui.nopatchnotes':    ('Todavía no hay notas del parche publicadas.', 'No patch notes published yet.'),
    'ui.loading':         ('Cargando…', 'Loading…'),
    'ui.newsfail':        ('No se pudieron cargar las novedades.', "Couldn't load the news."),
    'ui.realm':           ('ESTADO DEL REINO', 'REALM STATUS'),
    'ui.links':           ('ENLACES', 'LINKS'),
    'ui.login':           ('Login', 'Login'),
    'ui.world':           ('Mundo', 'World'),
    'ui.ping':            ('Latencia al login: {0} ms', 'Login latency: {0} ms'),
    'ui.ingame':          ('EN JUEGO', 'IN GAME'),
    'ui.updatebtn':       ('ACTUALIZAR', 'UPDATE'),
    'ui.update':          ('Hay una versión nueva del launcher (v{0})', 'A new launcher version is available (v{0})'),
    'ui.download':        ('Descargar', 'Download'),
    'ui.mustupdate':      ('Este launcher ya no sirve: descarga la versión {0} o posterior con el botón ACTUALIZAR.',
                           'This launcher is no longer supported: download version {0} or later with the UPDATE button.'),
    'ui.ready':           ('Listo para jugar.', 'Ready to play.'),
    'ui.client':          ('Cliente {0}', 'Client {0}'),
    'nav.news':           ('NOTICIAS', 'NEWS'),
    'nav.patch':          ('NOTAS DEL PARCHE', 'PATCH NOTES'),
    'nav.settings':       ('OPCIONES', 'SETTINGS'),
    'set.folder':         ('CARPETA DEL JUEGO', 'GAME FOLDER'),
    'set.change':         ('Cambiar carpeta', 'Change folder'),
    'set.pick':           ('Elegir carpeta', 'Choose folder'),
    'set.log':            ('Ver registro', 'View log'),
    'set.runner':         ('CÓMO SE ABRE EL JUEGO', 'HOW THE GAME IS STARTED'),
    'set.proton':         ('Proton (recomendado, sin Steam)', 'Proton (recommended, no Steam)'),
    'set.wine':           ('Wine del sistema', 'System Wine'),
    'set.protonhint':     ('La primera vez descarga GE-Proton y el entorno de Steam (≈1,5 GB) en ~/.local/share/umu y ~/.local/share/Steam/compatibilitytools.d.',
                           'The first time it downloads GE-Proton and the Steam runtime (≈1.5 GB) into ~/.local/share/umu and ~/.local/share/Steam/compatibilitytools.d.'),
    'set.protonhave':     ('Usa tu Proton instalado ({0}). La primera vez solo descarga el entorno de Steam (≈300 MB) en ~/.local/share/umu.',
                           'Uses your installed Proton ({0}). The first time it only downloads the Steam runtime (≈300 MB) into ~/.local/share/umu.'),
    'set.protonver':      ('Versión de Proton:', 'Proton version:'),
    'set.protonauto':     ('Automático', 'Automatic'),
    'set.protondl':       ('Descargar el último GE-Proton', 'Download the latest GE-Proton'),
    'set.cache':          ('CACHÉ DEL JUEGO', 'GAME CACHE'),
    'set.cachebtn':       ('Borrar caché', 'Clear cache'),
    'set.menu':           ('Añadir al menú de aplicaciones', 'Add to applications menu'),
    'set.addons':         ('Instalar y actualizar solos los addons del servidor', 'Install and update the server addons automatically'),
    'addon.installed':    ('Addon {0} {1} instalado.', 'Addon {0} {1} installed.'),
    'addon.updated':      ('Addon {0} actualizado a {1}.', 'Addon {0} updated to {1}.'),
    'addon.failed':       ('No se pudo instalar {0}: {1}', "Couldn't install {0}: {1}"),
    'set.menudone':       ('Añadido al menú de aplicaciones.', 'Added to the applications menu.'),
    'set.menuno':         ('Solo funciona al abrirlo desde la AppImage.', 'Only works when started from the AppImage.'),
    'cache.confirm':      ('Se borrará esta carpeta:\n{0}\n\nEl juego la vuelve a crear al entrar. ¿Continuar?',
                           'This folder will be deleted:\n{0}\n\nThe game rebuilds it when you log in. Continue?'),
    'cache.running':      ('Cierra el juego antes de borrar la caché.', 'Close the game before clearing the cache.'),
    'cache.empty':        ('La caché ya está vacía.', 'The cache is already empty.'),
    'cache.done':         ('Caché borrada. Se volverá a crear al entrar al juego.', 'Cache cleared. It will be rebuilt when you log in.'),
    'dir.choose':         ('Elige la carpeta _classic_beta_ del juego (en Opciones).', "Choose the game's _classic_beta_ folder (in Settings)."),
    'dir.noexe':          ('No encuentro WowB.exe en esa carpeta (tiene que ser _classic_beta_).', 'WowB.exe is not in that folder (it must be _classic_beta_).'),
    'dir.badbuild':       ('Tu cliente es la build {0}; el servidor admite {1}.', 'Your client is build {0}; the server supports {1}.'),
    'dir.dialog':         ('Elige la carpeta _classic_beta_ (la que tiene WowB.exe)', 'Choose the _classic_beta_ folder (the one with WowB.exe)'),
    'run.nowine':         ('No encuentro «wine». Instálalo o usa Proton (Opciones).', "'wine' not found. Install it or use Proton (Settings)."),
    'run.noumu':          ('Falta umu-run: usa la AppImage o instala umu-launcher.', 'umu-run is missing: use the AppImage or install umu-launcher.'),
    'run.opening':        ('Abriendo el juego…', 'Opening the game…'),
    'run.firstruntime':   ('Preparando el entorno de Steam por primera vez (≈300 MB, puede tardar unos minutos)…',
                           'Setting up the Steam runtime for the first time (≈300 MB, may take a few minutes)…'),
    'run.firstproton':    ('Preparando Proton por primera vez (descarga ≈1,5 GB, puede tardar varios minutos)…',
                           'Setting up Proton for the first time (≈1.5 GB download, may take several minutes)…'),
    'run.nogame':         ('El juego no llegó a abrirse. Mira Logs/launcher-linux.log y Logs/proton.log.',
                           "The game didn't start. Check Logs/launcher-linux.log and Logs/proton.log."),
    'run.closed':         ('El juego se cerró. Hasta la próxima.', 'The game closed. See you next time.'),
    'run.waiting':        ('Esperando a que entres al reino…', 'Waiting for you to enter the realm…'),
    'run.ready':          ('LISTO. Si el primer intento de entrar falló, vuelve a entrar SIN cerrar el juego.',
                           'READY. If your first attempt to enter failed, enter again WITHOUT closing the game.'),
    'run.found':          ('Almacén de certificados encontrado: aplicando la clave del servidor…', 'Certificate store found: applying the server key…'),
    'run.nomem':          ('Linux no deja leer la memoria del juego. Mira Logs/launcher-linux.log.', "Linux won't let me read the game's memory. See Logs/launcher-linux.log."),
    'run.root':           ('No abras el launcher con sudo: Wine usaría el prefijo de root.', "Don't run the launcher with sudo: Wine would use root's prefix."),
    'app.already':        ('El launcher ya está abierto.', 'The launcher is already running.'),
    'exit.confirm':       ('El juego sigue abierto. Si cierras el launcher y el juego se reconecta, no se volverá a poner la clave.\n\n¿Salir de todas formas?',
                           "The game is still running. If you close the launcher and the game reconnects, the key won't be applied again.\n\nExit anyway?"),
}
LANGS = ('es', 'en')


class Lang:
    code = 'es'

    @classmethod
    def get(cls, key, *args):
        row = T.get(key)
        if not row:
            return key
        s = row[LANGS.index(cls.code)]
        return s.format(*args) if args else s


L = Lang.get


# ----------------------------------------------------------------------------------------------------------- ajustes
def load_settings():
    try:
        with open(SETTINGS_FILE, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(s):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(s, f, indent=2)
    except OSError:
        pass


# ----------------------------------------------------------------------------------------------------------- juego
def exe_version(exe):
    """Texto FileVersion del recurso de version del .exe (lo mismo que FileVersionInfo.FileVersion en Windows).
    El campo numerico VS_FIXEDFILEINFO de WowB.exe no sirve: Blizzard lo rellena como 160.1.7012.4."""
    key = 'FileVersion'.encode('utf-16-le') + b'\0\0'
    try:
        with open(exe, 'rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
            i = m.rfind(key)
            if i < 0:
                return None
            j = i + len(key)
            j += (-j) % 4                      # el valor empieza alineado a 4 bytes
            end = j
            while end < len(m) - 1 and m[end:end + 2] != b'\0\0':
                end += 2
            v = m[j:end].decode('utf-16-le', errors='replace').strip()
            return v or None
    except (OSError, ValueError):
        return None


def find_game_dir():
    """_classic_beta_ en los sitios habituales: prefijos de Wine, Lutris, Bottles, Heroic y Steam, y discos de Windows."""
    import glob
    h = os.path.expanduser('~')
    wow = ['drive_c/Program Files (x86)/World of Warcraft/_classic_beta_', 'drive_c/Program Files/World of Warcraft/_classic_beta_']
    prefixes = [h + '/.wine', h + '/Games/*', h + '/Games/*/*', h + '/Games/Heroic/Prefixes/*', h + '/Games/Heroic/Prefixes/default/*',
                h + '/.local/share/Steam/steamapps/compatdata/*/pfx', h + '/.steam/steam/steamapps/compatdata/*/pfx',
                h + '/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata/*/pfx',
                h + '/.local/share/bottles/bottles/*', h + '/.var/app/com.usebottles.bottles/data/bottles/bottles/*',
                h + '/.local/share/lutris/runners/wine/*']
    pats = [p + '/' + w for p in prefixes for w in wow]
    for root in ('/mnt/*', '/media/*/*', '/run/media/*/*', h + '/Games'):
        for rel in ('World of Warcraft/_classic_beta_', 'Program Files (x86)/World of Warcraft/_classic_beta_',
                    'Games/World of Warcraft/_classic_beta_', 'Juegos/World of Warcraft/_classic_beta_'):
            pats.append(root + '/' + rel)
    for pat in pats:
        for d in sorted(glob.glob(pat)):
            if os.path.isfile(os.path.join(d, P.EXE_NAME)):
                return d
    return None


def find_protons():
    """Proton ya instalados (carpetas con 'proton' y 'toolmanifest.vdf'): Steam (tambien Flatpak y otras bibliotecas),
    compatibilitytools.d (GE-Proton, proton-cachyos...), Lutris y Heroic. Lista de (nombre, ruta), la mejor primero."""
    import glob
    import re
    h = os.path.expanduser('~')
    steams = [h + '/.steam/root', h + '/.steam/steam', h + '/.local/share/Steam',
              h + '/.var/app/com.valvesoftware.Steam/data/Steam', h + '/.var/app/com.valvesoftware.Steam/.local/share/Steam']
    pats = [st + '/compatibilitytools.d/*' for st in steams]
    pats += ['/usr/share/steam/compatibilitytools.d/*', '/usr/local/share/steam/compatibilitytools.d/*',
             h + '/.local/share/lutris/runners/proton/*', h + '/.config/heroic/tools/proton/*',
             h + '/.var/app/com.heroicgameslauncher.hgl/config/heroic/tools/proton/*']
    libs = set(steams)
    for st in steams:   # otras bibliotecas de Steam (otros discos)
        try:
            with open(st + '/steamapps/libraryfolders.vdf', encoding='utf-8', errors='replace') as f:
                libs.update(re.findall(r'"path"\s+"([^"]+)"', f.read()))
        except OSError:
            pass
    pats += [lib + '/steamapps/common/Proton*' for lib in libs]
    seen, found = set(), []
    for pat in pats:
        for d in glob.glob(pat):
            real = os.path.realpath(d)
            if real in seen or not (os.path.isfile(os.path.join(d, 'proton')) and os.path.isfile(os.path.join(d, 'toolmanifest.vdf'))):
                continue
            seen.add(real)
            found.append((os.path.basename(d.rstrip('/')), d))

    def rank(item):
        name = item[0].lower()
        nums = tuple(int(x) for x in re.findall(r'\d+', name))
        kind = 0 if name.startswith('ge-proton') else 1 if 'cachyos' in name else 2 if 'experimental' in name else 3
        return (kind, tuple(-n for n in nums))
    return sorted(found, key=rank)


def umu_path():
    for p in (os.path.join(HERE, 'umu', 'umu-run'), shutil.which('umu-run')):
        if p and os.path.isfile(p):
            return p
    return None


def clean_env():
    """Entorno para el juego: sin las variables que la AppImage pone para su Python y su Tk."""
    env = dict(os.environ)
    for k in ('TCL_LIBRARY', 'TK_LIBRARY', 'TKPATH', 'PYTHONHOME', 'PYTHONPATH'):   # SSL_CERT_FILE se queda: umu descarga Proton
        env.pop(k, None)
    return env


def ssl_context():
    ctx = ssl.create_default_context()
    if os.environ.get('SSL_CERT_FILE'):
        return ctx
    for ca in ('/etc/ssl/certs/ca-certificates.crt', '/etc/pki/tls/certs/ca-bundle.crt', '/etc/ssl/cert.pem'):
        if os.path.isfile(ca):
            try:
                ctx.load_verify_locations(ca)
            except ssl.SSLError:
                pass
            break
    return ctx


# ----------------------------------------------------------------------------------------------------------- addons del servidor
# Como src/Addons.cs: status.json "addons": [{name, version, url, sha256}], solo desde las Releases de este repo, SHA-256
# comprobado, solo ficheros de addon dentro de su carpeta, y nunca con el juego abierto.
ADDON_URL_PREFIX = 'https://github.com/defexnicolas/wow-classic-launcher/releases/download/'
ADDON_EXT = ('.lua', '.toc', '.xml', '.png', '.tga', '.blp', '.md', '.txt')
ADDON_MAX = 8 * 1024 * 1024


def addon_valid(a):
    import re
    return (isinstance(a, dict) and re.match(r'^[A-Za-z0-9_]{1,64}$', str(a.get('name', ''))) is not None
            and re.match(r'^[0-9A-Za-z.\-]{1,20}$', str(a.get('version', ''))) is not None
            and str(a.get('url', '')).startswith(ADDON_URL_PREFIX) and '..' not in str(a.get('url'))
            and (not a.get('sha256') or re.match(r'^[0-9a-fA-F]{64}$', str(a['sha256'])) is not None))


def addon_version(game_dir, name):
    """'## Version:' del .toc instalado, o None si no esta."""
    import re
    toc = os.path.join(game_dir, 'Interface', 'AddOns', name, name + '.toc')
    try:
        with open(toc, encoding='utf-8', errors='replace') as f:
            for line in f:
                m = re.match(r'^##\s*Version:\s*(\S+)', line)
                if m:
                    return m.group(1)
        return '?'
    except OSError:
        return None


def addon_install_zip(game_dir, a, data, expected):
    import hashlib
    import io
    import zipfile
    if len(data) > ADDON_MAX:
        raise ValueError('zip > 8 MB')
    if hashlib.sha256(data).hexdigest().lower() != str(expected).lower():
        raise ValueError('SHA-256 no coincide')
    name = a['name']
    addons = os.path.join(game_dir, 'Interface', 'AddOns')
    os.makedirs(addons, exist_ok=True)
    staging = os.path.join(addons, '.' + name + '.new')
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging)
    try:
        real_staging = os.path.realpath(staging) + os.sep
        total = 0
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                rel = info.filename.replace('\\', '/')
                if rel.endswith('/'):
                    continue
                if not rel.startswith(name + '/'):
                    raise ValueError('fichero fuera de %s: %s' % (name, rel))
                if os.path.splitext(rel)[1].lower() not in ADDON_EXT:
                    raise ValueError('tipo de fichero no permitido: ' + rel)
                dest = os.path.realpath(os.path.join(staging, rel[len(name) + 1:]))
                if not dest.startswith(real_staging):
                    raise ValueError('ruta no permitida: ' + rel)
                total += info.file_size
                if total > ADDON_MAX * 4:
                    raise ValueError('addon demasiado grande')
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with z.open(info) as src, open(dest, 'wb') as out:
                    shutil.copyfileobj(src, out)
        if not os.path.isfile(os.path.join(staging, name + '.toc')):
            raise ValueError('falta %s.toc' % name)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    target = os.path.join(addons, name)
    old = os.path.join(addons, '.' + name + '.old')
    shutil.rmtree(old, ignore_errors=True)
    if os.path.isdir(target):
        os.rename(target, old)
    os.rename(staging, target)
    shutil.rmtree(old, ignore_errors=True)


def addon_sync(game_dir, addons):
    """Instala o actualiza; lista de (clave del mensaje, args, color)."""
    out = []
    for a in addons:
        have = addon_version(game_dir, a['name'])
        if have == a['version']:
            continue
        try:
            ua = {'User-Agent': 'ClassicForever-Linux/' + APP_VERSION}
            with urllib.request.urlopen(urllib.request.Request(a['url'], headers=ua), timeout=30, context=ssl_context()) as r:
                data = r.read(ADDON_MAX + 1)
            expected = a.get('sha256')
            if not expected:
                with urllib.request.urlopen(urllib.request.Request(a['url'] + '.sha256', headers=ua), timeout=15, context=ssl_context()) as r:
                    expected = r.read(200).decode().split()[0]
            addon_install_zip(game_dir, a, data, expected)
            out.append(('addon.installed' if have is None else 'addon.updated', (a['name'], a['version']), GREEN))
        except Exception as ex:
            out.append(('addon.failed', (a['name'], str(ex)), AMBER))
    return out


# ----------------------------------------------------------------------------------------------------------- estado
class Status:
    def __init__(self):
        self.login_up = self.world_up = False
        self.login_ms = -1
        self.feed_ok = self.feed_fresh = self.feed_login = self.maintenance = False
        self.root = {}
        self.news, self.patch_notes, self.links, self.client_builds, self.addons = [], [], [], [], []
        self.latest = self.min = self.discord = None
        self.launcher_url = RELEASES_URL


def probe(port):
    t0 = time.time()
    try:
        with socket.create_connection((P.PORTAL, port), timeout=3):
            return int((time.time() - t0) * 1000)
    except OSError:
        return -1


def fetch_status():
    s = Status()
    res = {}
    th = [threading.Thread(target=lambda p=p: res.__setitem__(p, probe(p))) for p in (LOGIN_PORT, WORLD_PORT)]
    for t in th:
        t.start()
    try:
        req = urllib.request.Request(f'{FEED_URL}?t={int(time.time() // 60)}', headers={'Cache-Control': 'no-cache',
                                                                                     'User-Agent': 'ClassicForever-Linux/' + APP_VERSION})
        with urllib.request.urlopen(req, timeout=10, context=ssl_context()) as r:
            root = json.loads(r.read().decode('utf-8'))
        if isinstance(root, dict):
            s.feed_ok, s.root = True, root
            import datetime
            try:
                upd = datetime.datetime.strptime(root.get('updated', ''), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
                s.feed_fresh = (datetime.datetime.now(datetime.timezone.utc) - upd).total_seconds() < 900
            except ValueError:
                pass
            realm = root.get('realm') or {}
            s.feed_login = s.feed_fresh and bool(realm.get('login'))
            s.maintenance = bool(root.get('maintenance'))
            s.news = [n for n in root.get('news') or [] if isinstance(n, dict)]
            s.patch_notes = [n for n in root.get('patchNotes') or [] if isinstance(n, dict)]
            s.links = [l for l in root.get('links') or [] if isinstance(l, dict) and str(l.get('url', '')).startswith('https://')]
            lau = root.get('launcher') or {}
            s.latest, s.min = lau.get('version'), lau.get('min')
            if re.match(r'^https://(discord\.gg|discord\.com/invite)/[A-Za-z0-9-]{2,32}$', str(root.get('discord', ''))):
                s.discord = root['discord']
            if str(lau.get('url', '')).startswith('https://'):
                s.launcher_url = lau['url']
            s.client_builds = [v for v in root.get('clientBuilds') or [] if isinstance(v, str) and re.match(r'^1\.60\.\d+\.\d{5}$', v)]
            s.addons = [a for a in root.get('addons') or [] if addon_valid(a)]
    except Exception:
        pass
    for t in th:
        t.join()
    s.login_ms = res.get(LOGIN_PORT, -1)
    s.login_up, s.world_up = s.login_ms >= 0, res.get(WORLD_PORT, -1) >= 0
    return s


def tr(entry, key):
    v = entry.get(f'{key}_{Lang.code}')
    return v if v else entry.get(key)


def newer(a, b):
    try:
        return a is not None and tuple(int(x) for x in a.split('.')) > tuple(int(x) for x in b.split('.'))
    except ValueError:
        return False


# ----------------------------------------------------------------------------------------------------------- ventana
GOLD, DIM, BODY, TEXT = '#E8C46A', '#A3967C', '#D6CCB4', '#E6D9B8'
GREEN, RED, AMBER, GREY = '#5CD67A', '#E05A4E', '#F0B23E', '#8A8A8A'
BG = '#0B0907'
OX, OY = 7, 50          # el marco (946x665) se pinta en (7,50); las coordenadas de abajo son del marco, como en el XAML


class App:
    def __init__(self):
        self.settings = load_settings()
        Lang.code = self.settings.get('lang') or ('es' if os.environ.get('LANG', '').startswith('es') else 'en')
        self.root = tk.Tk(className='ClassicForever')
        self.root.title('Classic Forever')
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.geometry('960x722')
        self.img = {n[:-4]: tk.PhotoImage(file=os.path.join(IMG_DIR, n)) for n in os.listdir(IMG_DIR) if n.endswith('.png')}
        try:
            self.root.iconphoto(True, self.img['icon'])
        except tk.TclError:
            pass
        fams = set(tkfont.families(self.root))
        sans = next((f for f in ('Noto Sans', 'Cantarell', 'Ubuntu', 'DejaVu Sans', 'Liberation Sans') if f in fams), 'TkDefaultFont')
        serif = next((f for f in ('Noto Serif', 'DejaVu Serif', 'Liberation Serif') if f in fams), sans)
        self.f = {k: tkfont.Font(family=fam, size=sz, weight=w) for k, (fam, sz, w) in {
            'h': (sans, 10, 'bold'), 'h2': (sans, 11, 'bold'), 'nav': (sans, 8, 'bold'), 'body': (sans, 10, 'normal'),
            'small': (sans, 9, 'normal'), 'title': (sans, 11, 'bold'), 'status': (sans, 12, 'bold'),
            'step': (sans, 12, 'normal'), 'lang': (sans, 10, 'bold'), 'over': (serif, 13, 'bold'), 'btn': (sans, 10, 'normal')}.items()}

        self.q = queue.Queue()
        self.status = None
        self.tab = 'news'
        self.game_running = False
        self.must_update = False
        self.client_ok = False
        self.client_version = None
        self.game_dir = None
        self.step_msg = ('ui.ready', (), TEXT)

        self.build()
        self.set_game_dir(self.settings.get('game_dir') if self.game_dir_valid(self.settings.get('game_dir')) else find_game_dir(), save=False)
        self.apply_language()
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.after(100, self.pump)
        self.refresh_status()
        if os.geteuid() == 0:
            self.step('run.root', color=RED)

    # ------------------------------------------------------------------------------------------------ construccion
    def build(self):
        c = self.c = tk.Canvas(self.root, width=960, height=722, bg=BG, highlightthickness=0)
        c.pack()
        c.create_image(OX, OY, image=self.img['panel'], anchor='nw')
        c.create_image(394 + 86, 2 + 80, image=self.img['logo'])
        # Discord: en el hueco de la barra superior a la derecha del logo (lo muestra status.json "discord")
        self.discord = c.create_image(OX + 618, OY + 61, image=self.img['discord'], state='hidden')
        self.clickable(self.discord, lambda e: self.status and self.status.discord and webbrowser.open(self.status.discord))
        def hover(on):
            if on:
                self._before_discord = self.step_msg
                self.step('ui.discord', color=GOLD)
            elif getattr(self, '_before_discord', None):
                self.step(self._before_discord[0], *self._before_discord[1], color=self._before_discord[2])
        c.tag_bind(self.discord, '<Enter>', lambda e: hover(True), add='+')
        c.tag_bind(self.discord, '<Leave>', lambda e: hover(False), add='+')
        # idioma
        self.lang_items = {}
        for i, code in enumerate(LANGS):
            t = c.create_text(880 + i * 34, 24, text=code.upper(), font=self.f['lang'], fill=DIM)
            self.lang_items[code] = t
            self.clickable(t, lambda e, cd=code: self.set_language(cd))
        # menu lateral
        self.nav = {}
        for i, key in enumerate(('news', 'patch', 'settings')):
            y = OY + 138 + i * 96
            im = c.create_image(OX + 35 + 75, y + 30, image=self.img[f'nav_{key}_off'])
            lb = c.create_text(OX + 35 + 75, y + 70, text='', font=self.f['nav'], fill=DIM)
            self.nav[key] = (im, lb)
            for it in (im, lb):
                self.clickable(it, lambda e, k=key: self.show_tab(k))
        # centro: cabecera + lista desplazable (lienzo propio con el trozo del marco de fondo)
        self.center_header = c.create_text(OX + 219, OY + 140, text='', font=self.f['h2'], fill=GOLD, anchor='nw')
        self.feed = tk.Canvas(self.root, width=433, height=290, bg='#1a0e0c', highlightthickness=0)
        self.feed_bg = self.crop_panel(219, 166, 433, 290)
        self.feed_bg_item = self.feed.create_image(0, 0, image=self.feed_bg, anchor='nw')
        self.feed_win = c.create_window(OX + 219, OY + 166, window=self.feed, anchor='nw')
        for ev in ('<Button-4>', '<Button-5>', '<MouseWheel>'):
            self.feed.bind(ev, self.on_wheel)
        # opciones
        self.settings_frame = self.build_settings()
        self.settings_win = c.create_window(OX + 219, OY + 166, window=self.settings_frame, anchor='nw', state='hidden')
        # derecha arriba: estado
        self.realm_header = c.create_text(OX + 700, OY + 140, text='', font=self.f['h'], fill=GOLD, anchor='nw')
        self.dot = c.create_oval(OX + 701, OY + 167, OX + 711, OY + 177, fill=GREY, outline='')
        self.status_text = c.create_text(OX + 720, OY + 172, text='', font=self.f['status'], fill=TEXT, anchor='w', width=170)
        self.detail_text = c.create_text(OX + 720, OY + 190, text='', font=self.f['small'], fill=BODY, anchor='nw', width=170)
        self.login_dot = c.create_oval(OX + 720, OY + 214, OX + 726, OY + 220, fill='#555', outline='')
        self.login_lbl = c.create_text(OX + 731, OY + 217, text='', font=self.f['small'], fill=DIM, anchor='w')
        self.world_dot = c.create_oval(OX + 785, OY + 214, OX + 791, OY + 220, fill='#555', outline='')
        self.world_lbl = c.create_text(OX + 796, OY + 217, text='', font=self.f['small'], fill=DIM, anchor='w')
        self.ping_text = c.create_text(OX + 720, OY + 236, text='', font=self.f['small'], fill=DIM, anchor='w')
        # derecha abajo: aviso, launcher nuevo y enlaces (se recolocan en render_right)
        self.right_items = []
        # barra inferior
        self.step_text = c.create_text(OX + 52, OY + 528, text='', font=self.f['step'], fill=TEXT, anchor='nw', width=560)
        self.subtitle = c.create_text(OX + 52, OY + 582, text='', font=self.f['small'], fill=DIM, anchor='nw')
        c.create_text(OX + 52, OY + 600, text=f'Launcher v{APP_VERSION} · Linux', font=self.f['small'], fill='#7A6E58', anchor='nw')
        self.play = c.create_image(OX + 640 + 131, OY + 513 + 68, image=self.img['play_es'])
        self.play_over_bg = c.create_rectangle(0, 0, 0, 0, fill='#120C06', outline='#8A6A3A', state='hidden')
        self.play_over = c.create_text(OX + 771, OY + 632, text='', font=self.f['over'], fill='#F6DA8C', state='hidden')
        for it in (self.play, self.play_over, self.play_over_bg):
            self.clickable(it, lambda e: self.on_play())

    def crop_panel(self, x, y, w, h):
        img = tk.PhotoImage(width=w, height=h)
        img.tk.call(img, 'copy', self.img['panel'], '-from', x, y, x + w, y + h, '-to', 0, 0)
        return img

    def clickable(self, item, fn, canvas=None):
        c = canvas or self.c
        c.tag_bind(item, '<Button-1>', fn)
        c.tag_bind(item, '<Enter>', lambda e: c.configure(cursor='hand2'))
        c.tag_bind(item, '<Leave>', lambda e: c.configure(cursor=''))

    def button(self, parent, cmd):
        return tk.Button(parent, command=cmd, font=self.f['btn'], fg='#D8C7A3', bg='#2A1D14', activebackground='#3A2A1A',
                         activeforeground='#FFF7D5', relief='flat', bd=0, highlightthickness=1, highlightbackground='#6B5232',
                         padx=12, pady=4, cursor='hand2', disabledforeground='#6B6050')

    def build_settings(self):
        bg = '#1d110d'
        fr = tk.Frame(self.root, bg=bg, width=433, height=290)
        fr.pack_propagate(False)
        lab = lambda: tk.Label(fr, bg=bg, fg=DIM, font=self.f['nav'], anchor='w')
        self.s_folder_lbl = lab(); self.s_folder_lbl.pack(fill='x')
        self.s_folder = tk.Label(fr, bg=bg, fg=BODY, font=self.f['small'], anchor='w', justify='left', wraplength=425)
        self.s_folder.pack(fill='x')
        self.s_client = tk.Label(fr, bg=bg, fg=DIM, font=self.f['small'], anchor='w'); self.s_client.pack(fill='x')
        row = tk.Frame(fr, bg=bg); row.pack(fill='x', pady=(4, 8))
        self.b_folder = self.button(row, self.pick_folder); self.b_folder.pack(side='left', padx=(0, 6))
        self.b_log = self.button(row, self.open_log); self.b_log.pack(side='left', padx=(0, 6))
        self.b_cache = self.button(row, self.clear_cache); self.b_cache.pack(side='left')
        self.s_runner_lbl = lab(); self.s_runner_lbl.pack(fill='x')
        self.runner = tk.StringVar(value=self.settings.get('runner', 'proton'))
        self.r_proton = tk.Radiobutton(fr, variable=self.runner, value='proton', command=self.runner_changed)
        self.r_wine = tk.Radiobutton(fr, variable=self.runner, value='wine', command=self.runner_changed)
        for r in (self.r_proton, self.r_wine):
            r.configure(bg=bg, fg=BODY, selectcolor='#2A1D14', activebackground=bg, activeforeground='#FFF7D5',
                        font=self.f['small'], anchor='w', highlightthickness=0, bd=0)
            r.pack(fill='x')
        prow = tk.Frame(fr, bg=bg); prow.pack(fill='x', padx=(20, 0), pady=(2, 0))
        self.s_protonver = tk.Label(prow, bg=bg, fg=DIM, font=self.f['small']); self.s_protonver.pack(side='left')
        self.protons = find_protons()
        self.proton_var = tk.StringVar()
        self.proton_menu = tk.OptionMenu(prow, self.proton_var, '')
        self.proton_menu.configure(bg='#2A1D14', fg=BODY, activebackground='#3A2A1A', activeforeground='#FFF7D5', relief='flat',
                                   bd=0, highlightthickness=1, highlightbackground='#6B5232', font=self.f['small'], width=30, anchor='w')
        self.proton_menu['menu'].configure(bg='#2A1D14', fg=BODY, activebackground='#3A2A1A', activeforeground='#FFF7D5', font=self.f['small'])
        self.proton_menu.pack(side='left', padx=(6, 0))
        self.s_proton_hint = tk.Label(fr, bg=bg, fg=DIM, font=self.f['small'], anchor='w', justify='left', wraplength=405)
        self.s_proton_hint.pack(fill='x', padx=(20, 0), pady=(2, 8))
        self.addons_var = tk.BooleanVar(value=self.settings.get('addons', True))
        self.c_addons = tk.Checkbutton(fr, variable=self.addons_var, command=self.addons_changed, bg=bg, fg=BODY,
                                       selectcolor='#2A1D14', activebackground=bg, activeforeground='#FFF7D5',
                                       font=self.f['small'], anchor='w', highlightthickness=0, bd=0)
        self.c_addons.pack(fill='x', pady=(0, 6))
        self.b_menu = self.button(fr, self.add_to_menu); self.b_menu.pack(anchor='w')
        return fr

    # ------------------------------------------------------------------------------------------------ idioma y pestanas
    def set_language(self, code):
        Lang.code = code
        self.settings['lang'] = code
        save_settings(self.settings)
        self.apply_language()

    def apply_language(self):
        c = self.c
        for code, it in self.lang_items.items():
            c.itemconfigure(it, fill=GOLD if code == Lang.code else DIM)
        for key, (im, lb) in self.nav.items():
            c.itemconfigure(lb, text=L('nav.' + key))
        c.itemconfigure(self.realm_header, text=L('ui.realm'))
        c.itemconfigure(self.login_lbl, text=L('ui.login'))
        c.itemconfigure(self.world_lbl, text=L('ui.world'))
        c.itemconfigure(self.subtitle, text=L('ui.subtitle'))
        self.s_folder_lbl.configure(text=L('set.folder'))
        self.s_runner_lbl.configure(text=L('set.runner'))
        self.r_proton.configure(text=L('set.proton'))
        self.r_wine.configure(text=L('set.wine'))
        self.s_protonver.configure(text=L('set.protonver'))
        self.fill_proton_menu()
        self.b_log.configure(text=L('set.log'))
        self.b_cache.configure(text=L('set.cachebtn'))
        self.b_menu.configure(text=L('set.menu'))
        self.c_addons.configure(text=L('set.addons'))
        self.b_folder.configure(text=L('set.change' if self.game_dir else 'set.pick'))
        self.s_client.configure(text=L('ui.client', self.client_version) + ('  ✓' if self.client_ok else '') if self.client_version else '')
        self.render_status()
        self.render_feed()
        self.paint_nav()
        self.paint_play()
        self.step(self.step_msg[0], *self.step_msg[1], color=self.step_msg[2])

    def show_tab(self, key):
        self.tab = key
        settings = key == 'settings'
        self.c.itemconfigure(self.feed_win, state='hidden' if settings else 'normal')
        self.c.itemconfigure(self.settings_win, state='normal' if settings else 'hidden')
        self.render_feed()
        self.paint_nav()

    def paint_nav(self):
        for key, (im, lb) in self.nav.items():
            on = key == self.tab
            self.c.itemconfigure(im, image=self.img[f'nav_{key}' + ('' if on else '_off')])
            self.c.itemconfigure(lb, fill=GOLD if on else '#9C9076')
        self.c.itemconfigure(self.center_header, text=L({'news': 'ui.news', 'patch': 'ui.patchnotes', 'settings': 'nav.settings'}[self.tab]))

    def paint_play(self):
        c = self.c
        if self.must_update:
            img, over = 'update', L('ui.updatebtn')
        elif self.game_running:
            img, over = 'play_' + Lang.code + '_off', L('ui.ingame')
        else:
            img, over = 'play_' + Lang.code, None
        c.itemconfigure(self.play, image=self.img[img])
        if over:
            c.itemconfigure(self.play_over, text=over, state='normal')
            x1, y1, x2, y2 = c.bbox(self.play_over)
            c.coords(self.play_over_bg, x1 - 10, y1 - 2, x2 + 10, y2 + 2)
            c.itemconfigure(self.play_over_bg, state='normal')
            c.tag_raise(self.play_over_bg); c.tag_raise(self.play_over)
        else:
            c.itemconfigure(self.play_over, state='hidden')
            c.itemconfigure(self.play_over_bg, state='hidden')

    def step(self, key, *args, color=TEXT):
        """Mensaje de la barra inferior; una clave que empieza por '!' es texto literal (errores del sistema)."""
        self.step_msg = (key, args, color)
        self.c.itemconfigure(self.step_text, text=key[1:] if key.startswith('!') else L(key, *args), fill=color)

    # ------------------------------------------------------------------------------------------------ estado y noticias
    def refresh_status(self):
        def work():
            s = fetch_status()
            self.q.put(('status', s))
        threading.Thread(target=work, daemon=True).start()
        self.root.after(60000, self.refresh_status)

    def on_status(self, s):
        if not s.feed_ok and self.status and self.status.feed_ok:   # fallo puntual del status.json: se conserva lo anterior
            old = self.status
            for k in ('feed_ok', 'root', 'news', 'patch_notes', 'links', 'latest', 'min', 'launcher_url', 'client_builds', 'addons', 'discord'):
                setattr(s, k, getattr(old, k))
        self.status = s
        if s.client_builds:
            for v in s.client_builds:
                if v not in SUPPORTED:
                    SUPPORTED.append(v)
        was = self.must_update
        self.must_update = newer(s.min, APP_VERSION)
        self.render_status()
        self.render_feed()
        self.paint_play()
        if self.must_update and not was and not self.game_running:
            self.step('ui.mustupdate', s.min, color=AMBER)
        elif not self.client_ok and not self.game_running and self.game_dir:
            self.set_game_dir(self.game_dir, save=False)   # la build se vuelve a comprobar con los clientBuilds recibidos
        self.sync_addons()

    def render_status(self):
        c, s = self.c, self.status
        if s is None:
            c.itemconfigure(self.status_text, text=L('status.checking'))
            return
        if s.login_up and s.world_up:
            col, key = GREEN, 'status.online'
        elif s.login_up:
            col, key = AMBER, 'status.worlddown'
        elif s.feed_login:
            col, key = AMBER, 'status.unreachable'
        elif s.maintenance:
            col, key = AMBER, 'status.maintenance'
        else:
            col, key = RED, 'status.offline'
        c.itemconfigure(self.dot, fill=col)
        c.itemconfigure(self.discord, state='normal' if s.discord else 'hidden')
        c.itemconfigure(self.status_text, text=L(key))
        c.itemconfigure(self.detail_text, text=L('status.noresponse') if not s.login_up and not s.world_up else '')
        c.itemconfigure(self.login_dot, fill=GREEN if s.login_up else RED)
        c.itemconfigure(self.world_dot, fill=GREEN if s.world_up else RED)
        c.itemconfigure(self.ping_text, text=L('ui.ping', s.login_ms) if s.login_ms >= 0 else '')
        # coloca login/mundo/latencia debajo del texto de estado (que puede ocupar dos lineas)
        y = (c.bbox(self.status_text)[3] if c.bbox(self.status_text) else OY + 180) + 4
        if c.itemcget(self.detail_text, 'text'):
            c.coords(self.detail_text, OX + 720, y)
            y = c.bbox(self.detail_text)[3] + 4
        for it, x in ((self.login_dot, 720), (self.world_dot, 785)):
            c.coords(it, OX + x, y + 5, OX + x + 6, y + 11)
        c.coords(self.login_lbl, OX + 731, y + 8)
        c.coords(self.world_lbl, OX + 796, y + 8)
        c.coords(self.ping_text, OX + 720, y + 28)
        self.render_right()

    def render_right(self):
        c, s = self.c, self.status
        for it in self.right_items:
            c.delete(it)
        self.right_items = []
        if s is None:
            return
        x, y, w = OX + 700, OY + 318, 192

        def text(t, font, fill, **kw):
            nonlocal y
            it = c.create_text(x, y, text=t, font=font, fill=fill, anchor='nw', width=w, **kw)
            self.right_items.append(it)
            y = c.bbox(it)[3] + 6
            return it

        msg = tr(s.root, 'message') if s.feed_ok else ''
        if msg:
            text(msg, self.f['body'], GOLD)
            y += 4
        if newer(s.latest, APP_VERSION) and not self.must_update:
            text(L('ui.update', s.latest), self.f['small'], TEXT)
            it = text(L('ui.download'), self.f['h'], GOLD)
            self.clickable(it, lambda e: webbrowser.open(s.launcher_url))
            y += 4
        if s.links and y < OY + 440:
            text(L('ui.links'), self.f['h'], GOLD)
            for l in s.links:
                if y > OY + 450:
                    break
                it = text('› ' + (tr(l, 'label') or l['url']), self.f['small'], BODY)
                url = l['url']
                self.clickable(it, lambda e, u=url: webbrowser.open(u))
                c.tag_bind(it, '<Enter>', lambda e, i=it: (c.itemconfigure(i, fill='#FFF1D2'), c.configure(cursor='hand2')), add='+')
                c.tag_bind(it, '<Leave>', lambda e, i=it: (c.itemconfigure(i, fill=BODY), c.configure(cursor='')), add='+')

    def render_feed(self):
        if self.tab == 'settings':
            return
        f = self.feed
        f.delete('item')
        s = self.status
        y = 0
        if s is None or not s.feed_ok:
            f.create_text(0, 0, text=L('ui.loading' if s is None else 'ui.newsfail'), font=self.f['body'], fill=DIM, anchor='nw', tags='item')
        else:
            items = s.patch_notes if self.tab == 'patch' else s.news
            if not items:
                f.create_text(0, 0, text=L('ui.nopatchnotes' if self.tab == 'patch' else 'ui.nonews'), font=self.f['body'],
                              fill=DIM, anchor='nw', width=420, tags='item')
            for n in items:
                if n.get('date'):
                    it = f.create_text(0, y, text=n['date'], font=self.f['small'], fill=DIM, anchor='nw', tags='item')
                    y = f.bbox(it)[3] + 1
                url = n.get('url') if str(n.get('url', '')).startswith('https://') else None
                it = f.create_text(0, y, text=tr(n, 'title') or '', font=self.f['title'], fill=GOLD if url else TEXT,
                                   anchor='nw', width=420, tags='item')
                if url:
                    self.clickable(it, lambda e, u=url: webbrowser.open(u), canvas=f)
                y = f.bbox(it)[3] + 2
                body = tr(n, 'text')
                if body:
                    it = f.create_text(0, y, text=body, font=self.f['body'], fill=BODY, anchor='nw', width=420, tags='item')
                    y = f.bbox(it)[3]
                y += 16
        f.configure(scrollregion=(0, 0, 433, max(y, 290)))
        f.yview_moveto(0)
        f.coords(self.feed_bg_item, 0, 0)
        self.feed_height = max(y, 290)
        self.paint_scrollbar()

    def paint_scrollbar(self):
        """Indicador dorado a la derecha de la lista cuando hay mas de lo que cabe (la rueda la desplaza)."""
        f = self.feed
        f.delete('sb')
        total = getattr(self, 'feed_height', 290)
        if total <= 290:
            return
        top = f.canvasy(0)
        h = max(24, 290 * 290 / total)
        y0 = top + (290 - h) * (top / (total - 290))
        f.create_rectangle(427, top, 432, top + 290, fill='#241510', outline='', tags='sb')
        f.create_rectangle(427, y0, 432, y0 + h, fill='#A88A4C', outline='', tags='sb')

    def on_wheel(self, e):
        d = -1 if (getattr(e, 'num', 0) == 4 or getattr(e, 'delta', 0) > 0) else 1
        self.feed.yview_scroll(d * 2, 'units')
        self.feed.coords(self.feed_bg_item, 0, self.feed.canvasy(0))   # el fondo no se desplaza
        self.paint_scrollbar()

    # ------------------------------------------------------------------------------------------------ carpeta y opciones
    @staticmethod
    def game_dir_valid(d):
        return bool(d) and os.path.isfile(os.path.join(d, P.EXE_NAME))

    def check_game_dir(self, d):
        """(clave del error, args) o None si se puede jugar; como Patcher.CheckGameDir."""
        self.client_version = None
        if not d:
            return ('dir.choose', ())
        exe = os.path.join(d, P.EXE_NAME)
        if not os.path.isfile(exe):
            return ('dir.noexe', ())
        self.client_version = exe_version(exe)
        if self.client_version not in SUPPORTED:
            return ('dir.badbuild', (self.client_version or '?', ', '.join(SUPPORTED)))
        return None

    def set_game_dir(self, d, save=True):
        self.game_dir = d
        self.addons_done_for = None
        err = self.check_game_dir(d)
        self.client_ok = err is None
        self.s_folder.configure(text=d or '—')
        self.s_client.configure(text=L('ui.client', self.client_version) + ('  ✓' if self.client_ok else '') if self.client_version else '')
        self.b_folder.configure(text=L('set.change' if d else 'set.pick'))
        self.b_cache.configure(state='normal' if self.client_ok and not self.game_running else 'disabled')
        if err:
            self.step(err[0], *err[1], color=AMBER)
        else:
            if self.must_update:
                self.step('ui.mustupdate', self.status.min, color=AMBER)
            else:
                self.step('ui.ready')
            if save:
                self.settings['game_dir'] = d
                save_settings(self.settings)

    def pick_folder(self):
        title = L('dir.dialog')
        start = self.game_dir or os.path.expanduser('~')
        d = None
        if shutil.which('zenity'):
            r = subprocess.run(['zenity', '--file-selection', '--directory', '--title', title, '--filename', start + '/'],
                               capture_output=True, text=True, env=clean_env())
            d = r.stdout.strip() if r.returncode == 0 else None
            if r.returncode not in (0, 1):
                d = filedialog.askdirectory(title=title, initialdir=start)
        elif shutil.which('kdialog'):
            r = subprocess.run(['kdialog', '--getexistingdirectory', start, '--title', title], capture_output=True, text=True, env=clean_env())
            d = r.stdout.strip() if r.returncode == 0 else None
        else:
            d = filedialog.askdirectory(title=title, initialdir=start)
        if not d:
            return
        sub = os.path.join(d, '_classic_beta_')
        if not self.game_dir_valid(d) and self.game_dir_valid(sub):   # eligio "World of Warcraft"
            d = sub
        self.set_game_dir(d)

    def open_log(self):
        if not self.game_dir:
            return
        log = os.path.join(self.game_dir, 'Logs', 'launcher-linux.log')
        if os.path.isfile(log):
            subprocess.Popen(['xdg-open', log], env=clean_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def proton_choice(self):
        """'auto' (el mejor instalado; si no hay, descargar), 'download' (ultimo GE-Proton) o la ruta de uno instalado."""
        return self.settings.get('proton') or 'auto'

    def proton_path(self):
        """Valor de PROTONPATH para umu: ruta de un Proton instalado o 'GE-Proton' (descarga el ultimo)."""
        ch = self.proton_choice()
        if ch == 'download':
            return 'GE-Proton'
        if ch != 'auto' and os.path.isfile(os.path.join(ch, 'proton')):
            return ch
        return self.protons[0][1] if self.protons else 'GE-Proton'

    def fill_proton_menu(self):
        opts = [('auto', L('set.protonauto') + (f' ({self.protons[0][0]})' if self.protons else ''))]
        opts += [(path, name) for name, path in self.protons]
        opts.append(('download', L('set.protondl')))
        ch = self.proton_choice()
        if ch not in [k for k, _ in opts]:
            ch = 'auto'
        menu = self.proton_menu['menu']
        menu.delete(0, 'end')
        for key, label in opts:
            menu.add_command(label=label, command=lambda k=key, l=label: self.set_proton(k, l))
        self.proton_var.set(dict(opts)[ch])
        pp = self.proton_path()
        self.s_proton_hint.configure(text=L('set.protonhint') if pp == 'GE-Proton' else L('set.protonhave', os.path.basename(pp)))

    def set_proton(self, key, label):
        self.settings['proton'] = key
        save_settings(self.settings)
        self.fill_proton_menu()

    def runner_changed(self):
        self.settings['runner'] = self.runner.get()
        save_settings(self.settings)

    def clear_cache(self):
        """Borra <carpeta del juego>/Cache: solo con WowB.exe en la carpeta, el juego cerrado y confirmacion."""
        if not self.client_ok or not self.game_dir_valid(self.game_dir):
            self.step('dir.choose', color=RED)
            return
        if self.game_running or P.find_clients():
            self.step('cache.running', color=AMBER)
            return
        cache = os.path.join(self.game_dir, 'Cache')
        if not os.path.isdir(cache):
            self.step('cache.empty')
            return
        if not messagebox.askyesno('Classic Forever', L('cache.confirm', cache), default='no'):
            return
        try:
            shutil.rmtree(cache)
            self.step('cache.done', color=GREEN)
        except OSError as ex:
            self.step('!' + str(ex), color=RED)

    def addons_changed(self):
        self.settings['addons'] = bool(self.addons_var.get())
        save_settings(self.settings)
        self.addons_done_for = None
        self.sync_addons()

    def sync_addons(self):
        """Addons del servidor: en un hilo, con el juego cerrado, una vez por carpeta del juego y sesion."""
        s = self.status
        if (getattr(self, 'addons_busy', False) or not self.settings.get('addons', True) or not self.client_ok
                or self.game_running or not self.game_dir or getattr(self, 'addons_done_for', None) == self.game_dir
                or s is None or not s.feed_ok or not s.addons or P.find_clients()):
            return
        self.addons_busy = True
        gd, addons = self.game_dir, list(s.addons)

        def work():
            try:
                for key, args, color in addon_sync(gd, addons):
                    self.q.put(('stepargs', key, args, color))
                self.addons_done_for = gd
            finally:
                self.addons_busy = False
        threading.Thread(target=work, daemon=True).start()

    def add_to_menu(self):
        appimage = os.environ.get('APPIMAGE')
        if not appimage:
            self.step('set.menuno', color=AMBER)
            return
        apps = os.path.join(os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share'), 'applications')
        icons = os.path.join(DATA_DIR, 'icon.png')
        os.makedirs(apps, exist_ok=True)
        os.makedirs(DATA_DIR, exist_ok=True)
        shutil.copyfile(os.path.join(IMG_DIR, 'icon.png'), icons)
        with open(os.path.join(apps, 'classic-forever.desktop'), 'w', encoding='utf-8') as f:
            f.write('[Desktop Entry]\nType=Application\nName=Classic Forever\nComment=Launcher del servidor Classic Forever\n'
                    f'Exec="{appimage}"\nIcon={icons}\nCategories=Game;\nTerminal=false\nStartupWMClass=ClassicForever\n')
        self.step('set.menudone', color=GREEN)

    # ------------------------------------------------------------------------------------------------ jugar
    def on_play(self):
        if self.must_update:
            webbrowser.open(self.status.launcher_url)
            return
        if self.game_running:
            return
        err = self.check_game_dir(self.game_dir)
        if err:
            self.step(err[0], *err[1], color=RED)
            if err[0] != 'dir.badbuild':
                self.show_tab('settings')
            return
        if os.geteuid() == 0:
            self.step('run.root', color=RED)
            return
        exe = os.path.join(self.game_dir, P.EXE_NAME)
        env = clean_env()
        if self.runner.get() == 'wine':
            wine = shutil.which('wine')
            if not wine:
                self.step('run.nowine', color=RED)
                return
            cmd = [wine, exe]
        else:
            umu = umu_path()
            if not umu:
                self.step('run.noumu', color=RED)
                return
            cmd = [sys.executable, umu, exe]
            env.setdefault('WINEPREFIX', os.path.join(DATA_DIR, 'prefix'))
            env.setdefault('GAMEID', 'umu-default')
            env.setdefault('PROTONPATH', self.proton_path())
            os.makedirs(env['WINEPREFIX'], exist_ok=True)
        cmd += ['-config', P.CONFIG_NAME]
        self.settings['game_dir'] = self.game_dir
        save_settings(self.settings)
        self.game_running = True
        self.paint_play()
        self.b_folder.configure(state='disabled')
        self.b_cache.configure(state='disabled')
        threading.Thread(target=self.run_game, args=(cmd, env), daemon=True).start()

    def run_game(self, cmd, env):
        """Hilo: abre el juego, lo busca entre los descendientes y le pone la clave (P.watch hasta que se cierra)."""
        q = self.q
        gd = self.game_dir
        os.makedirs(os.path.join(gd, 'Logs'), exist_ok=True)
        P.LOG_FILE = os.path.join(gd, 'Logs', 'launcher-linux.log')
        P.GAME_DIR = gd
        orig_say = P.say

        def say(text, color=''):   # el parcheador escribe su registro en espanol; la ventana muestra lo importante
            orig_say(text, color)
            low = text.lower()
            if low.startswith('listo'):
                q.put(('step', 'run.ready', GREEN))
            elif low.startswith('almacen de certificados'):
                q.put(('step', 'run.found', TEXT))
            elif low.startswith('esperando a que entres'):
                q.put(('step', 'run.waiting', DIM))
            elif 'no me deja leer la memoria' in low:
                q.put(('step', 'run.nomem', RED))
        P.say = say
        try:
            P.say('----- inicio (AppImage %s): %s%s' % (APP_VERSION, ' '.join(cmd),
                                                      ' | PROTONPATH=' + env['PROTONPATH'] if 'PROTONPATH' in env else ''), 'dim')
            P.ensure_config(gd)
            import glob
            first = 'umu' in ' '.join(cmd[:2]) and not glob.glob(os.path.expanduser('~/.local/share/umu/steamrt*/*_platform_*'))
            own = env.get('PROTONPATH', '').startswith('/')
            q.put(('step', ('run.firstruntime' if own else 'run.firstproton') if first else 'run.opening', TEXT))
            with open(os.path.join(gd, 'Logs', 'proton.log'), 'ab') as plog:
                child = subprocess.Popen(cmd, env=env, stdout=plog, stderr=subprocess.STDOUT, cwd=gd)
            pid, exited_at = None, None
            while pid is None:
                time.sleep(1)
                clients = P.find_clients(child.pid)
                if clients:
                    pid = clients[0]
                    break
                if child.poll() is not None:
                    exited_at = exited_at or time.time()
                    if time.time() - exited_at > 60:   # lanzadores que terminan antes de que aparezca el juego
                        break
            if pid is None:
                for line in P.describe_candidates():
                    P.say('  ' + line, 'dim')
                q.put(('step', 'run.nogame', RED))
            else:
                P.say(f'Juego en PID {pid}. Haz login y entra al reino.', 'cyan')
                q.put(('step', 'run.waiting', DIM))
                P.watch(pid)
                q.put(('step', 'run.closed', TEXT))
        except Exception as ex:   # nunca dejar la ventana en "EN JUEGO"
            P.say(f'Error: {ex!r}', 'red')
            q.put(('stepraw', str(ex), RED))
        finally:
            P.say = orig_say
            q.put(('ended', None))

    def pump(self):
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == 'status':
                    self.on_status(msg[1])
                elif kind == 'step':
                    self.step(msg[1], color=msg[2])
                elif kind == 'stepargs':
                    self.step(msg[1], *msg[2], color=msg[3])
                elif kind == 'stepraw':
                    self.step('!' + msg[1], color=msg[2])
                elif kind == 'ended':
                    self.game_running = False
                    self.paint_play()
                    self.b_folder.configure(state='normal')
                    self.b_cache.configure(state='normal' if self.client_ok else 'disabled')
                    self.root.deiconify()
                    self.sync_addons()
        except queue.Empty:
            pass
        self.root.after(150, self.pump)

    def on_close(self):
        if self.game_running and not messagebox.askyesno('Classic Forever', L('exit.confirm'), default='no'):
            return
        self.root.destroy()


def main():
    if '--version' in sys.argv:
        print(APP_VERSION)
        return 0
    # sin ventana (servidor sin grafica): el parcheador de siempre, por linea de ordenes
    if len(sys.argv) > 1 and sys.argv[1] in ('--patcher', '--cli'):
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        return P.main()
    # Una sola ventana, como el mutex del launcher de Windows: dos parcheadores sobre el mismo juego se pisarian.
    import fcntl
    os.makedirs(CONFIG_DIR, exist_ok=True)
    lock = open(os.path.join(os.environ.get('XDG_RUNTIME_DIR') or CONFIG_DIR, 'classic-forever-launcher.lock'), 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        settings = load_settings()
        Lang.code = settings.get('lang') or ('es' if os.environ.get('LANG', '').startswith('es') else 'en')
        r = tk.Tk(); r.withdraw()
        messagebox.showinfo('Classic Forever', L('app.already'))
        return 1
    App().root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
