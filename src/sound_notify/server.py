"""MCP server that lets Claude alert the user with a sound when it finishes
building or completing something, instead of the user having to watch the
screen the whole time.
"""

from mcp.server.mcpserver import MCPServer

from sound_notify.sound import play_notification

server = MCPServer(
    "sound-notify",
    instructions=(
        "Call the `notify` tool once, right after you finish building something, "
        "complete a multi-step task, or fix a bug the user asked about -- so the "
        "user hears a chime instead of having to watch the screen the whole time. "
        "Do not call it after every small step, only when the task the user is "
        "waiting on is actually done."
    ),
)


@server.tool()
def notify(status: str = "success", message: str = "") -> str:
    """Play a short notification chime to alert the user that a task finished.

    Args:
        status: "success" for a completed/working task, "error" for a task
            that failed or needs the user's attention, "info" for a minor
            heads-up. Defaults to "success".
        message: optional short description of what finished, echoed back in
            the tool result for logging (not spoken aloud -- this plays a
            sound, not text-to-speech).
    """
    if status not in ("success", "error", "info"):
        status = "success"
    played = play_notification(status)  # type: ignore[arg-type]
    backend = "audio device" if played else "terminal bell (no audio backend found)"
    label = f" -- {message}" if message else ""
    return f"Played {status} notification via {backend}{label}"


if __name__ == "__main__":
    server.run()
