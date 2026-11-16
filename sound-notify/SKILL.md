---
name: sound-notify
description: Plays a short chime when the agent finishes a task the user is waiting on, so they can look away from the screen. Use after completing a build, a multi-step task, a bug fix, or when blocked and needing the user's input. Requires the Sound Notify MCP server.
---

# Sound Notify

This skill lets the user step away while you work. Call the `notify` tool from
the Sound Notify MCP server to play a chime when they need to come back.

## When to call `notify`

Call it **once**, at the moment the user's attention is needed:

- You finished the task they asked for (built a feature, fixed a bug, ran a long job) → `status: "success"`
- The task failed, or you are blocked and need their answer or approval → `status: "error"`
- A minor heads-up they may want to see, but nothing is blocked → `status: "info"`

## When NOT to call it

- After every small step, file edit, or tool call
- For quick one-message answers the user is already watching
- More than once for the same finished task

## How to call it

```
notify(status="success", message="Login page built and tests pass")
```

- `status`: `"success"` (default), `"error"`, or `"info"`
- `message`: short summary of what finished. It is logged, not spoken aloud.

Call `notify` as the last action, right before your final reply, so the chime
plays when the result is actually ready.

## Setup

Install the Sound Notify MCP server from https://github.com/zeelShah-12/sound-notify-mcp
(`pip install` from the repo, then run `sound-notify setup`). See its README for details.
