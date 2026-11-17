"""The checks that caught real defects while this was built. Errors block the final render."""
import asyncio, io
import numpy as np
from PIL import Image, ImageDraw
from common import load, launch_args, die
from playwright.async_api import async_playwright
from render import open_page

SPEED_WARN, SPEED_ERR = 3600, 6000       # board px per second
TEXT_WARN, TEXT_ERR = 40, 26             # on-screen font px while being written (phone rule)
EDGE = 6
HOLD_MIN = 2.5                           # seconds the last frame should rest
SAFE_916 = {'top': 220, 'bottom': 380, 'right': 140}   # Shorts, Reels and TikTok put their own buttons and captions here


async def _info(film):
    cfg = load(film / 'film.json')
    fmt = cfg.get('format', '16:9')
    W, H = (1080, 1920) if fmt == '9:16' else (1080, 1080) if fmt == '1:1' else (1920, 1080)
    async with async_playwright() as p:
        b = await p.chromium.launch(**launch_args())
        pg, cdp, errs = await open_page(b, film / 'build/page.html', W, H)
        info = await pg.evaluate('S.info()')
        grid = [round(k * 0.25, 3) for k in range(int(info['dur'] / 0.25))]
        info['grid'] = grid
        times = sorted({round(x, 3) for j in info['jobs'] for x in (j['t0'], (j['t0'] + j['t1']) / 2, j['t1'])} | {round(info['dur'] - .02, 3), 0.0} | set(grid) | {round(t + 0.1, 3) for t in grid})
        cams = await pg.evaluate('ts => ts.map(t => S.camAt(t))', times)
        samples = [round(j['t0'] + (j['t1'] - j['t0']) * k / 8, 3) for j in info['jobs'] if j['layer'] == 'ink' for k in range(9)]
        info['tips'] = dict(zip(samples, await pg.evaluate('ts => ts.map(t => S.penAt(t))', samples)))
        await pg.evaluate('t => __seek(t)', 0)
        f0 = await pg.screenshot(type='png')
        await b.close()
    info['cam'] = dict(zip(times, cams))
    info['frame0'] = f0
    return info


def box_on_screen(it, c, W, H):
    p = it.get('pad') or 0
    return (W / 2 + c['s'] * (it['x'] + p - c['x']), H / 2 + c['s'] * (it['y'] + p - c['y']),
            W / 2 + c['s'] * (it['x'] + it['w'] - p - c['x']), H / 2 + c['s'] * (it['y'] + it['h'] - p - c['y']))


def ink_mask(film, it, scale, x0, y0, shape):
    """Where this item's ink and colour land on a low-res picture of the board."""
    m = np.zeros(shape, bool)
    def stamp(alpha, x, y):
        h, w = alpha.shape
        X, Y = int((x - x0) * scale), int((y - y0) * scale)
        ys, xs = max(0, Y), max(0, X)
        ye, xe = min(shape[0], Y + h), min(shape[1], X + w)
        if ye > ys and xe > xs:
            m[ys:ye, xs:xe] |= alpha[ys - Y:ye - Y, xs - X:xe - X]
    if it['kind'] == 'mark':
        im = Image.new('L', (max(1, int(it['w'] * scale)), max(1, int(it['h'] * scale))), 0)
        d = ImageDraw.Draw(im)
        for st in it['src']:
            d.line([((p[0] - it['x']) * scale, (p[1] - it['y']) * scale) for p in st], fill=255, width=max(1, int(it['lw'] * scale)))
        stamp(np.asarray(im) > 128, it['x'], it['y'])
    else:
        for layer in ('ink', 'fill'):
            f = film / 'art' / f"{it['name']}_{layer}.png"
            if f.exists():
                im = Image.open(f).getchannel('A').resize((max(1, int(it['w'] * scale)), max(1, int(it['h'] * scale))), Image.BILINEAR)
                stamp(np.asarray(im) > 110, it['x'], it['y'])
    return m


def check(film):
    info = asyncio.run(_info(film))
    W, H, dur = info['W'], info['H'], info['dur']
    items = {i['id']: i for i in info['items']}
    errors, warns = [], []
    J = info['jobs']
    print('\n  time           item              px     px/s')
    prev = None
    for j in J:
        flag = ''
        if prev and j['t0'] < prev['t1'] - 1e-3:
            errors.append(f"{j['id']} ({j['t0']:.2f}s) starts before {prev['id']} ends ({prev['t1']:.2f}s). There is one pen.")
            flag = '  OVERLAP'
        if j['layer'] == 'ink' and j['v'] > SPEED_WARN:
            need = max(0.1, j['len'] / 3000 - j['len'] / j['v'])
            (errors if j['v'] > SPEED_ERR else warns).append(f"{j['id']} draws too fast ({j['v']:.0f} px/s). Needs about {need:.1f} s more: let it run on over the next words, start it earlier, add a pause at a sentence end, or simplify the drawing.")
            flag = '  FAST'
        print('  %6.2f-%6.2f %-14s %s %6.0f %7.0f%s' % (j['t0'], j['t1'], j['id'][:14], j['layer'][0], j['len'], j['v'], flag))
        prev = j
    for it in info['items']:
        for layer in it['layers']:
            if not any(j['id'] == it['id'] and j['layer'] == layer for j in J):
                errors.append(f"{it['id']} is on the board but never drawn ({layer}). Add S.draw, or remove it.")
    if J and J[-1]['t1'] > dur:
        errors.append(f"The last drawing ends at {J[-1]['t1']:.2f}s but the film ends at {dur:.2f}s.")
    if J and dur - J[-1]['t1'] < HOLD_MIN:
        warns.append(f"The final frame rests only {dur - J[-1]['t1']:.1f} s. Give it at least {HOLD_MIN} s: raise pacing tail in film.json, or finish the last drawing sooner.")
    # what the camera does to each item while it is drawn
    for j in J:
        if j['layer'] != 'ink':
            continue
        it = items[j['id']]
        for k in range(9):                                              # the pen must stay in frame the whole time it draws
            t = round(j['t0'] + (j['t1'] - j['t0']) * k / 8, 3)
            x, y = info['tips'][t]
            if x < -20 or y < -20 or x > W + 20 or y > H + 20:
                errors.append(f"{it['id']}: the pen is off-frame at {t:.2f}s (x {x:.0f}, y {y:.0f}). The camera has to arrive before the pen starts.")
                break
        c = info['cam'][round(j['t1'], 3)]                              # and the finished item must be whole
        b = box_on_screen(it, c, W, H)
        if not it.get('travel') and (b[0] < -EDGE or b[1] < -EDGE or b[2] > W + EDGE or b[3] > H + EDGE):
            errors.append(f"{it['id']} is cut by the frame edge when it finishes at {j['t1']:.2f}s (x {b[0]:.0f} to {b[2]:.0f}, y {b[1]:.0f} to {b[3]:.0f}). Move it or the camera.")
        if it['kind'] == 'text' and it['fontSize']:
            px = it['fontSize'] * c['s']
            if px < TEXT_ERR:
                errors.append(f"{it['id']} is written at {px:.0f} px on screen. Too small for a phone: make it bigger or push the camera in.")
            elif px < TEXT_WARN:
                warns.append(f"{it['id']} is written at only {px:.0f} px on screen. Aim for 40 or more.")
        if it['kind'] == 'art' and it['w'] * it['h'] * c['s'] ** 2 < 40000:    # by area, so long thin things like a key are judged fairly
            warns.append(f"{it['id']} is small on screen when drawn ({it['w'] * c['s']:.0f} x {it['h'] * c['s']:.0f} px). Prefer fewer, bigger drawings.")
        if it.get('traceW') and abs(it['w'] / it['traceW'] - 1) > 0.18:
            warns.append(f"{it['id']} shows at {it['w']:.0f} wide but was traced at {it['traceW']:.0f}, so its line weight will not match. Put the width in drawings.json and run wb art.")
    # the last frame
    c = info['cam'][round(dur - .02, 3)]
    for it in info['items']:
        b = box_on_screen(it, c, W, H)
        inside = b[0] >= 0 and b[1] >= 0 and b[2] <= W and b[3] <= H
        away = b[2] < 0 or b[0] > W or b[3] < 0 or b[1] > H
        if not inside and not away:
            errors.append(f"{it['id']} is cut by the frame edge in the final frame.")
        elif inside and min(b[0], b[1], W - b[2], H - b[3]) < 24:
            warns.append(f"{it['id']} sits within {min(b[0], b[1], W - b[2], H - b[3]):.0f} px of the edge in the final frame. Give it more margin.")
    # finished things cut by the frame while the camera holds: fine in passing, looks like a mistake when it stays
    done = {}
    for j in J:
        done[j['id']] = max(done.get(j['id'], 0), j['t1'])
    cut = {}
    for t in info['grid']:
        c, c2 = info['cam'][t], info['cam'][round(t + 0.1, 3)]
        if abs(c['x'] - c2['x']) * c['s'] > 8 or abs(c['y'] - c2['y']) * c['s'] > 8 or abs(c['s'] - c2['s']) > 0.015:
            continue
        for it in info['items']:
            if it['kind'] == 'mark' or done.get(it['id'], 1e9) > t:
                continue
            b = box_on_screen(it, c, W, H)
            if not (b[0] >= -EDGE and b[1] >= -EDGE and b[2] <= W + EDGE and b[3] <= H + EDGE) and not (b[2] < 0 or b[0] > W or b[3] < 0 or b[1] > H):
                cut.setdefault(it['id'], []).append(t)
    for k, ts in cut.items():
        if len(ts) >= 10:
            warns.append(f"{k} sits cut by the frame edge for {len(ts) * 0.25:.1f} s while the camera holds (around {ts[0]:.1f} to {ts[-1]:.1f} s). Frame it fully or move it fully out.")
    # the app's own buttons and captions on a vertical video
    if H > W:
        s = SAFE_916
        for it in info['items']:
            if it['kind'] != 'text':
                continue
            c = info['cam'][round(dur - .02, 3)]
            b = box_on_screen(it, c, W, H)
            hit = [n for n, bad in (('top', b[1] < s['top']), ('bottom', b[3] > H - s['bottom']), ('right', b[2] > W - s['right'] and b[3] > H * 0.45)) if bad]
            if hit and not (b[2] < 0 or b[0] > W or b[3] < 0 or b[1] > H):
                warns.append(f"{it['id']} is in the {' and '.join(hit)} zone of the final frame, where Shorts, Reels and TikTok put their own buttons and captions.")
    # ink collisions on the board
    if info['items']:
        x0 = min(i['x'] for i in info['items']); y0 = min(i['y'] for i in info['items'])
        x1 = max(i['x'] + i['w'] for i in info['items']); y1 = max(i['y'] + i['h'] for i in info['items'])
        sc = min(0.5, 2600 / max(x1 - x0, y1 - y0))
        shape = (int((y1 - y0) * sc) + 2, int((x1 - x0) * sc) + 2)
        masks = {i['id']: ink_mask(film, i, sc, x0, y0, shape) for i in info['items']}
        allowed = {frozenset(p) for p in info['allowed']}
        ids = list(masks)
        for a in range(len(ids)):
            for b_ in range(a + 1, len(ids)):
                ia, ib = items[ids[a]], items[ids[b_]]
                if frozenset((ids[a], ids[b_])) in allowed or 'text' not in (ia['kind'], ib['kind']):
                    continue
                n = int((masks[ids[a]] & masks[ids[b_]]).sum())
                if n > 6:
                    errors.append(f"{ids[a]} and {ids[b_]} collide on the board. Move one, or allow it with S.overlapOK if it is on purpose.")
    # frame 0
    a = np.asarray(Image.open(io.BytesIO(info['frame0'])).convert('L')).astype(float)
    if a.max() - a.min() > 60:
        errors.append('Frame 0 is not blank.')
    for m in load(film / 'voice/pacing-problems.json', []):
        warns.append('Pacing: ' + m)
    errors = list(dict.fromkeys(errors))
    warns = list(dict.fromkeys(warns))
    print()
    for w in warns:
        print('WARN  ' + w)
    for e in errors:
        print('ERROR ' + e)
    print(f"\n{len(info['items'])} items, {len(J)} pen jobs, film {dur:.2f} s: {len(errors)} errors, {len(warns)} warnings")
    return not errors
