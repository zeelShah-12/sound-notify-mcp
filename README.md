# Sound Notify MCP Server

Claude can take minutes to finish building or fixing something — so you either sit and
watch the terminal, or tab away and miss the moment it's done. **Sound Notify** is a tiny
MCP (Model Context Protocol) server that gives Claude a `notify` tool: a single call plays
a short audio chime, so you get an audible cue the moment a task actually finishes.

No API keys, no cloud calls, no bundled audio files — every chime is a sine-wave sequence
synthesized in memory at call time and played through whatever the OS already has.

## How it works

1. This MCP server exposes exactly one tool: `notify(status, message)`.
2. Claude is told (via the server's `instructions` string, which becomes part of its
   context once the server is connected) to call `notify` once it finishes a build, fixes
   a bug, or completes a task you were waiting on — not after every small step.
3. `notify` synthesizes a short sine-wave chime (different for `success` / `error` / `info`)
   and plays it through the platform's native audio path:
   - **Windows** — `winsound.PlaySound(..., SND_MEMORY)`, no temp file needed
   - **macOS** — writes a temp WAV, plays it with `afplay`
   - **Linux** — writes a temp WAV, tries `paplay`, then `aplay`, then `play`
   - **No backend found anywhere** — falls back to the terminal bell (`\a`) so you still
     get *something*, and the tool's return text says so explicitly

Claude decides *when* to call the tool based on the instructions and the tool's own
description — this is the honest trade-off of building it as an MCP tool call instead of
a Claude Code lifecycle hook: it's flexible (Claude can pass a custom `message`, and this
works in any MCP client, not just Claude Code) but relies on Claude remembering to call it,
rather than firing unconditionally on every response.

## Quick Start

### Prerequisites

- Python 3.10+
- An MCP client (e.g. Claude Code CLI)

### 1. Install

```bash
pip install git+https://github.com/zeelShah-12/sound-notify-mcp.git
```

This puts a `sound-notify` command on your PATH — no cloning, no hardcoded file paths.

### 2. Register it with Claude Code

```bash
sound-notify setup
```

```text
Registered 'sound-notify' with Claude Code.
Added stdio MCP server sound-notify with command: sound-notify serve to local config
Restart Claude Code (or start a new session) and it will have a `notify` tool.
```

No credentials to enter — this server needs none. If the `claude` CLI isn't on your PATH,
`sound-notify setup` tells you the one manual command to run instead:

```bash
claude mcp add sound-notify -- sound-notify serve
```

### 3. Restart your client

Restart Claude Code (or start a new session) and check it connected:

```bash
claude mcp list
```

### Add it to Claude Desktop instead

Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sound-notify": {
      "command": "sound-notify",
      "args": ["serve"]
    }
  }
}
```

## The tool

```
notify(status: "success" | "error" | "info" = "success", message: str = "") -> str
```

Example call and result:

```
> notify(status="success", message="finished refactoring the auth module")
"Played success notification via audio device -- finished refactoring the auth module"
```

## Verifying it actually works

This was built and verified end-to-end, not just unit-tested in isolation:

```bash
git clone https://github.com/zeelShah-12/sound-notify-mcp.git
cd sound-notify-mcp
pip install -r requirements-dev.txt   # editable install + pytest
pytest -v
```

15 tests cover four layers:
- **Tone synthesis** (`tests/test_sound.py`) — the generated WAV has the right sample rate,
  channel count, duration, and never clips past 16-bit range.
- **Playback backend selection** (`tests/test_sound.py`) — the correct OS-specific player is
  invoked, with the fallback path exercised too.
- **The `setup` CLI** (`tests/test_cli.py`) — registration succeeds, fails gracefully when
  `claude` isn't installed, and (see the bug below) actually passes the right subprocess flags.
- **The actual MCP protocol** (`tests/test_server.py`) — one test talks to the server
  in-process, and one spawns the installed `sound-notify serve` console script as a real
  subprocess and talks MCP-over-stdio to it, exactly the way Claude Code or Claude Desktop
  does: list tools, call `notify`, check the response. That subprocess test uses the *real*
  (non-mocked) sound backend, so it doubles as a smoke test that audio playback doesn't
  crash on the current machine.

## Real bugs this caught

Both of these passed their first, naively-mocked unit test and only broke against the real
thing — which is why the test suite above insists on exercising real subprocesses/binaries
wherever practical, not just mocked interfaces:

- **`winsound.PlaySound(data, SND_MEMORY | SND_ASYNC)` on Windows** raised
  `RuntimeError: Cannot play asynchronously from memory` the first time it actually tried to
  play a sound — `SND_ASYNC` isn't supported together with `SND_MEMORY`. Fixed by playing
  synchronously, a non-issue since a chime is well under a second long.
- **`sound-notify setup` calling `subprocess.run(["claude", ...])`** raised
  `FileNotFoundError: [WinError 2]` against the real `claude` CLI on Windows, because
  `claude` resolves to a `.cmd` shim that `CreateProcess` can't launch without a shell.
  Fixed by passing `shell=True` on Windows only.

## Project structure

```
14 project/
├── pyproject.toml           Packaging + the `sound-notify` console-script entry point
├── src/sound_notify/
│   ├── __main__.py            CLI: `sound-notify serve` / `sound-notify setup`
│   ├── server.py               MCP server + the `notify` tool definition
│   └── sound.py                 Tone synthesis (stdlib `wave`/`math`) + cross-platform playback
├── tests/
│   ├── test_sound.py            Synthesis + backend-selection unit tests
│   ├── test_cli.py               `setup` command tests
│   └── test_server.py             Real MCP protocol tests (in-process + stdio subprocess)
├── requirements-dev.txt
└── pytest.ini
```

## Notes for the portfolio writeup

- Deliberately synthesizes tones instead of bundling `.wav` assets — no licensing
  questions, no binary files in the repo, and the exact frequencies/durations are visible
  and tunable in `sound.py`.
- `status="error"` uses a distinct falling two-note tone from `status="success"`'s rising
  chime, so you can tell success from failure by ear without looking at the screen.
- This plays a *sound*, not text-to-speech — the `message` argument is for the tool's
  return text (useful for logging what finished) but is never spoken aloud.
