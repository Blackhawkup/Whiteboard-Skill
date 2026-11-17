"""Check everything the skill needs. With --install, install whatever is missing. Safe to run again.
Standard library only, because it has to run before anything is installed.
Installs: system tools through the computer's package manager (Homebrew, apt, dnf, winget), a Python environment and packages in
<workspace>/.tools, Flow Studio (flow-mcp) in the home folder, and the Flow connection in every coding agent it finds."""
import json, os, re, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HOME, TOOLS, FILMS, VENV_PY, IS_MAC, IS_WIN, find_chrome

FLOW_REPO = 'https://github.com/GTAI-1/flow-mcp.git'
FLOW_DIR = Path(os.environ.get('FLOW_MCP_DIR', str(Path.home() / 'flow-mcp')))
PACKAGES = ['numpy', 'pillow', 'scipy', 'scikit-image', 'playwright', 'faster-whisper']
ok = bad = 0
todo_user = []


def good(m):
    global ok
    ok += 1
    print(f'  ok    {m}')


def need(m, fix=''):
    global bad
    bad += 1
    print(f'  NEED  {m}' + (f'\n        -> {fix}' if fix else ''))


def note(m):
    print(f'  note  {m}')


def sh(cmd, **kw):
    print('        $ ' + (cmd if isinstance(cmd, str) else ' '.join(map(str, cmd))))
    return subprocess.run(cmd, shell=isinstance(cmd, str), **kw).returncode == 0


def manager():
    if IS_WIN:
        return 'winget' if shutil.which('winget') else None
    if IS_MAC:
        return 'brew' if shutil.which('brew') or Path('/opt/homebrew/bin/brew').exists() else None
    for m in ('apt-get', 'dnf', 'pacman'):
        if shutil.which(m):
            return m
    return None


NAMES = {  # tool -> package per manager
    'ffmpeg': {'brew': 'ffmpeg', 'winget': 'Gyan.FFmpeg', 'apt-get': 'ffmpeg', 'dnf': 'ffmpeg', 'pacman': 'ffmpeg'},
    'node': {'brew': 'node', 'winget': 'OpenJS.NodeJS', 'apt-get': 'nodejs npm', 'dnf': 'nodejs npm', 'pacman': 'nodejs npm'},
    'git': {'brew': 'git', 'winget': 'Git.Git', 'apt-get': 'git', 'dnf': 'git', 'pacman': 'git'},
    'python': {'brew': 'python@3.12', 'winget': 'Python.Python.3.12', 'apt-get': 'python3 python3-venv', 'dnf': 'python3', 'pacman': 'python'},
}


def pkg_install(tool):
    m = manager()
    if not m:
        return False
    pk = NAMES[tool].get(m)
    if m == 'brew':
        brew = shutil.which('brew') or '/opt/homebrew/bin/brew'
        return sh([brew, 'install'] + pk.split())
    if m == 'winget':
        return sh(['winget', 'install', '-e', '--silent', '--accept-package-agreements', '--accept-source-agreements', '--id', pk])
    args = {'apt-get': ['install', '-y'], 'dnf': ['install', '-y'], 'pacman': ['-S', '--noconfirm']}[m]
    prefix = [] if os.geteuid() == 0 else ['sudo', '-n']
    return sh(prefix + [m] + args + pk.split())


def manager_help():
    if IS_MAC:
        return 'Homebrew is missing. Ask the user to paste this in a terminal (it needs their password): /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    if IS_WIN:
        return 'winget is missing. Ask the user to install "App Installer" from the Microsoft Store.'
    return 'If a password is needed, ask the user to run the install command themselves.'


def path_refresh():
    extra = ['/opt/homebrew/bin', '/usr/local/bin']
    os.environ['PATH'] = os.pathsep.join(extra + [os.environ.get('PATH', '')])


def tool(name, check, install):
    v = check()
    if v:
        good(v)
        return True
    if install:
        print(f'  ...   installing {name}')
        if pkg_install(name):
            path_refresh()
            v = check()
            if v:
                good(v + ' (just installed)')
                return True
        need(name, f'Automatic install failed. {manager_help()}')
    else:
        need(name, 'run: wb setup --install')
    return False


def out(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ''


def check_ffmpeg():
    return ('ffmpeg ' + out(['ffmpeg', '-version']).split()[2]) if shutil.which('ffmpeg') and shutil.which('ffprobe') else None


def check_node():
    if not shutil.which('node'):
        return None
    v = out(['node', '-v'])
    m = re.match(r'v(\d+)', v)
    return f'node {v}' if m and int(m.group(1)) >= 22 else None


def check_git():
    return 'git' if shutil.which('git') else None


def find_python():
    names = ['python3.12', 'python3.13', 'python3.11', 'python3.10', 'python3', 'python'] + (['py'] if IS_WIN else [])
    for n in names:
        p = shutil.which(n)
        if p and out([p, '-c', 'import sys; print(int((3,10) <= sys.version_info[:2] <= (3,13)))']) == '1':
            return p
    if IS_MAC:
        for n in ('3.12', '3.13', '3.11', '3.10'):
            p = f'/opt/homebrew/bin/python{n}'
            if Path(p).exists():
                return p
    return None


def check_python():
    p = find_python()
    return f'python 3.10-3.13 ({p})' if p else None


def venv_ok():
    if not VENV_PY.exists():
        return False
    code = 'import numpy, PIL, scipy, skimage, playwright, faster_whisper'
    return subprocess.run([str(VENV_PY), '-c', code], capture_output=True).returncode == 0


def setup_chrome(install):
    c = find_chrome()
    if c:
        good(f'chrome ({c})')
        return
    if install:
        print('  ...   installing Google Chrome')
        done = False
        if IS_MAC and manager() == 'brew':
            done = sh([shutil.which('brew') or '/opt/homebrew/bin/brew', 'install', '--cask', 'google-chrome'])
        elif IS_WIN and manager() == 'winget':
            done = sh(['winget', 'install', '-e', '--silent', '--accept-package-agreements', '--accept-source-agreements', '--id', 'Google.Chrome'])
        if done and find_chrome():
            good('chrome (just installed)')
            return
        if VENV_PY.exists() and sh([str(VENV_PY), '-m', 'playwright', 'install', 'chromium']):
            note('Google Chrome is still missing, so rendering uses playwright\'s Chromium. Flow Studio needs real Chrome: https://www.google.com/chrome')
            good('chromium for rendering')
            return
    need('Google Chrome', 'run: wb setup --install, or install it from https://www.google.com/chrome')


def setup_flow(install):
    index = FLOW_DIR / 'dist' / 'index.js'
    if index.exists():
        good(f'Flow Studio ({FLOW_DIR})')
    elif install:
        print('  ...   installing Flow Studio (flow-mcp)')
        if not (FLOW_DIR / 'package.json').exists() and not sh(['git', 'clone', '--depth', '1', FLOW_REPO, str(FLOW_DIR)]):
            need('Flow Studio', f'git clone {FLOW_REPO} {FLOW_DIR}')
            return None
        npm = shutil.which('npm') or 'npm'
        if sh([npm, 'install'], cwd=FLOW_DIR) and sh([npm, 'run', 'build'], cwd=FLOW_DIR) and index.exists():
            good('Flow Studio (just installed)')
        else:
            need('Flow Studio', f'cd {FLOW_DIR} && npm install && npm run build')
            return None
    else:
        need('Flow Studio (draws the pictures and records the voice)', 'run: wb setup --install')
        return None
    note(f'Google sign-in for Flow cannot be checked from here: flow_status is the authority. If it reports not signed in, run "npm run login" in {FLOW_DIR}.')
    if not (Path.home() / '.flow-mcp' / 'chrome-profile').exists():
        todo_user.append(f'Sign in to Google for Flow: run "npm run login" in {FLOW_DIR}. A Chrome window opens; the user signs in, opens a Flow project and leaves the window open.')
    return index


def connect_agents(index, install):
    """Register the Flow tools in every coding agent found on this computer."""
    node = shutil.which('node') or 'node'
    H = Path.home()
    any_new = False

    def json_entry(path, write):
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text() or '{}')
            except ValueError:
                note(f'{path} is not plain JSON, so add Flow by hand (see reference/setup.md)')
                return False
        if write(data, True):
            return False
        if install:
            if path.exists():
                shutil.copy(path, str(path) + '.before-whiteboard')
            write(data, False)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2) + '\n')
            return True
        return None

    def servers_key(key):
        def w(d, only_check):
            s = d.setdefault(key, {}) if not only_check else d.get(key, {})
            if 'flow' in s:
                return True
            if not only_check:
                s['flow'] = {'command': node, 'args': [str(index)]}
            return False
        return w

    def opencode(d, only_check):
        s = d.setdefault('mcp', {}) if not only_check else d.get('mcp', {})
        if 'flow' in s:
            return True
        if not only_check:
            s['flow'] = {'type': 'local', 'command': [node, str(index)], 'enabled': True}
        return False

    if shutil.which('claude'):
        if 'flow' in out(['claude', 'mcp', 'list']).lower():
            good('Flow connected to Claude Code')
        elif install and sh(['claude', 'mcp', 'add', '--scope', 'user', 'flow', '--', node, str(index)]):
            good('Flow connected to Claude Code (just now)'); any_new = True
        elif not install:
            need('Flow not connected to Claude Code', 'run: wb setup --install')
    codex_cfg = H / '.codex' / 'config.toml'
    if (H / '.codex').exists():
        text = codex_cfg.read_text() if codex_cfg.exists() else ''
        if '[mcp_servers.flow]' in text:
            good('Flow connected to Codex')
        elif install:
            codex_cfg.write_text(text.rstrip() + f'\n\n[mcp_servers.flow]\ncommand = {json.dumps(node)}\nargs = [{json.dumps(str(index))}]\n')
            good('Flow connected to Codex (just now)'); any_new = True
        else:
            need('Flow not connected to Codex', 'run: wb setup --install')
    for label, marker, path, writer in (
        ('Antigravity', H / '.gemini/antigravity', H / '.gemini/antigravity/mcp_config.json', servers_key('mcpServers')),
        ('OpenCode', H / '.config/opencode', H / '.config/opencode/opencode.json', opencode),
        ('Cursor', H / '.cursor', H / '.cursor/mcp.json', servers_key('mcpServers')),
        ('Gemini CLI', H / '.gemini', H / '.gemini/settings.json', servers_key('mcpServers')),
    ):
        if not marker.exists():
            continue
        r = json_entry(path, writer)
        if r is False:
            good(f'Flow connected to {label}')
        elif r is True:
            good(f'Flow connected to {label} (just now)'); any_new = True
        else:
            need(f'Flow not connected to {label}', 'run: wb setup --install')
    if any_new:
        todo_user.append('Restart your coding agent, or start a new chat, so it picks up the new Flow tools. Then continue from where you were.')


def main():
    install = '--install' in sys.argv
    path_refresh()
    HOME.mkdir(parents=True, exist_ok=True)
    FILMS.mkdir(parents=True, exist_ok=True)
    TOOLS.mkdir(parents=True, exist_ok=True)
    print(f'whiteboard-explainer setup (workspace: {HOME})')
    if install and not manager():
        note(manager_help())
    tool('python', check_python, install)
    tool('ffmpeg', check_ffmpeg, install)
    tool('node', check_node, install)
    tool('git', check_git, install)
    if venv_ok():
        good('python packages')
    elif install and find_python():
        print('  ...   creating the Python environment and installing packages (about 500 MB, a few minutes)')
        py = find_python()
        if not VENV_PY.exists():
            sh([py, '-m', 'venv', str(TOOLS / 'venv')])
        sh([str(VENV_PY), '-m', 'pip', 'install', '-q', '--upgrade', 'pip'])
        if sh([str(VENV_PY), '-m', 'pip', 'install', '-q'] + PACKAGES) and venv_ok():
            good('python packages (just installed)')
        else:
            need('python packages', f'{VENV_PY} -m pip install ' + ' '.join(PACKAGES))
    else:
        need('python packages', 'run: wb setup --install')
    setup_chrome(install)
    index = setup_flow(install) if shutil.which('node') else None
    if index:
        connect_agents(index, install)
    key = Path.home() / '.flow-mcp' / 'gemini-key'
    if key.exists() and key.read_text().strip():
        good('Google AI Studio key saved (free narration voices)')
    else:
        note('No Google AI Studio key yet. The voice step explains how to add one (reference/voice.md). A recording or a free local voice also works.')
    if IS_MAC:
        for protected in ('Desktop', 'Documents', 'Downloads'):
            if str(HOME).startswith(str(Path.home() / protected)):
                note(f'macOS protects ~/{protected}: Flow cannot read references there. Prefer the default ~/WhiteboardFilms.')
    print(f'\n{ok} ready, {bad} missing')
    if todo_user:
        print('\nThe user has to do this part:')
        for t in todo_user:
            print(f'  - {t}')
    sys.exit(0 if bad == 0 else 1)


if __name__ == '__main__':
    main()
