"""Shared paths and helpers. Standard library only, so setup can import it before anything is installed."""
import json, os, platform, re, shutil, subprocess, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
HOME = Path(os.environ.get('WHITEBOARD_HOME', str(Path.home() / 'WhiteboardFilms'))).expanduser()
TOOLS = HOME / '.tools'
FILMS = HOME / 'films'
HAND_DIR = HOME / 'hand'
IS_WIN = platform.system() == 'Windows'
IS_MAC = platform.system() == 'Darwin'
VENV_PY = TOOLS / 'venv' / ('Scripts/python.exe' if IS_WIN else 'bin/python')


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def film_dir(name):
    p = Path(name).expanduser()
    if p.is_dir() and (p / 'film.json').exists():
        return p.resolve()
    p = FILMS / name
    if (p / 'film.json').exists():
        return p
    die(f"No film '{name}'. Give a slug under {FILMS} or a folder that holds film.json.")


def load(path, default=None):
    path = Path(path)
    if not path.exists():
        if default is not None:
            return default
        die(f'Missing {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=kw.pop('check', True), **kw)


def ffmpeg(*args, **kw):
    return run(['ffmpeg', '-y', '-v', 'error', *args], **kw)


def probe_duration(path):
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], capture_output=True, text=True)
    return float(r.stdout.strip())


def norm(word):
    """A word as the clock compares it: lower case, letters and digits only."""
    return re.sub(r'[\W_]+', '', word.lower())


def find_chrome():
    env = os.environ.get('CHROME_PATH')
    cands = [env] if env else []
    if IS_MAC:
        cands += ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium']
    elif IS_WIN:
        for base in (os.environ.get('PROGRAMFILES'), os.environ.get('PROGRAMFILES(X86)'), os.environ.get('LOCALAPPDATA')):
            if base:
                cands.append(os.path.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe'))
    else:
        cands += [shutil.which(n) for n in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser')]
    for c in cands:
        if c and os.path.exists(c):
            return c
    return None


def launch_args():
    """Keyword arguments for playwright's chromium.launch: the system Chrome when there is one, else playwright's own."""
    kw = {'args': ['--allow-file-access-from-files', '--disable-gpu-vsync', '--force-color-profile=srgb']}
    c = find_chrome()
    if c:
        kw['executable_path'] = c
    return kw
