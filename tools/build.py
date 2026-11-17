"""Everything between the Flow images and a page the renderer can open:
trace drawings, trace labels, bundle them, write the page and the small data files it loads."""
import asyncio, colorsys, json, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from common import SKILL, HAND_DIR, die, load, launch_args
import strokes as ST

BUNDLED = {  # family -> (file, css weight range)
    'Geist': ('geist.woff2', '100 900'),
    'Inter': ('inter-var.woff2', '100 900'),
    'Archivo Black': ('archivo-black.woff2', '400'),
    'Instrument Serif': ('instrument-serif.woff2', '400'),
    'Caveat': ('caveat-700.woff2', '700'),
}


def resolve(cfg, c):
    """A colour may be a palette role (problem, solution, highlight, ink) or a hex value."""
    if c in (None, 'none', ''):
        return None
    pal = cfg.get('palette', {})
    return pal.get(c, c)


def art(film, only=None):
    cfg = load(film / 'film.json')
    (film / 'art').mkdir(exist_ok=True)
    missing = []
    for d in load(film / 'drawings.json'):
        name = d['name']
        if only and name not in only:
            continue
        src = next((p for p in sorted((film / 'incoming').glob(d.get('from', name) + '.*'))), None)   # "from": the same image again, at another size
        if not src:
            missing.append(name)
            continue
        ST.trace(str(src), str(film / 'art' / name), d.get('w', 400), ink_color=resolve(cfg, 'ink') or '#111111', fill_color=resolve(cfg, d.get('colour')),
                 flip=d.get('flip', False), start=d.get('start', 'top'), thick=d.get('thick', cfg.get('line_weight', 8.5)), mode=d.get('mode', cfg.get('art_mode', 'line')))
    if missing:
        print('Waiting on images for: ' + ', '.join(missing))


async def _labels(film, cfg, labels):
    from playwright.async_api import async_playwright
    build = film / 'build'
    build.mkdir(exist_ok=True)
    font = cfg.get('font', {'family': 'Geist'})
    if isinstance(font, str):
        font = {'family': font}
    fam = font['family']
    css, head = [], ''
    for f, (file, weights) in BUNDLED.items():
        shutil.copy(SKILL / 'engine' / 'fonts' / file, build / file)
        css.append(f"@font-face{{font-family:'{f}';src:url({file}) format('woff2');font-weight:{weights};font-display:block}}")
    if font.get('file'):
        p = Path(font['file']).expanduser()
        if not p.exists():
            die(f'Font file not found: {p}')
        shutil.copy(p, build / p.name)
        css.append(f"@font-face{{font-family:'{fam}';src:url({p.name});font-weight:100 900;font-display:block}}")
    text_all = ''.join(l['text'] for l in labels)
    if not font.get('file') and (fam not in BUNDLED or any(ord(c) > 0x7e for c in text_all)):
        # a Google font, or letters the bundled subset may lack
        head = f"<link rel='stylesheet' href='https://fonts.googleapis.com/css2?family={fam.replace(' ', '+')}:wght@400;500;600;700;800;900&display=block'>"
    spans = ''
    for l in labels:
        w = l.get('weight', 800)
        spans += f"<div><span id='{l['id']}' style=\"font:{l.get('style', 'normal')} {w} {l['size']}px '{l.get('family', fam)}', serif;letter-spacing:{l.get('tracking', '-0.01em')};line-height:1.3;padding:12px 16px;display:inline-block;white-space:nowrap\">{l['text']}</span></div>"
    page = build / '_labels.html'
    page.write_text(f"<!doctype html><html><head><meta charset='utf-8'>{head}<style>{''.join(css)}body{{margin:0;background:#fff;color:#000}}</style></head><body>{spans}</body></html>", encoding='utf-8')
    (film / 'art').mkdir(exist_ok=True)
    (film / 'incoming').mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(**launch_args())
        pg = await b.new_page(device_scale_factor=3, viewport={'width': 3000, 'height': 900})
        await pg.goto(page.resolve().as_uri(), wait_until='networkidle')
        await pg.evaluate('document.fonts.ready')
        fonts = sorted({f"{l.get('weight', 800)} 40px '{l.get('family', fam)}'" for l in labels})
        await pg.evaluate('fs => Promise.all(fs.map(f => document.fonts.load(f)))', fonts)
        real = await pg.evaluate("f => { const c=document.createElement('canvas').getContext('2d'); const w=(ff)=>{c.font=ff;return c.measureText('Handgloves 0123').width}; return f.map(x=>w(x+', monospace')!==w('40px monospace')) }", fonts)
        if not all(real):
            die(f"Font '{fam}' did not load. Use a bundled one ({', '.join(BUNDLED)}), a Google Fonts name (needs internet) or give a font file in film.json.")
        for l in labels:
            png = film / 'incoming' / f"txt_{l['id']}.png"
            await pg.locator('#' + l['id']).screenshot(path=str(png))
            w = await pg.evaluate("id => { const r=document.createRange(); r.selectNodeContents(document.getElementById(id)); return r.getBoundingClientRect().width }", l['id'])
            ST.trace(str(png), str(film / 'art' / l['id']), w + 2 * ST.PAD / ST.SCALE, ink_color=resolve(cfg, l.get('colour', 'ink')) or '#111111', text=True, font_size=l['size'])
        await b.close()


def labels(film):
    cfg = load(film / 'film.json')
    L = load(film / 'labels.json', [])
    if L:
        asyncio.run(_labels(film, cfg, L))


def _shade(hex_, dl):
    r, g, b = ST.hexrgb(hex_)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    l = max(0, min(1, l + dl))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return '#%02X%02X%02X' % (int(r * 255), int(g * 255), int(b * 255))


def hand_source():
    if (HAND_DIR / 'hand.png').exists():
        return HAND_DIR
    return SKILL / 'assets' / 'hand'


def page(film):
    """Write build/page.html and the data files. The final render needs no fonts: all type is traced by now."""
    cfg = load(film / 'film.json')
    build = film / 'build'
    build.mkdir(exist_ok=True)
    fmt = cfg.get('format', '16:9')
    W, H = (1080, 1920) if fmt == '9:16' else (1080, 1080) if fmt == '1:1' else (1920, 1080)
    board = cfg.get('board', '#F7F3ED')
    dark = sum(ST.hexrgb(board)) < 380
    metas = {}
    for j in sorted((film / 'art').glob('*.json')):
        metas[j.stem] = json.loads(j.read_text())
    (build / 'art.js').write_text('window.ART=' + json.dumps(metas, separators=(',', ':')) + ';\n')
    shutil.copy(SKILL / 'engine' / 'wb.js', build / 'wb.js')
    hs = hand_source()
    shutil.copy(hs / 'hand.png', build / 'hand.png')
    (build / 'film.js').write_text('window.FILM=' + json.dumps({'W': W, 'H': H, 'ink': cfg.get('palette', {}).get('ink', '#111111'), 'palette': cfg.get('palette', {}), 'pen_speed': cfg.get('pen_speed', 2600)}) +
                                   ';window.HAND_META=' + (hs / 'hand.json').read_text() + ';\n')
    if not (build / 'grain.png').exists():
        g = ndi.gaussian_filter(np.random.default_rng(7).normal(128, 40, (512, 512)), 0.7)
        Image.fromarray(((g - g.min()) / (g.max() - g.min()) * 255).astype(np.uint8)).save(build / 'grain.png')
    light, edge = _shade(board, 0.03), _shade(board, -0.035)
    (build / 'page.html').write_text(f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:{board}}}
#bg{{position:absolute;inset:0;background:radial-gradient(130% 120% at 22% 8%,{light} 0%,{board} 48%,{edge} 100%)}}
#grain{{position:absolute;inset:0;background-image:url(grain.png);opacity:{'.08' if dark else '.05'};mix-blend-mode:{'overlay' if dark else 'multiply'}}}
#cam{{position:absolute;left:0;top:0;transform-origin:0 0;will-change:transform}}
#board{{position:absolute;left:0;top:0}}
.item{{position:absolute}}
#hand{{position:absolute;left:0;top:0;z-index:10;pointer-events:none;will-change:transform;opacity:0}}
</style></head><body>
<div id="bg"></div><div id="grain"></div>
<div id="cam"><div id="board"></div></div>
<img id="hand" src="hand.png">
<script src="clocks.js"></script><script src="film.js"></script><script src="art.js"></script><script src="wb.js"></script>
<script src="../scene.js"></script>
<script>S.start();</script>
</body></html>
""", encoding='utf-8')
    return W, H


def intake_sheet(film):
    """Labelled picture of every image the film has so far, so wrong or swapped images are caught before tracing."""
    out = film / 'out'
    out.mkdir(exist_ok=True)
    tiles = []
    pairs = [(p.stem, p) for p in sorted((film / 'incoming').iterdir()) if not p.name.startswith(('txt_', '.'))]
    try:
        font = ImageFont.truetype('Arial.ttf', 26)
    except OSError:
        font = ImageFont.load_default()
    for name, path in pairs:
        im = Image.open(path).convert('RGB')
        im.thumbnail((440, 440))
        t = Image.new('RGB', (460, 500), 'white')
        t.paste(im, ((460 - im.width) // 2, 50))
        ImageDraw.Draw(t).text((10, 10), name, fill=(200, 0, 60), font=font)
        tiles.append(t)
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 470, rows * 510), (235, 235, 235))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 470 + 5, (i // cols) * 510 + 5))
    p = out / 'intake.jpg'
    sheet.save(p, quality=88)
    return p
