"""Tests for the `sound-notify setup` CLI command.

This exists because the first version called `subprocess.run(["claude", ...])`
without `shell=True` on Windows, which raised `FileNotFoundError: [WinError 2]`
-- Windows resolves the `claude` CLI to a `.cmd` shim, and `CreateProcess` can't
launch a .cmd directly without a shell to interpret it. That bug only shows up
against the real `claude` binary, never against a mock, so this pins the fix
by asserting the shell flag itself rather than just that the call "succeeds".
"""

import os
from unittest.mock import MagicMock, patch

from sound_notify.__main__ import _setup


def test_setup_passes_shell_true_on_windows_so_the_cmd_shim_resolves():
    with patch("shutil.which", return_value=r"C:\npm\claude.CMD"), \
         patch("os.name", "nt"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        _setup()

    assert mock_run.call_args.kwargs["shell"] is True


def test_setup_does_not_need_shell_on_posix():
    with patch("shutil.which", return_value="/usr/local/bin/claude"), \
         patch("os.name", "posix"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        _setup()

    assert mock_run.call_args.kwargs["shell"] is False


def test_setup_reports_missing_claude_cli_instead_of_crashing():
    with patch("shutil.which", return_value=None), \
         patch("subprocess.run") as mock_run, \
         patch("builtins.print") as mock_print, \
         patch("sys.exit") as mock_exit:
        _setup()

    mock_exit.assert_called_once_with(1)
    mock_run.assert_not_called()
    printed = " ".join(str(c.args[0]) for c in mock_print.call_args_list)
    assert "claude mcp add sound-notify -- sound-notify serve" in printed
