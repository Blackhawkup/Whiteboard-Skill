"""A photo of a hand holding a marker -> the hand the engine moves.

Clears a white background, finds the marker tip, extends the sleeve so the arm never ends inside the frame.
Expected picture: the marker tip toward the upper-left, the arm leaving through the bottom-right. See reference/prompts.md.
Writes <dir>/hand.png, hand.json (tip anchor and scale) and hand_check.jpg (red ring = where the pen writes)."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

ARM = np.array([0.58, 0.81])                 # the direction the arm leaves the picture
ARM = ARM / np.linalg.norm(ARM)
OUT_SCALE = 0.5
HAND_K = 0.74                                # hand px to board px at camera scale 1


def key_white(im):
    """Keep what is clearly hand, marker or sleeve: skin has colour, marker and sleeve are dark. A photo's soft shadow is neither."""
    a = np.asarray(im.convert('RGB')).astype(np.float32)
    edge = np.concatenate([a[:6].reshape(-1, 3), a[:, :6].reshape(-1, 3)])
    if np.median(edge.min(1)) < 170:
        raise SystemExit('The hand picture needs a plain white background. Regenerate it with the prompt in reference/prompts.md.')
    V = a.max(-1) / 255
    S = (a.max(-1) - a.min(-1)) / np.maximum(a.max(-1), 1)
    solid = (S > 0.11) | (V < 0.62)
    solid = ndi.gaussian_filter(ndi.binary_opening(solid, iterations=2).astype(np.float32), 2.5) > 0.5
    lab, n = ndi.label(solid)                                           # the hand is the biggest thing in the picture
    if n > 1:
        solid = lab == (int(np.argmax(np.bincount(lab.ravel())[1:])) + 1)
    # fill bright spots inside the hand (nail shine, marker sheen), but keep real gaps between the fingers open
    holes = ndi.binary_fill_holes(solid) & ~solid
    lab, n = ndi.label(holes)
    if n:
        areas = np.bincount(lab.ravel())
        small = areas < 1500
        small[0] = False
        solid = solid | small[lab]
    solid = ndi.binary_erosion(solid, iterations=1)
    alpha = np.clip(ndi.gaussian_filter(solid.astype(np.float32), 0.9) * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([a.astype(np.uint8), alpha]))


def fabric(a, solid, W, H, CW, CH):
    """Tile a patch of the real sleeve so the extension has the same texture, mirrored so it has no visible seams."""
    p = 170
    for y in range(H - p - 80, H // 2, -20):
        for x in range(W - p - 80, W // 2, -20):
            if solid[y:y + p, x:x + p].all():
                patch = a[y:y + p, x:x + p, :3]
                blur = np.dstack([ndi.gaussian_filter(patch[..., c], 22) for c in range(3)])
                patch = patch - blur + patch.mean((0, 1))               # keep the weave, drop the folds, so tiling shows no pattern
                row = np.concatenate([patch, patch[:, ::-1]], axis=1)
                tile = np.concatenate([row, row[::-1]], axis=0)
                ny, nx = CH // tile.shape[0] + 1, CW // tile.shape[1] + 1
                return np.tile(tile, (ny, nx, 1))[:CH, :CW]
    mu = np.median(a[..., :3][solid], 0)
    return np.ones((CH, CW, 3), np.float32) * mu


def extend_sleeve(im):
    """Continue the arm past the picture's bottom-right edge at a constant width, feathered into the photo."""
    W, H = im.size
    a = np.asarray(im).astype(np.float32)
    solid = a[..., 3] > 200
    if not solid[H - 8].any() and not solid[:, W - 8].any():
        print('NOTE: the arm ends inside the picture, so it cannot be extended. Regenerate with the arm leaving at the bottom-right.')
        return im
    rows = np.arange(max(0, H - 180), H - 6)
    lx = np.array([np.nonzero(solid[r])[0].min() if solid[r].any() else W for r in rows])
    kL = np.polyfit(rows, lx, 1)
    cols = np.arange(max(0, W - 160), W - 6)
    ty = np.array([np.nonzero(solid[:, c])[0].min() if solid[:, c].any() else H for c in cols])
    kR = np.polyfit(cols, ty, 1)
    P1 = np.array([np.polyval(kL, H - 70), H - 70.0])
    P2 = np.array([W - 70.0, np.polyval(kR, W - 70)])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    edge = np.minimum(H - 1 - yy, W - 1 - xx)
    EXT = 2600
    CW, CH = int(W + EXT * 0.75), int(H + EXT * 0.95)
    tex = fabric(a, solid, W, H, CW, CH)
    a[..., 3] = np.where(yy > H * 0.7, a[..., 3] * np.clip((edge - 6) / 54, 0, 1), a[..., 3])
    mask = Image.new('L', (CW, CH), 0)
    ImageDraw.Draw(mask).polygon([tuple(P1), tuple(P1 + ARM * EXT), tuple(P2 + ARM * EXT), tuple(P2), (W - 70, H - 70)], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.0))
    Y, X = np.mgrid[0:CH, 0:CW].astype(np.float32)
    perp = np.array([-ARM[1], ARM[0]])
    t = ((X - P1[0]) * perp[0] + (Y - P1[1]) * perp[1]) / (abs((P2 - P1) @ perp) + 1)
    shade = 0.84 + 0.2 * np.sin(np.clip(np.abs(t), 0, 1) * np.pi)       # a little roundness across the arm
    rgb = np.clip(tex * shade[..., None], 0, 255).astype(np.uint8)
    canvas = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    canvas.alpha_composite(Image.fromarray(np.dstack([rgb, np.asarray(mask)])))
    canvas.alpha_composite(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    return canvas


def make(src, out_dir, tip=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    keyed = key_white(Image.open(src).convert('RGB'))
    alpha = np.asarray(keyed)[..., 3] > 128
    ys, xs = np.nonzero(alpha)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    if tip:
        tx, ty = tip
    else:                                                               # the marker tip is the left-most solid point
        tx = int(xs.min())
        ty = int(np.median(ys[xs <= tx + 3]))
    # keep the picture's own bottom-right edge so the sleeve can be measured against it
    crop = keyed.crop((x0, y0, keyed.width, keyed.height))
    tx, ty = tx - x0, ty - y0
    full = extend_sleeve(crop)
    final = full.resize((int(full.width * OUT_SCALE), int(full.height * OUT_SCALE)), Image.LANCZOS)
    final.save(out_dir / 'hand.png')
    ax, ay = tx * OUT_SCALE, ty * OUT_SCALE
    (out_dir / 'hand.json').write_text(json.dumps({'ax': round(ax, 1), 'ay': round(ay, 1), 'k': HAND_K}))
    bg = Image.new('RGBA', final.size, (247, 243, 237, 255))
    bg.alpha_composite(final)
    w = min(final.width, 900)
    h = min(final.height, 1000)
    sheet = Image.new('RGB', (w + 60, h + 60), (247, 243, 237))         # a margin so the ring around the tip is never clipped
    sheet.paste(bg.crop((0, 0, w, h)).convert('RGB'), (60, 60))
    d = ImageDraw.Draw(sheet)
    d.ellipse([ax + 60 - 14, ay + 60 - 14, ax + 60 + 14, ay + 60 + 14], outline=(255, 0, 0), width=3)
    sheet.save(out_dir / 'hand_check.jpg', quality=88)
    print('hand -> %s  tip at (%.0f, %.0f). Look at hand_check.jpg: the red ring must sit on the marker tip and the background must be clean.' % (out_dir / 'hand.png', ax, ay))


if __name__ == '__main__':
    make(sys.argv[1], sys.argv[2])
