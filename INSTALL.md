# Installation and Setup Guide: Whiteboard Explainer Skill

This guide walks you through installing and configuring the **Whiteboard Explainer Skill** across all supported AI coding agents and operating systems (Windows, macOS, and Linux).

---

## Table of Contents

1. [System Prerequisites](#1-system-prerequisites)
2. [Quick Installation (Recommended)](#2-quick-installation-recommended)
3. [Agent Configuration Details](#3-agent-configuration-details)
4. [Setting Up Google Flow Studio (MCP Server)](#4-setting-up-google-flow-studio-mcp-server)
5. [Setting Up Voice Narration (Gemini TTS)](#5-setting-up-voice-narration-gemini-tts)
6. [Multi-Model Configuration](#6-multi-model-configuration)
7. [Verifying Your Setup](#7-verifying-your-setup)
8. [Manual / Offline Mode (No Flow Tools)](#8-manual--offline-mode-no-flow-tools)
9. [Troubleshooting & Common Issues](#9-troubleshooting--common-issues)

---

## 1. System Prerequisites

The whiteboard pipeline uses Python for stroke tracing and audio mixing, Node.js for the Flow Studio MCP server, Google Chrome/Chromium via Playwright for 60fps headless canvas rendering, and FFmpeg for video encoding and audio analysis.

### Required Software:
- **Python**: 3.10 to 3.13 (`python3` or `python` on Windows)
- **Node.js**: v22.0.0 or later (`node` and `npm`)
- **FFmpeg & FFprobe**: in your system PATH
- **Google Chrome**: (or Chromium)
- **Git**: for cloning repositories and managing dependencies

### Installing Prerequisites by Operating System:

#### Windows (via winget or manual installer)
Run PowerShell as Administrator or standard user:
```powershell
# Install system packages via winget
winget install -e --id Python.Python.3.12
winget install -e --id Gyan.FFmpeg
winget install -e --id OpenJS.NodeJS
winget install -e --id Google.Chrome
winget install -e --id Git.Git
```
*Restart your PowerShell terminal after installing to ensure all binaries are present in your `$PATH`.*

#### macOS (via Homebrew)
```bash
brew install python@3.12 ffmpeg node git
brew install --cask google-chrome
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg nodejs npm git google-chrome-stable
```

#### Linux (Fedora)
```bash
sudo dnf install -y python3 python3-virtualenv ffmpeg nodejs npm git
```

---

## 2. Quick Installation (Recommended)

### Step 2.1: Clone the Repository
Clone this repository to your machine:
```bash
git clone https://github.com/Blackhawkup/Whiteboard-Skill.git
cd Whiteboard-Skill
```

### Step 2.2: Register the Skill Globally with Your Agents
Run the installer script:
- **macOS / Linux**:
  ```bash
  python3 scripts/install.py
  ```
- **Windows**:
  ```powershell
  python scripts\install.py
  ```

This automatically detects installed coding agents on your machine and installs the skill folder to their respective global skill directories:
- **Claude Code**: `~/.claude/skills/whiteboard-explainer`
- **Codex / Open Agent Standard**: `~/.agents/skills/whiteboard-explainer` or `~/.codex/skills/whiteboard-explainer`
- **Antigravity**: `~/.gemini/antigravity/skills/whiteboard-explainer` and `~/.gemini/config/skills/whiteboard-explainer`
- **OpenCode**: `~/.config/opencode/skills/whiteboard-explainer`
- **Gemini CLI**: `~/.gemini/skills/whiteboard-explainer`
- **Cursor**: `~/.cursor/skills/whiteboard-explainer`
- **Windsurf**: `~/.codeium/windsurf/skills/whiteboard-explainer`

*To install into a custom directory, pass `--dir <path>`:*
```bash
python3 scripts/install.py --dir /path/to/custom/agent/skills
```

---

### Step 2.3: Bootstrap Dependencies & Flow Studio
Run the setup utility with the `--install` flag:

- **macOS / Linux**:
  ```bash
  ./scripts/wb setup --install
  ```
- **Windows**:
  ```powershell
  .\scripts\wb.cmd setup --install
  ```

**What this automatically does:**
1. Checks for Python, FFmpeg, Node.js, Git, and Chrome.
2. Creates an isolated Python virtual environment in `~/WhiteboardFilms/.tools/venv` (or `%USERPROFILE%\WhiteboardFilms\.tools\venv`).
3. Installs required Python libraries: `numpy`, `pillow`, `scipy`, `scikit-image`, `playwright`, and `faster-whisper`.
4. Clones and builds **Flow Studio** (`flow-mcp`) in `~/flow-mcp` (or `%USERPROFILE%\flow-mcp`).
5. Configures the Flow MCP server entry in every detected agent's configuration file.

---

## 3. Agent Configuration Details

If you prefer to configure your agent's Model Context Protocol (MCP) server manually, use the following settings:

| Agent | Config File Location | MCP Configuration Entry |
|---|---|---|
| **Claude Code** | Global CLI command | `claude mcp add --scope user flow -- node <FLOW_DIR>/dist/index.js` |
| **Antigravity** | `~/.gemini/antigravity/mcp_config.json` | Under `"mcpServers"`: `{"flow": {"command": "node", "args": ["<FLOW_DIR>/dist/index.js"]}}` |
| **OpenCode** | `~/.config/opencode/opencode.json` | Under `"mcp"`: `{"flow": {"type": "local", "command": ["node", "<FLOW_DIR>/dist/index.js"], "enabled": true}}` |
| **Codex** | `~/.codex/config.toml` | Under `[mcp_servers.flow]`: `command = "node"`, `args = ["<FLOW_DIR>/dist/index.js"]` |
| **Cursor** | `~/.cursor/mcp.json` | Under `"mcpServers"`: `{"flow": {"command": "node", "args": ["<FLOW_DIR>/dist/index.js"]}}` |
| **Gemini CLI**| `~/.gemini/settings.json` | Under `"mcpServers"`: `{"flow": {"command": "node", "args": ["<FLOW_DIR>/dist/index.js"]}}` |

*(Replace `<FLOW_DIR>` with the full absolute path to `flow-mcp`, e.g., `/home/username/flow-mcp` or `C:/Users/username/flow-mcp`)*.

---

## 4. Setting Up Google Flow Studio (MCP Server)

Flow Studio gives your agent zero-cost doodle generation and camera asset generation directly inside Google Flow.

### Step 4.1: Log in to Google Flow
1. Navigate to your `flow-mcp` directory:
   ```bash
   cd ~/flow-mcp
   # On Windows: cd %USERPROFILE%\flow-mcp
   ```
2. Start the interactive login window:
   ```bash
   npm run login
   ```
3. A dedicated Google Chrome browser instance will open.
4. Sign in to your Google Account.
5. Visit [Google Flow (labs.google/fx/tools/flow)](https://labs.google/fx/tools/flow) and either open an existing project or create a new one.
6. **Important**: Leave this Chrome window open or minimized while using the whiteboard skill so the agent can communicate with it.

---

## 5. Setting Up Voice Narration (Gemini TTS)

The whiteboard skill generates expressive, human-like voice narration using Gemini's prebuilt voices (e.g. `Charon`, `Puck`, `Fenrir`, `Kore`, `Aoede`) through Google AI Studio.

### Getting a Free API Key
1. Go to [Google AI Studio](https://aistudio.google.com/) and create a free API key.

### Configuring Your Key
You have three flexible ways to save your API key:

#### Option A: Save in Flow Studio config (Recommended)
Save the key directly to `~/.flow-mcp/gemini-key` (or `%USERPROFILE%\.flow-mcp\gemini-key` on Windows):
- In bash:
  ```bash
  mkdir -p ~/.flow-mcp
  echo "YOUR_GEMINI_API_KEY" > ~/.flow-mcp/gemini-key
  ```
- In Windows PowerShell:
  ```powershell
  if (!(Test-Path "$HOME\.flow-mcp")) { New-Item -ItemType Directory -Path "$HOME\.flow-mcp" }
  Set-Content -Path "$HOME\.flow-mcp\gemini-key" -Value "YOUR_GEMINI_API_KEY"
  ```

#### Option B: Environment Variable
Export `GEMINI_API_KEY` in your shell profile (`.bashrc`, `.zshrc`, or Windows Environment Variables):
```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

#### Option C: Multi-Key Rotation Pool (Automatic Failover)
To avoid hitting free-tier 429 rate limits or quota exhaustion during production runs, you can supply as many keys as you want:
- **In Flow Studio Web UI:** Paste multiple keys into the Voice tab textarea (one per line). Click **Save & Verify Keys**.
- **In Environment:** Set `GEMINI_API_KEYS="KEY_1,KEY_2,KEY_3"` (comma or newline separated).
- **In Key File:** Put one key per line in `~/.flow-mcp/gemini-key`.

The engine automatically tests each key, tracks the active key index, and instantly fails over to the next key if a 429 quota limit or 403 error is encountered.

---

## 6. Multi-Model Configuration

The pipeline supports selecting and auto-failing over across multiple AI models:

### 6.1. Multiple Gemini TTS Voice Models
You are not locked into a single TTS model. The allowed model pool includes:
- `gemini-2.5-flash-preview-tts` (Default ultra-realistic narration)
- `gemini-2.0-flash`
- `gemini-1.5-flash`
- `gemini-2.5-pro`

**Ways to configure or override the TTS model:**
1. **Via CLI argument:**
   ```bash
   wb tts <film> --voice Charon --model gemini-2.0-flash
   ```
2. **Via `film.json`:**
   ```json
   {
     "tts_model": "gemini-2.5-flash-preview-tts"
   }
   ```
3. **Via Environment Variable:**
   ```bash
   export GEMINI_TTS_MODEL="gemini-2.0-flash"
   ```
*If a model returns a 404, 400, or model-level quota limit, the engine automatically tries the next model in the allowed model pool.*

### 6.2. Multiple Faster-Whisper Speech-to-Text Models
Word timing and synchronisation uses `faster-whisper`. You can select the model based on your speed vs. accuracy requirements:
- `base` (Default: ~150 MB, fast and accurate for English)
- `small` (~460 MB, higher accuracy for multi-speaker or noisy audio)
- `medium` (~1.5 GB, high-fidelity multilingual)
- `large-v3` (~3 GB, studio-grade transcription)
- `tiny` (~75 MB, ultra-fast low-resource)

**Ways to configure the Whisper model:**
1. **Via CLI argument:**
   ```bash
   wb voice <film> narration.wav --whisper-model small
   # or with tts:
   wb tts <film> --voice Charon --whisper-model small
   ```
2. **Via `film.json`:**
   ```json
   {
     "whisper_model": "small"
   }
   ```
3. **Via Environment Variable:**
   ```bash
   export WHISPER_MODEL="small"
   ```

### 6.3. Parallel Server Instances (Side-by-Side Video Generation)
If you are generating multiple videos simultaneously, you can run multiple independent Flow Studio instances on separate ports:
- **On Windows:** Double-click `flow-mcp\Flow Studio - New Window.cmd`
- **In Terminal:** Run `npm run studio:new` inside `~/flow-mcp` (or `node dist/studio.js --new`)
- **From Studio Web UI:** Click the **"+ New Studio Window (Parallel Server)"** button in the header.

Each instance finds an available port (`8788`, `8789`, etc.) and runs independently without collision.

---

## 7. Verifying Your Setup

To verify that your installation, dependencies, and rendering pipeline are functioning properly:

1. Run the bundled example film:
   - **macOS / Linux**:
     ```bash
     ./scripts/wb example chatbot-vs-agent
     ```
   - **Windows**:
     ```powershell
     .\scripts\wb.cmd example chatbot-vs-agent
     ```

2. What the verification does:
   - Sets up the example film in `~/WhiteboardFilms/films/chatbot-vs-agent`.
   - Times words against the audio track.
   - Traces image vector paths and computes stroke geometry.
   - Runs validation checks (pen speeds, boundaries, collisions).
   - Generates contact sheet previews in `out/sheets/`.

3. To render the full video:
   ```bash
   wb make chatbot-vs-agent
   ```
   The final MP4 will be rendered to `~/WhiteboardFilms/films/chatbot-vs-agent/out/chatbot-vs-agent.mp4`.

---

## 8. Manual / Offline Mode (No Flow Tools)

If you are using an agent that does not support Model Context Protocol (MCP) or if you want to operate without the Flow Studio browser window:

1. **Drawings / Images**:
   - Run `wb prompts <film>` to output `prompts.json`.
   - Generate your illustrations manually in any image tool (Google Flow, Midjourney, DALL-E, etc.).
   - Place image files and import them with:
     ```bash
     wb intake <film> name1=path/to/img1.png name2=path/to/img2.png
     ```
2. **Narration Audio**:
   - Record your own voice or generate TTS using `wb tts <film> --voice Charon`.
   - Lock the voice with:
     ```bash
     wb voice <film> path/to/narration.wav
     ```
3. Continue the standard build and make pipeline (`wb art`, `wb labels`, `wb make`).

---

## 9. Troubleshooting & Common Issues

| Issue / Error | Cause | Solution |
|---|---|---|
| `'wb' is not recognized` | Script not in PATH or using wrong launcher on Windows | On Windows, invoke `.\scripts\wb.cmd` or add the `scripts` folder to your system PATH. On Linux/macOS, invoke `./scripts/wb` or alias `wb`. |
| `Missing numpy / playwright / ...` | Python venv packages not installed | Run `wb setup --install` to automatically populate `~/WhiteboardFilms/.tools/venv`. |
| `flow_status reports not signed in` | Chrome profile expired or closed | Run `npm run login` inside `~/flow-mcp`, sign in to Google, and keep the window open. |
| `AI Studio says quota limit (429)` | Google AI Studio free tier rate limit reached | Add additional API keys separated by commas in `GEMINI_API_KEYS` or `~/.flow-mcp/gemini-key` for automatic failover rotation. |
| `EPERM` or permission denied (macOS) | macOS privacy sandbox on `Desktop`/`Downloads` | Keep films and `flow-mcp` in `~/WhiteboardFilms` and `~/flow-mcp`, not in protected user folders. |
| Slow rendering | CPU thread starvation | Set `WB_WORKERS=<n>` (e.g. `export WB_WORKERS=4`) before running `wb make`. |
