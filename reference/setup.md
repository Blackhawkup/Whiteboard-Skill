# Setup

## What `wb setup --install` does

| Piece | Why | How it installs |
|---|---|---|
| Python 3.10 to 3.13 | The tools | Homebrew, apt, dnf, pacman or winget |
| ffmpeg | Audio and video | Same |
| Node.js 22+ and git | Flow Studio | Same |
| Python packages | Tracing, rendering, word timing | A private environment in `~/WhiteboardFilms/.tools`, about 500 MB |
| Google Chrome | Rendering and Flow | Homebrew cask or winget; otherwise playwright's Chromium is used for rendering |
| Flow Studio | Pictures and voice | Cloned to `~/flow-mcp` and built |
| The Flow connection | So your agent has the Flow tools | Added to every agent found (below). Config files get a `.before-whiteboard` backup first |

Nothing is installed by `wb setup` without `--install`. Running it again is safe.

**What only the user can do:**
- Type their password if a system install asks for one. If Homebrew itself is missing on a Mac, it prints the official install command for them to paste.
- Sign in to Google: `npm run login` inside `~/flow-mcp` opens Flow's own Chrome window. They sign in, open or create a Flow project, and leave the window open. You never see or type the password.
- Restart the agent, or start a new chat, so it loads the new tools.

## Each agent

| Agent | Global skills folder | Where the Flow connection goes |
|---|---|---|
| Claude Code | `~/.claude/skills` | `claude mcp add --scope user flow -- node ~/flow-mcp/dist/index.js` |
| Codex | `~/.codex/skills`, `~/.agents/skills` | `~/.codex/config.toml`, section `[mcp_servers.flow]` |
| Antigravity | `~/.gemini/antigravity/skills` | `~/.gemini/antigravity/mcp_config.json`, under `mcpServers` |
| OpenCode | `~/.config/opencode/skills` | `~/.config/opencode/opencode.json`, under `mcp` with `"type": "local"` |
| Gemini CLI | `~/.gemini/skills` | `~/.gemini/settings.json`, under `mcpServers` |
| Cursor | `~/.cursor/skills` | `~/.cursor/mcp.json`, under `mcpServers` |
| Anything else | Run `python3 scripts/install.py --dir <its skills folder>`, or tell it to read `SKILL.md` | Add a local MCP server: command `node`, argument `~/flow-mcp/dist/index.js` (full path) |

Skill folder locations change between versions of these tools. If an agent does not list the skill after a restart, tell it directly: "Read `<folder>/SKILL.md` and follow it." It works the same way.

## Installing from the zip

When the user says "install the whiteboard skill in my downloads folder and make it available globally":
1. Find the zip in their Downloads folder (its name contains `whiteboard`) and unzip it somewhere temporary.
2. Run `python3 <unzipped>/whiteboard-explainer/scripts/install.py`.
3. Tell them to start a new chat and ask for a whiteboard explainer.

## Manual mode: no Flow tools in this agent

The film can still be made. Everything else in the skill runs on its own.
- **Images:** `wb prompts <film>` writes `prompts.json`. Ask the user to run those prompts in [Google Flow](https://labs.google/fx/tools/flow), or any image tool, then give you the files. Continue with `wb intake`.
- **Voice:** `wb tts <film> --voice Charon` calls Google AI Studio directly if the key is saved, or use any recording or other tool's file with `wb voice`.

## Windows

Use `scripts\wb.cmd` instead of `scripts/wb`. The setup and rendering pipeline supports Windows (via `winget` for system tools, `Scripts\python.exe` virtual environment, and normalized POSIX paths for ffmpeg concat rendering). Run commands in PowerShell or CMD. Ensure Git and Python 3.10-3.13 are available in your PATH.

## When something fails

| Symptom | Fix |
|---|---|
| `wb` says a package is missing | `wb setup --install` |
| `flow_status` says not signed in or no project | The user signs in and opens a Flow project in Flow's Chrome window |
| Flow tools missing after install | Restart the agent. Check the table above for that agent's config |
| Agent batch fails or returns too few images | See "When a batch fails" in `reference/prompts.md` |
| `EPERM` reading files on a Mac | Keep `flow-mcp` and `~/WhiteboardFilms` out of Desktop, Documents and Downloads, which macOS protects |
| A render is very slow | `WB_WORKERS=<n>` sets the parallel renderers. The default is half the CPU cores |
