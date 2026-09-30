#!/usr/bin/env python3
"""Genera linux/appimage/img/ a partir de src/img/ (las del launcher de Windows) al tamano exacto en pantalla:
Tk no reescala con suavizado. Requiere Pillow; solo hace falta al cambiar las imagenes (el resultado va en git)."""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', '..', 'src', 'img')
OUT = os.path.join(HERE, 'img')


def fit(name, box, out=None, dim=None):
    im = Image.open(os.path.join(SRC, name)).convert('RGBA')
    s = min(box[0] / im.width, box[1] / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    if dim is not None:
        a = im.getchannel('A').point(lambda v: int(v * dim))
        im.putalpha(a)
    im = im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG)
    im.save(os.path.join(OUT, out or name), optimize=True)


os.makedirs(OUT, exist_ok=True)
fit('panel.png', (946, 665))
fit('logo.png', (172, 161))
for n in ('nav_news', 'nav_patch', 'nav_settings'):
    fit(n + '.png', (112, 60))
    fit(n + '.png', (112, 60), n + '_off.png', 0.55)
for n in ('play_es', 'play_en', 'update'):
    fit(n + '.png', (262, 136))
    fit(n + '.png', (262, 136), n + '_off.png', 0.45)
fit('logo.png', (256, 256), 'icon.png')
fit('discord.png', (84, 62))
