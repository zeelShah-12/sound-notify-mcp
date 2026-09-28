"""CLI entry point.

`sound-notify serve` (the default) runs the MCP server over stdio -- this is
what an MCP client actually launches.

`sound-notify setup` registers it with Claude Code automatically by shelling
out to `claude mcp add`, the same one-command experience as the setup wizard
in other MCP server projects, minus the credential prompts -- this server
needs none.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def _serve() -> None:
    from sound_notify.server import server

    server.run()


def _setup() -> None:
    if shutil.which("claude") is None:
        print(
            "Could not find the `claude` CLI on PATH. Install Claude Code first, then run:\n"
            "  claude mcp add sound-notify -- sound-notify serve"
        )
        sys.exit(1)
        return  # unreachable in real usage; guards against a mocked sys.exit in tests

    # On Windows, the `claude` CLI resolves to a .cmd shim that CreateProcess
    # can't launch directly -- it needs a shell to interpret it.
    result = subprocess.run(
        ["claude", "mcp", "add", "sound-notify", "--", "sound-notify", "serve"],
        capture_output=True,
        text=True,
        shell=(os.name == "nt"),
    )
    if result.returncode == 0:
        print("Registered 'sound-notify' with Claude Code.")
        print(result.stdout.strip())
        print("Restart Claude Code (or start a new session) and it will have a `notify` tool.")
    else:
        print("Could not auto-register with Claude Code:")
        print((result.stderr or result.stdout).strip())
        print("\nYou can add it manually instead:")
        print("  claude mcp add sound-notify -- sound-notify serve")
        sys.exit(result.returncode)


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "serve"
    if command == "setup":
        _setup()
    elif command == "serve":
        _serve()
    else:
        print(f"Unknown command: {command}\nUsage: sound-notify [serve|setup]")
        sys.exit(1)


if __name__ == "__main__":
    main()
