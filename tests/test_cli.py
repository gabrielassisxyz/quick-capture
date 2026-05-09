"""Tests for the CLI/TUI module."""

import sys
from unittest.mock import patch

import pytest

from quick_capture.cli import main, run_capture_tui


class TestRunCaptureTui:
    """Tests for run_capture_tui."""

    def test_returns_stripped_text_on_submit(self):
        """Multiline input is returned stripped."""
        with patch("quick_capture.cli.prompt", return_value="Line 1\nLine 2"):
            result = run_capture_tui()
            assert result == "Line 1\nLine 2"

    def test_returns_none_on_keyboard_interrupt(self):
        """Escape key (KeyboardInterrupt) returns None."""
        with patch("quick_capture.cli.prompt", side_effect=KeyboardInterrupt):
            result = run_capture_tui()
            assert result is None

    def test_returns_none_on_whitespace_only(self):
        """Whitespace-only input returns None (no save)."""
        with patch("quick_capture.cli.prompt", return_value="   \n  \t  "):
            result = run_capture_tui()
            assert result is None

    def test_strips_leading_trailing_whitespace(self):
        """Leading/trailing whitespace is stripped from result."""
        with patch("quick_capture.cli.prompt", return_value="  hello world  "):
            result = run_capture_tui()
            assert result == "hello world"


class TestMain:
    """Tests for main entry point."""

    def test_saves_and_exits_on_capture(self):
        """Successful capture calls save_capture and exits with 0."""
        with (
            patch("sys.argv", ["quick-capture"]),
            patch("quick_capture.cli.prompt", return_value="My thought"),
            patch("quick_capture.cli.save_capture", return_value="abc-123-def"),
            patch.object(sys, "exit", side_effect=SystemExit) as mock_exit,
        ):
            with pytest.raises(SystemExit):
                main()
            mock_exit.assert_called_with(0)

    def test_cancels_and_exits_on_none(self):
        """Cancel (None from TUI) prints Cancelled and exits with 0."""
        with (
            patch("sys.argv", ["quick-capture"]),
            patch("quick_capture.cli.prompt", side_effect=KeyboardInterrupt),
            patch.object(sys, "exit", side_effect=SystemExit) as mock_exit,
        ):
            with pytest.raises(SystemExit):
                main()
            mock_exit.assert_called_with(0)

    def test_rejects_oversized_input(self):
        """Input over 10KB is rejected with error exit."""
        with (
            patch("sys.argv", ["quick-capture"]),
            patch("quick_capture.cli.prompt", return_value="x" * 10001),
            patch.object(sys, "exit", side_effect=SystemExit) as mock_exit,
        ):
            with pytest.raises(SystemExit):
                main()
            mock_exit.assert_called_with(1)

