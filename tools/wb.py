#!/usr/bin/env python3
"""wb: one command for the whiteboard-explainer skill. Workspace: $WHITEBOARD_HOME (default ~/WhiteboardFilms).

  wb setup [--install]            check everything; with --install, install whatever is missing
  wb example [one-key]            copy a bundled film to the workspace and render a proof of life (default chatbot-vs-agent, 16:9; one-key is 9:16)
  wb new <slug> [--format 16:9|9:16|1:1]   a new film folder
  wb prompts <film>               Flow prompts from drawings.json + the film's style (prompts.json, scenes to paste)
  wb intake <film> name=file ...  bring images in, with a labelled sheet to verify them (out/intake.jpg)
  wb hand <image> [--tip x,y]     make the hand from a picture; saved for every film
  wb art <film> [name ...]        trace drawings into pen strokes (colours from film.json)
  wb labels <film>                write labels.json in the film's font and trace them
  wb tts <film> --voice V [--style S]   record through Google AI Studio directly (when the Flow tools are not reachable)
  wb voice <film> <audio> [more] [--tempo X | --target SECONDS] [--words file.json] [--language en]   lock the take, time every word
  wb pace <film>                  re-apply film.json pacing without re-timing the words
  wb words <film>                 print the word clock
  wb check <film>                 the checks: one pen, pen speed, cut edges, small type, collisions, frame 0
  wb stills <film> --times 1,2.5  full frames in out/stills
  wb sheet <film> [--every S] [--from A --to B]    contact sheets in out/sheets
  wb preview <film>               quick half-size MP4 with sound (out/preview.mp4)
  wb make <film> [--force]        final MP4: check, mix, 60 fps render (out/<slug>.mp4)
<film> is a slug under the workspace, or a folder holding film.json."""
import argparse, json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FILMS, HAND_DIR, HOME, SKILL, die, film_dir, load, save, run


def need_deps():
    try:
        import numpy, PIL, scipy, skimage, playwright  # noqa
    except ImportError as e:
        die(f'Missing {e.name}. Run: wb setup --install')


def refresh_page(f):
    import build
    if not (f / 'build/clocks.js').exists():
        die('No word clock yet. Run wb voice first: the animation is timed to the locked voice.')
    build.page(f)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('help', '-h', '--help'):
        print(__doc__)
        return
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == 'setup':
        sys.argv = ['setup'] + rest
        import setup
        setup.main()
        return
    need_deps()
    ap = argparse.ArgumentParser(prog='wb ' + cmd)
    if cmd == 'example':
        ap.add_argument('name', nargs='?', default='chatbot-vs-agent'); a = ap.parse_args(rest)
        dest = FILMS / a.name
        if not (SKILL / 'examples' / a.name).exists():
            die('Examples: chatbot-vs-agent, one-key')
        if dest.exists():
            shutil.rmtree(dest)
        FILMS.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SKILL / 'examples' / a.name, dest)
        import voice, render, check
        voice.pace(dest)
        refresh_page(dest)
        ok = check.check(dest)
        render.sheet(dest)
        print('\nThe example works.' if ok else '\nThe example has errors: see above.')
        print(f'Look at {dest}/out/sheets. "wb make {a.name}" renders the full film.')
    elif cmd == 'new':
        ap.add_argument('slug'); ap.add_argument('--format', default='16:9', choices=['16:9', '9:16', '1:1'])
        a = ap.parse_args(rest)
        f = FILMS / a.slug
        if f.exists():
            die(f'{f} already exists')
        shutil.copytree(SKILL / 'templates/film', f)
        c = load(f / 'film.json'); c['slug'] = a.slug; c['format'] = a.format; save(f / 'film.json', c)
        for d in ('incoming', 'art', 'voice', 'out', 'build'):
            (f / d).mkdir(exist_ok=True)
        print(f)
    elif cmd == 'prompts':
        ap.add_argument('film'); a = ap.parse_args(rest)
        import prompts
        prompts.write(film_dir(a.film))
    elif cmd == 'intake':
        ap.add_argument('film'); ap.add_argument('pairs', nargs='+'); a = ap.parse_args(rest)
        import build
        f = film_dir(a.film); (f / 'incoming').mkdir(exist_ok=True)
        got = []
        for p in a.pairs:
            name, path = p.split('=', 1)
            src = Path(path).expanduser()
            if not src.exists():
                die(f'No such image: {src}')
            for old in (f / 'incoming').glob(name + '.*'):
                old.unlink()
            dst = f / 'incoming' / (name + src.suffix.lower())
            shutil.copy(src, dst)
            got.append((name, dst))
        print(f'{len(got)} images in. Look at {build.intake_sheet(f)}: each picture must match its name and the style before tracing.')
    elif cmd == 'hand':
        ap.add_argument('image'); ap.add_argument('--tip'); a = ap.parse_args(rest)
        import hand
        hand.make(a.image, HAND_DIR, tuple(int(x) for x in a.tip.split(',')) if a.tip else None)
    elif cmd == 'art':
        ap.add_argument('film'); ap.add_argument('names', nargs='*'); a = ap.parse_args(rest)
        import build
        build.art(film_dir(a.film), a.names or None)
    elif cmd == 'labels':
        ap.add_argument('film'); a = ap.parse_args(rest)
        import build
        build.labels(film_dir(a.film))
    elif cmd == 'tts':
        ap.add_argument('film'); ap.add_argument('--voice', required=True); ap.add_argument('--style'); ap.add_argument('--tempo', type=float); ap.add_argument('--target', type=float)
        ap.add_argument('--model', help='Gemini TTS model override (e.g. gemini-2.5-flash-preview-tts, gemini-2.0-flash)')
        ap.add_argument('--whisper-model', help='Whisper model (e.g. base, small, medium, large-v3)')
        a = ap.parse_args(rest)
        import voice
        f = film_dir(a.film)
        voice.lock(f, voice.tts(f, a.voice, a.style, model=a.model), a.tempo, a.target, whisper_model=a.whisper_model)
    elif cmd == 'voice':
        ap.add_argument('film'); ap.add_argument('audio', nargs='+'); ap.add_argument('--tempo', type=float); ap.add_argument('--target', type=float)
        ap.add_argument('--words'); ap.add_argument('--language')
        ap.add_argument('--whisper-model', help='Whisper model (e.g. base, small, medium, large-v3)')
        a = ap.parse_args(rest)
        import voice
        voice.lock(film_dir(a.film), [Path(x).expanduser() for x in a.audio], a.tempo, a.target, a.language, a.words, whisper_model=a.whisper_model)
    elif cmd == 'pace':
        ap.add_argument('film'); a = ap.parse_args(rest)
        import voice
        voice.pace(film_dir(a.film))
    elif cmd == 'words':
        ap.add_argument('film'); a = ap.parse_args(rest)
        f = film_dir(a.film); text = (f / 'build/clocks.js').read_text(encoding='utf-8')
        W = json.loads(text[len('window.WORDS='):text.index(';window.DUR')])
        print(' | '.join(f"{w['s']:.2f} {w['w']}" for w in W))
    elif cmd == 'check':
        ap.add_argument('film'); a = ap.parse_args(rest)
        import check
        f = film_dir(a.film); refresh_page(f)
        sys.exit(0 if check.check(f) else 1)
    elif cmd == 'stills':
        ap.add_argument('film'); ap.add_argument('--times', required=True); a = ap.parse_args(rest)
        import render
        f = film_dir(a.film); refresh_page(f)
        render.stills(f, [float(x) for x in a.times.split(',')])
    elif cmd == 'sheet':
        ap.add_argument('film'); ap.add_argument('--every', type=float); ap.add_argument('--from', dest='t0', type=float, default=0); ap.add_argument('--to', dest='t1', type=float)
        a = ap.parse_args(rest)
        import render
        f = film_dir(a.film); refresh_page(f)
        render.sheet(f, a.every, a.t0, a.t1)
    elif cmd in ('preview', 'make'):
        ap.add_argument('film'); ap.add_argument('--force', action='store_true'); a = ap.parse_args(rest)
        import asyncio, check, mix, render
        from playwright.async_api import async_playwright
        f = film_dir(a.film); refresh_page(f)
        if not check.check(f) and not a.force:
            die('Fix the errors above first (or pass --force).')
        async def pens():
            from common import launch_args
            async with async_playwright() as p:
                b = await p.chromium.launch(**launch_args())
                pg, _, _ = await render.open_page(b, f / 'build/page.html', 1920, 1080)
                out = await pg.evaluate('S.penLog()')
                await b.close()
                return out
        mix.mix(f, asyncio.run(pens()))
        slug = load(f / 'film.json').get('slug', f.name)
        if cmd == 'preview':
            render.video(f, f / 'out/preview.mp4', fps=30, scale=0.5, crf=23, audio=f / 'voice/mix.wav')
        else:
            render.video(f, f / 'out' / f'{slug}.mp4', fps=60, audio=f / 'voice/mix.wav')
            render.stills(f, [0])
    else:
        die(f'Unknown command "{cmd}". See: wb help')


if __name__ == '__main__':
    main()
