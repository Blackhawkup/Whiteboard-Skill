"""Seek-render the page in Chrome. Parallel workers each render one stretch of the film into a segment, then they are joined."""
import asyncio, base64, os, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw
from common import launch_args, run, die, load
from playwright.async_api import async_playwright


async def open_page(browser, html, W, H):
    errs = []
    ctx = await browser.new_context(viewport={'width': W, 'height': H})
    pg = await ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    await pg.goto(Path(html).resolve().as_uri())
    for _ in range(600):
        if errs:
            break
        if await pg.evaluate('window.__READY===true'):
            break
        await asyncio.sleep(0.1)
    if errs:
        die('The scene has an error:\n  ' + '\n  '.join(errs))
    cdp = await ctx.new_cdp_session(pg)
    return pg, cdp, errs


async def shot(cdp, W=None, H=None, scale=1.0):
    args = {'format': 'png', 'optimizeForSpeed': True, 'captureBeyondViewport': False}
    if scale != 1.0:
        args['clip'] = {'x': 0, 'y': 0, 'width': W, 'height': H, 'scale': scale}
    r = await cdp.send('Page.captureScreenshot', args)
    return base64.b64decode(r['data'])


async def _worker(browser, html, W, H, scale, fps, frames, seg, crf):
    pg, cdp, _ = await open_page(browser, html, W, H)
    ff = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'image2pipe', '-framerate', str(fps), '-c:v', 'png', '-i', '-', '-c:v', 'libx264', '-preset', 'fast', '-crf', str(crf),
                           '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', str(seg)],
                          stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in frames:
        await pg.evaluate('t => window.__seek(t)', i / fps)
        data = await shot(cdp, W, H, scale)
        ff.stdin.write(data)
    ff.stdin.close()
    ff.wait()


async def _video(film, out, fps, scale, crf, t0, t1, audio):
    html = film / 'build/page.html'
    cfg = load(film / 'film.json')
    fmt = cfg.get('format', '16:9')
    W, H = (1080, 1920) if fmt == '9:16' else (1080, 1080) if fmt == '1:1' else (1920, 1080)
    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_args())
        pg, _, _ = await open_page(browser, html, W, H)
        dur = await pg.evaluate('window.CLOCK.dur')
        await pg.context.close()
        a, b = round((t0 or 0) * fps), round((t1 or dur) * fps)
        n = max(1, min(int(os.environ.get('WB_WORKERS', '0')) or max(1, (os.cpu_count() or 4) // 2), 8))
        total = b - a
        print(f'rendering {total} frames at {fps} fps with {n} workers...', flush=True)
        with tempfile.TemporaryDirectory(dir=str(film / 'build')) as tmp:
            segs, jobs = [], []
            for k in range(n):
                seg = Path(tmp) / f'seg{k:02d}.mp4'
                segs.append(seg)
                jobs.append(_worker(browser, html, W, H, scale, fps, range(a + total * k // n, a + total * (k + 1) // n), seg, crf))
            await asyncio.gather(*jobs)
            await browser.close()
            lst = Path(tmp) / 'list.txt'
            lst.write_text(''.join(f"file '{Path(s).resolve().as_posix()}'\n" for s in segs))
            args = ['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst]
            if audio and Path(audio).exists():
                args += ['-ss', str(a / fps), '-t', str(total / fps), '-i', audio, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '256k', '-shortest']
            run(args + ['-c:v', 'copy', '-movflags', '+faststart', out])
    print(f'{out}  ({total / fps:.1f} s)')


def video(film, out, fps=60, scale=1.0, crf=14, t0=None, t1=None, audio=None):
    Path(out).parent.mkdir(exist_ok=True)
    asyncio.run(_video(film, out, fps, scale, crf, t0, t1, audio))


async def _grab(film, times):
    cfg = load(film / 'film.json')
    fmt = cfg.get('format', '16:9')
    W, H = (1080, 1920) if fmt == '9:16' else (1080, 1080) if fmt == '1:1' else (1920, 1080)
    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_args())
        pg, cdp, _ = await open_page(browser, film / 'build/page.html', W, H)
        dur = await pg.evaluate('window.CLOCK.dur')
        out = []
        for t in (times(dur) if callable(times) else times):
            await pg.evaluate('t => window.__seek(t)', t)
            out.append((t, await shot(cdp)))
        await browser.close()
    return out, W, H


def stills(film, times):
    d = film / 'out' / 'stills'
    d.mkdir(parents=True, exist_ok=True)
    grabbed, _, _ = asyncio.run(_grab(film, times))
    for t, png in grabbed:
        p = d / f't{t:06.2f}.png'
        p.write_bytes(png)
        print(p)


def sheet(film, every=None, t0=0, t1=None):
    """Contact sheets of the whole film, 12 frames per sheet, time stamped."""
    import io
    def times(dur):
        end = t1 or dur
        step = every or max(0.5, (end - t0) / 24)
        ts, t = [], t0
        while t < end - 1e-3:
            ts.append(round(t, 3))
            t += step
        ts.append(round(end - 0.02, 3))
        return ts
    grabbed, W, H = asyncio.run(_grab(film, times))
    d = film / 'out' / 'sheets'
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob('sheet-*.jpg'):
        f.unlink()
    tw = 620 if W >= H else 300
    th = int(tw * H / W)
    cols = 3 if W >= H else 6
    per = cols * (4 if W >= H else 2)
    for s in range(0, len(grabbed), per):
        chunk = grabbed[s:s + per]
        rows = (len(chunk) + cols - 1) // cols
        im = Image.new('RGB', (cols * (tw + 6), rows * (th + 6)), (40, 40, 40))
        for i, (t, png) in enumerate(chunk):
            f = Image.open(io.BytesIO(png)).convert('RGB').resize((tw, th), Image.LANCZOS)
            dr = ImageDraw.Draw(f)
            dr.rectangle([0, th - 22, 70, th], fill=(0, 0, 0))
            dr.text((5, th - 18), f'{t:.2f} s', fill=(255, 255, 255))
            im.paste(f, ((i % cols) * (tw + 6) + 3, (i // cols) * (th + 6) + 3))
        p = d / f'sheet-{s // per + 1:02d}.jpg'
        im.save(p, quality=86)
        print(p)
