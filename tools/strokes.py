"""Line art -> a drawable: the exact final image plus the pen strokes that reveal it.

Writes  <out>_ink.png   ink with alpha (the exact final look)
        <out>_fill.png  colour layer with alpha (only if the art has colour)
        <out>.json      pen strokes: skeleton centre lines, ordered like a person draws, each with a mask width,
                        plus a zig-zag scribble that reveals the colour
Coordinates are canvas pixels (the png size, SCALE x board units). The engine draws the strokes into a mask up to the pen's
distance and composites the image through it, so the last frame is always the exact image: letters are never half-drawn.
"""
import json, math, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

SCALE = 1.5          # canvas resolution vs board units, sharp under camera pushes up to about 1.4
PAD = 24
NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def remove_small_objects(mask, size):
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    if not n:
        return mask
    areas = np.bincount(lab.ravel())
    keep = areas >= size
    keep[0] = False
    return keep[lab]


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load(path, out_w, flip=False):
    im = Image.open(path).convert('RGBA')
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    a = np.asarray(im).astype(np.float32) / 255.
    rgb = a[..., :3] * a[..., 3:4] + (1 - a[..., 3:4])                 # flatten onto white
    corners = np.concatenate([rgb[:12, :12].reshape(-1, 3), rgb[:12, -12:].reshape(-1, 3), rgb[-12:, :12].reshape(-1, 3), rgb[-12:, -12:].reshape(-1, 3)])
    white_bg = float(np.median(corners.min(1))) > 0.88
    V = rgb.max(-1)
    m = rgb.min(-1)
    S = np.where(V > 1e-3, (V - m) / np.maximum(V, 1e-3), 0)
    ink = np.clip((0.72 - V) / (0.72 - 0.28), 0, 1)                     # dark = ink
    fill = ((S > 0.30) & (V > 0.30)).astype(np.float32)                 # saturated = colour
    paper = m > 0.90                                                    # near white, connected to the border = background
    lab, _ = ndi.label(paper)
    border = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    border.discard(0)
    obj = (~np.isin(lab, list(border))).astype(np.float32)
    content = remove_small_objects((ink > 0.5) | (fill > 0.5), 60)
    ys, xs = np.nonzero(content)
    if not len(ys):
        raise SystemExit(f'{path}: nothing found on the image')
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    k = (out_w * SCALE - 2 * PAD) / (x1 - x0)
    W, H = int(round((x1 - x0) * k)) + 2 * PAD, int(round((y1 - y0) * k)) + 2 * PAD

    def rs(arr):
        img = Image.fromarray((np.clip(arr[y0:y1, x0:x1], 0, 1) * 255).astype(np.uint8)).resize((W - 2 * PAD, H - 2 * PAD), Image.LANCZOS)
        out = np.zeros((H, W), np.float32)
        out[PAD:H - PAD, PAD:W - PAD] = np.asarray(img) / 255.
        return out

    colour = np.dstack([rs(rgb[..., c]) for c in range(3)])
    return rs(ink), rs(fill), rs(obj), colour, white_bg


def trace_graph(skel):
    pts = set(zip(*np.nonzero(skel)))

    def nbrs(p):
        return [(p[0] + dy, p[1] + dx) for dy, dx in NB if (p[0] + dy, p[1] + dx) in pts]

    deg = {p: len(nbrs(p)) for p in pts}
    node = {p for p in pts if deg[p] != 2}
    edges, used = [], set()

    def walk(a, b):
        path = [a, b]
        while path[-1] not in node:
            nxt = [q for q in nbrs(path[-1]) if q != path[-2] and (min(path[-1], q), max(path[-1], q)) not in used]
            if not nxt:
                break
            nxt.sort(key=lambda q: abs(q[0] - path[-1][0]) + abs(q[1] - path[-1][1]))
            used.add((min(path[-1], nxt[0]), max(path[-1], nxt[0])))
            path.append(nxt[0])
            if path[-1] == path[0]:
                break
        return path

    for a in node:
        for b in nbrs(a):
            key = (min(a, b), max(a, b))
            if key in used:
                continue
            used.add(key)
            edges.append(walk(a, b))
    seen = {p for e in edges for p in e}                                # pure loops (no nodes)
    for p in list(pts):
        if p in seen or p in node:
            continue
        nb = nbrs(p)
        if not nb:
            continue
        used.add((min(p, nb[0]), max(p, nb[0])))
        node.add(p)
        e = walk(p, nb[0])
        node.discard(p)
        edges.append(e)
        seen.update(e)
    return edges


def direction(path, at_start, n=10):
    seg = path[:n] if at_start else path[-n:][::-1]
    if len(seg) < 2:
        return (0., 0.)
    dy, dx = seg[-1][0] - seg[0][0], seg[-1][1] - seg[0][1]
    L = math.hypot(dx, dy) or 1.
    return (dx / L, dy / L)


def merge(edges, dt):
    """Prune short spurs, then join edges through junctions along the straightest continuation."""
    for _ in range(3):
        ends = {}
        for i, e in enumerate(edges):
            for p in (e[0], e[-1]):
                ends.setdefault(p, []).append(i)
        keep = []
        for e in edges:
            free = [p for p in (e[0], e[-1]) if len(ends[p]) == 1]
            junction = [p for p in (e[0], e[-1]) if len(ends[p]) >= 3]
            if len(free) == 1 and junction and len(e) < 2.2 * max(dt[junction[0]], 1.0):
                continue
            keep.append(e)
        if len(keep) == len(edges):
            break
        edges = keep
    ends = {}
    for i, e in enumerate(edges):
        for p in (e[0], e[-1]):
            ends.setdefault(p, []).append(i)
    done, strokes = set(), []

    def extend(path):
        while True:
            tip = path[-1]
            cand = [j for j in ends.get(tip, []) if j not in done]
            if not cand:
                return path
            din = direction(path, at_start=False)
            best, bs = None, -2
            for j in cand:
                e = edges[j]
                dout = direction(e, at_start=(e[0] == tip))
                s = -(din[0] * dout[0] + din[1] * dout[1])              # 1 = straight on
                if s > bs:
                    best, bs = j, s
            if bs < 0.35:                                               # sharper than about 70 degrees: lift the pen
                return path
            done.add(best)
            e = edges[best]
            path = path + (e[1:] if e[0] == tip else e[::-1][1:])

    for i in sorted(range(len(edges)), key=lambda i: -len(edges[i])):
        if i in done:
            continue
        done.add(i)
        p = extend(list(edges[i]))
        p = extend(p[::-1])
        strokes.append(p)
    return strokes


def smooth(path, it=2):
    P = np.array(path, np.float32)[:, ::-1]                             # (x, y)
    closed = len(P) > 8 and np.hypot(*(P[0] - P[-1])) < 2.5
    for _ in range(it):
        if len(P) < 5:
            break
        Q = P.copy()
        Q[1:-1] = (P[:-2] + 2 * P[1:-1] + P[2:]) / 4
        if closed:
            Q[0] = Q[-1] = (P[1] + 2 * P[0] + P[-2]) / 4
        P = Q
    return P


def rdp(P, eps):
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    ab = b - a
    L = np.hypot(*ab)
    d = np.hypot(*(P - a).T) if L < 1e-6 else np.abs(ab[0] * (P[:, 1] - a[1]) - ab[1] * (P[:, 0] - a[0])) / L
    i = int(np.argmax(d))
    if d[i] > eps:
        return np.vstack([rdp(P[:i + 1], eps)[:-1], rdp(P[i:], eps)])
    return np.vstack([a, b])


def plen(P):
    return float(np.sum(np.hypot(*np.diff(P, axis=0).T))) if len(P) > 1 else 0.


def order_art(S, start='top'):
    """A sweep like a person drawing: start at the top (or right), then nearest-next, penalising jumps back up the page,
    with a pull toward long strokes so outlines come before details."""
    def top(s):
        return min(p[1] for p in s['pts'])

    if start == 'right':
        S = sorted(S, key=lambda s: -max(p[0] for p in s['pts']) - 0.15 * s['len'])
    elif start == 'left':
        S = sorted(S, key=lambda s: min(p[0] for p in s['pts']) - 0.15 * s['len'])
    else:
        S = sorted(S, key=lambda s: top(s) - 0.15 * s['len'])
    first = S.pop(0)
    a, b = first['pts'][0], first['pts'][-1]
    if (b[1] + 0.3 * b[0]) < (a[1] + 0.3 * a[0]):
        first['pts'] = first['pts'][::-1]
    out = [first]
    while S:
        pen = np.array(out[-1]['pts'][-1])
        best, bc, rev = 0, 1e18, False
        for i, s in enumerate(S):
            a, b = np.array(s['pts'][0]), np.array(s['pts'][-1])
            da, db = np.hypot(*(a - pen)), np.hypot(*(b - pen))
            back = max(0., pen[1] - top(s)) * 0.9
            c = (min(da, db) + back) / (1 + s['len']) ** 0.2
            if c < bc:
                best, bc, rev = i, c, db < da
        s = S.pop(best)
        if rev:
            s['pts'] = s['pts'][::-1]
        out.append(s)
    return out


def order_text(S):
    """Glyph by glyph, left to right; inside a glyph top-left first, then nearest."""
    groups = {}
    for s in S:
        groups.setdefault(s['comp'], []).append(s)
    out = []
    for g in sorted(groups, key=lambda g: min(min(p[0] for p in s['pts']) for s in groups[g])):
        G = groups[g]
        for s in G:
            a, b = s['pts'][0], s['pts'][-1]
            if (b[1] + 0.35 * b[0]) < (a[1] + 0.35 * a[0]):
                s['pts'] = s['pts'][::-1]
        G.sort(key=lambda s: s['pts'][0][1] + 0.35 * s['pts'][0][0])
        cur = [G.pop(0)]
        while G:
            pen = np.array(cur[-1]['pts'][-1])
            i = min(range(len(G)), key=lambda i: min(np.hypot(*(np.array(G[i]['pts'][0]) - pen)), np.hypot(*(np.array(G[i]['pts'][-1]) - pen))))
            s = G.pop(i)
            if np.hypot(*(np.array(s['pts'][-1]) - pen)) < np.hypot(*(np.array(s['pts'][0]) - pen)):
                s['pts'] = s['pts'][::-1]
            cur.append(s)
        out += cur
    return out


def scribble(fill, sw):
    """Boustrophedon zig-zag over the rows that hold colour, tilted like a marker colouring in."""
    ys, xs = np.nonzero(fill > 0.5)
    if not len(ys):
        return []
    pts, y, flip = [], ys.min() + sw * 0.35, False
    step = sw * 0.62
    while y <= ys.max() + 1:
        band = (ys >= y - step / 2) & (ys < y + step / 2)
        if band.any():
            a, b = xs[band].min() + sw * 0.25, xs[band].max() - sw * 0.25
            if b < a:
                a = b = (a + b) / 2
            seg = [(a, y), (b, y + step * 0.45)]
            pts += seg[::-1] if flip else seg
            flip = not flip
        y += step
    return [[round(float(x), 1), round(float(yy), 1)] for x, yy in pts]


def trace(src, out, w, ink_color='#111111', fill_color=None, text=False, flip=False, start='top', thick=0, mode='line', font_size=None):
    """mode 'line': ink and colour are recoloured to the palette. mode 'painted': the image keeps its own colours and shading."""
    ink, fill, obj, colour, white_bg = load(src, w, flip)
    H, W = ink.shape
    binary = remove_small_objects(ink > 0.5, 40)
    if not binary.any():
        raise SystemExit(f'{src}: no dark lines found. The pen follows dark outlines, so regenerate with bold black outlines.')
    sk = skeletonize(binary)
    if thick:                                                           # even marker weight: grow every line to the target
        half = float(np.median(ndi.distance_transform_edt(binary)[sk]))
        grow = thick * SCALE / 2 - half
        if grow > 0.3:
            ink = np.maximum(ink, np.clip(grow + 0.5 - ndi.distance_transform_edt(~binary), 0, 1))
            binary = ink > 0.5
    dt = ndi.distance_transform_edt(binary)
    raw = merge(trace_graph(sk), dt)
    lab, _ = ndi.label(binary, structure=np.ones((3, 3)))
    S = []
    for r in raw:
        if len(r) < 3 and (len(r) == 1 or dt[r[0]] < 2):
            continue
        rr = np.array(r)
        sw = 2 * float(dt[rr[:, 0], rr[:, 1]].max()) + 3.0
        P = rdp(smooth(r), 0.6)
        if len(P) < 2:
            P = np.vstack([P, P + 0.5])
        if np.hypot(*(P[0] - P[-1])) > 3:                               # open stroke: reach into square ends and corners
            for i, j in ((0, 1), (-1, -2)):
                d = P[i] - P[j]
                n = np.hypot(*d)
                if n > 1e-3:
                    P[i] = P[i] + d / n * 0.3 * (sw - 3) / 2
        L = plen(P)
        if L < 2 and sw < 6:
            continue
        S.append({'pts': [[round(float(x), 1), round(float(y), 1)] for x, y in P], 'w': round(sw, 1), 'len': L, 'comp': int(lab[r[len(r) // 2]])})
    S = order_text(S) if text else order_art(S, start)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = (colour * 255).astype(np.uint8) if mode == 'painted' else hexrgb(ink_color)
    rgba[..., 3] = (np.clip(ink, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(rgba).save(out + '_ink.png')
    meta = {'w': W, 'h': H, 'scale': SCALE, 'pad': PAD, 'board_w': w, 'kind': 'text' if text else 'art', 'strokes': [{'pts': s['pts'], 'w': s['w']} for s in S]}
    if font_size:
        meta['font_size'] = font_size
    f = None
    if mode == 'painted':
        f = np.clip(ndi.gaussian_filter(obj, 0.8), 0, 1)
    elif fill_color and fill.max() > 0.5:
        f = ndi.binary_dilation(fill > 0.5, iterations=3) & ~ndi.binary_dilation(~ndi.binary_fill_holes(binary | (fill > 0.5)), iterations=1)
        f = np.clip(ndi.gaussian_filter(f.astype(np.float32), 0.8), 0, 1)
    if f is not None and f.max() > 0.5:
        frgba = np.zeros((H, W, 4), np.uint8)
        frgba[..., :3] = (colour * 255).astype(np.uint8) if mode == 'painted' else hexrgb(fill_color)
        frgba[..., 3] = (f * 255).astype(np.uint8)
        Image.fromarray(frgba).save(out + '_fill.png')
        sw = max(30., min(120., W / 7))
        meta['fill'] = {'pts': scribble(f, sw), 'w': round(sw * 1.25, 1)}
    with open(out + '.json', 'w') as fh:
        json.dump(meta, fh)
    notes = []
    if not white_bg:
        notes.append('background is not white')
    if not text and fill_color and 'fill' not in meta and mode != 'painted':
        notes.append('no colour found, so nothing gets scribbled in')
    px = sum(s['len'] for s in S) / SCALE
    hops = 0.0                                                          # natural pen time, the same sum the engine does
    for s0, s1 in zip(S, S[1:]):
        d = math.hypot(s1['pts'][0][0] - s0['pts'][-1][0], s1['pts'][0][1] - s0['pts'][-1][1]) / SCALE
        hops += 0 if d < 12 else 0.006 + d / 9000
    pen = px / 2600 + hops
    if not text and pen > 2.8:
        notes.append(f'{pen:.1f} s of pen is over the 2.5 s budget: simplify the prompt (name exactly how many parts) or make it smaller')
    print('%-20s board %4d x %-4d  pen %.1f s  %4d strokes  %s%s' % (
        os.path.basename(out), W / SCALE, H / SCALE, pen, len(S), 'colour' if 'fill' in meta else 'no colour', ('  NOTE: ' + '; '.join(notes)) if notes else ''))
    return meta
