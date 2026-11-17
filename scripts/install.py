#!/usr/bin/env python3
"""Make this skill available globally to every coding agent on this computer.
Run it with any Python 3, from wherever the folder was unzipped:   python3 scripts/install.py
Copies the folder into the global skills folder of each agent it finds. Options:
  --dir PATH   also install into PATH/whiteboard-explainer (for an agent that is not in the list)
  --all        create the folders for every agent, even ones not found yet"""
import argparse, shutil
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
NAME = 'whiteboard-explainer'
H = Path.home()
TARGETS = [  # agent, the folder that shows it is installed, its global skills folder
    ('Claude Code', H / '.claude', H / '.claude/skills'),
    ('Codex', H / '.codex', H / '.codex/skills'),
    ('Codex and other agents (open standard)', H / '.agents', H / '.agents/skills'),
    ('OpenCode', H / '.config/opencode', H / '.config/opencode/skills'),
    ('Antigravity', H / '.gemini/antigravity', H / '.gemini/antigravity/skills'),
    ('Gemini Config Skills', H / '.gemini/config', H / '.gemini/config/skills'),
    ('Gemini CLI', H / '.gemini', H / '.gemini/skills'),
    ('Cursor', H / '.cursor', H / '.cursor/skills'),
    ('Windsurf', H / '.codeium/windsurf', H / '.codeium/windsurf/skills'),
]


def copy_to(folder):
    dest = folder / NAME
    if dest.resolve() == SRC:
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SRC, dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '.DS_Store', 'build', 'out', 'models', '*.incomplete', '.locks'))
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', action='append', default=[])
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    done = 0
    for agent, marker, folder in TARGETS:
        if marker.exists() or a.all:
            print(f'  {agent}: {copy_to(folder)}')
            done += 1
    for d in a.dir:
        print(f'  {d}: {copy_to(Path(d).expanduser())}')
        done += 1
    if not done:
        print(f'  No known agent found, so it went to {copy_to(H / ".agents/skills")}.')
        print('  If your agent reads skills from another folder, run this again with --dir <that folder>.')
    print('\nInstalled. Start a new chat so the agent picks it up, then ask for a whiteboard explainer.')
    print('The first run checks for ffmpeg, Node, Chrome and the rest, and installs what is missing.')


if __name__ == '__main__':
    main()
