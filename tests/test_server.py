"""End-to-end test: talks to the real MCP server over the real MCP protocol
(in-process transport), the same way Claude Code or Claude Desktop would --
not just calling the Python function directly.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import Client, ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import server as server_module

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.asyncio
async def test_notify_tool_is_registered():
    async with Client(server_module.server) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools.tools}
    assert "notify" in names


@pytest.mark.asyncio
async def test_notify_tool_call_succeeds_and_plays_sound():
    with patch("server.play_notification", return_value=True) as mock_play:
        async with Client(server_module.server) as client:
            result = await client.call_tool("notify", {"status": "success", "message": "build finished"})

    mock_play.assert_called_once_with("success")
    assert result.is_error is False
    text = result.content[0].text
    assert "success" in text
    assert "build finished" in text


@pytest.mark.asyncio
async def test_notify_tool_falls_back_to_bell_and_says_so():
    with patch("server.play_notification", return_value=False):
        async with Client(server_module.server) as client:
            result = await client.call_tool("notify", {"status": "error"})

    text = result.content[0].text
    assert "terminal bell" in text


@pytest.mark.asyncio
async def test_notify_tool_rejects_unknown_status_by_defaulting_to_success():
    with patch("server.play_notification", return_value=True) as mock_play:
        async with Client(server_module.server) as client:
            await client.call_tool("notify", {"status": "not-a-real-status"})

    mock_play.assert_called_once_with("success")


@pytest.mark.asyncio
async def test_notify_tool_over_real_stdio_subprocess():
    """Spawns server.py as a real subprocess and talks MCP-over-stdio to it --
    exactly the transport Claude Code / Claude Desktop use. This exercises the
    real synthesized chime (no mocking), so it doubles as a smoke test that
    audio playback doesn't crash on this machine.
    """
    params = StdioServerParameters(command=sys.executable, args=["server.py"], cwd=str(PROJECT_ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert "notify" in {t.name for t in tools.tools}

            result = await session.call_tool("notify", {"status": "info", "message": "subprocess smoke test"})
            assert result.is_error is False
            assert "subprocess smoke test" in result.content[0].text
