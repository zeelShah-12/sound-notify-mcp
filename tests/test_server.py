"""End-to-end test: talks to the real MCP server over the real MCP protocol
(in-process transport), the same way Claude Code or Claude Desktop would --
not just calling the Python function directly.
"""

import sys
from unittest.mock import patch

import pytest

from mcp import Client, ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import sound_notify.server as server_module


@pytest.mark.asyncio
async def test_notify_tool_is_registered():
    async with Client(server_module.server) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools.tools}
    assert "notify" in names


@pytest.mark.asyncio
async def test_notify_tool_call_succeeds_and_plays_sound():
    with patch("sound_notify.server.play_notification", return_value=True) as mock_play:
        async with Client(server_module.server) as client:
            result = await client.call_tool("notify", {"status": "success", "message": "build finished"})

    mock_play.assert_called_once_with("success")
    assert result.is_error is False
    text = result.content[0].text
    assert "success" in text
    assert "build finished" in text


@pytest.mark.asyncio
async def test_notify_tool_falls_back_to_bell_and_says_so():
    with patch("sound_notify.server.play_notification", return_value=False):
        async with Client(server_module.server) as client:
            result = await client.call_tool("notify", {"status": "error"})

    text = result.content[0].text
    assert "terminal bell" in text


@pytest.mark.asyncio
async def test_notify_tool_rejects_unknown_status_by_defaulting_to_success():
    with patch("sound_notify.server.play_notification", return_value=True) as mock_play:
        async with Client(server_module.server) as client:
            await client.call_tool("notify", {"status": "not-a-real-status"})

    mock_play.assert_called_once_with("success")


@pytest.mark.asyncio
async def test_notify_tool_over_real_stdio_subprocess():
    """Spawns the installed `sound-notify serve` console script as a real
    subprocess and talks MCP-over-stdio to it -- exactly the transport and
    exactly the command Claude Code / Claude Desktop use once this package is
    pip-installed. This exercises the real synthesized chime (no mocking), so
    it doubles as a smoke test that audio playback doesn't crash on this
    machine.
    """
    params = StdioServerParameters(command="sound-notify", args=["serve"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert "notify" in {t.name for t in tools.tools}

            result = await session.call_tool("notify", {"status": "info", "message": "subprocess smoke test"})
            assert result.is_error is False
            assert "subprocess smoke test" in result.content[0].text
