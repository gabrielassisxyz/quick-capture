"""Tests for the enrichment module."""

import json
import sqlite3
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from quick_capture.db import get_capture, save_capture
from quick_capture.enrich import (
    ENRICHMENT_PROMPT,
    enrich_capture,
    parse_enrichment_output,
)


class TestParseEnrichmentOutput:
    """Tests for parse_enrichment_output."""

    def test_parses_valid_json_with_all_fields(self) -> None:
        """Plain JSON object with all fields is parsed correctly."""
        output = json.dumps({
            "bucket": "Task",
            "enriched_text": "Develop this idea further",
            "tags": ["ideas", "capture"],
            "wikilinks": ["[[Projects]]"],
        })
        result = parse_enrichment_output(output)
        assert result["bucket"] == "Task"
        assert result["enriched_text"] == "Develop this idea further"
        assert result["tags"] == ["ideas", "capture"]
        assert result["wikilinks"] == ["[[Projects]]"]

    def test_handles_json_wrapped_in_code_fences(self) -> None:
        """JSON wrapped in ```json ... ``` code fences is extracted."""
        inner = json.dumps({
            "bucket": "Idea",
            "enriched_text": "A creative thought",
            "tags": ["creative"],
            "wikilinks": [],
        })
        output = f"```json\n{inner}\n```"
        result = parse_enrichment_output(output)
        assert result["bucket"] == "Idea"
        assert result["enriched_text"] == "A creative thought"

    def test_extracts_last_json_object_from_mixed_output(self) -> None:
        """Last JSON object is extracted from output with preamble text."""
        inner = json.dumps({
            "bucket": "Reference",
            "enriched_text": "A useful link",
            "tags": [],
            "wikilinks": ["[[Reading]]"],
        })
        output = f"Here is the enrichment:\n{inner}"
        result = parse_enrichment_output(output)
        assert result["bucket"] == "Reference"

    def test_raises_value_error_on_unparseable_output(self) -> None:
        """ValueError is raised when no valid JSON can be found."""
        with pytest.raises(ValueError, match="Could not parse"):
            parse_enrichment_output("this is not json at all")

    def test_rejects_invalid_bucket(self) -> None:
        """Invalid bucket value raises ValueError."""
        output = json.dumps({
            "bucket": "InvalidBucket",
            "enriched_text": "text",
            "tags": [],
            "wikilinks": [],
        })
        with pytest.raises(ValueError, match="bucket"):
            parse_enrichment_output(output)

    def test_accepts_all_valid_buckets(self) -> None:
        """All four valid buckets are accepted."""
        for bucket in ("Task", "Idea", "Reference", "Question"):
            output = json.dumps({
                "bucket": bucket,
                "enriched_text": "text",
                "tags": [],
                "wikilinks": [],
            })
            result = parse_enrichment_output(output)
            assert result["bucket"] == bucket


class TestEnrichmentPrompt:
    """Tests for ENRICHMENT_PROMPT constant."""

    def test_contains_wiki_query_instruction(self) -> None:
        """ENRICHMENT_PROMPT includes wiki-query instruction (ENRI-04)."""
        assert "wiki-query" in ENRICHMENT_PROMPT.lower()


class TestEnrichCapture:
    """Tests for enrich_capture pipeline."""

    def test_sets_status_enriching_then_enriched_on_success(
        self, db: sqlite3.Connection
    ) -> None:
        """On success: status goes unprocessed → enriching → enriched."""
        capture_id = save_capture("Remind me to buy milk", conn=db)
        mock_output = json.dumps({
            "bucket": "Task",
            "enriched_text": "Buy milk — an actionable task",
            "tags": ["errands"],
            "wikilinks": ["[[Shopping]]"],
        })

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output

        with patch("quick_capture.enrich.subprocess.run", return_value=mock_result):
            result = enrich_capture(capture_id, conn=db)

        assert result["bucket"] == "Task"
        capture = get_capture(capture_id, conn=db)
        assert capture["status"] == "enriched"

    def test_resets_status_to_unprocessed_on_subprocess_failure(
        self, db: sqlite3.Connection
    ) -> None:
        """On subprocess failure: status goes back to unprocessed."""
        capture_id = save_capture("Test thought", conn=db)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "opencode error"

        with (
            patch("quick_capture.enrich.subprocess.run", return_value=mock_result),
            pytest.raises(RuntimeError, match="opencode"),
        ):
            enrich_capture(capture_id, conn=db)

        capture = get_capture(capture_id, conn=db)
        assert capture["status"] == "unprocessed"

    def test_resets_status_on_failure_with_existing_capture(
        self, db: sqlite3.Connection
    ) -> None:
        """On subprocess failure with existing capture: status resets to unprocessed."""
        capture_id = save_capture("Test thought", conn=db)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "opencode error"

        with (
            patch("quick_capture.enrich.subprocess.run", return_value=mock_result),
            pytest.raises(RuntimeError, match="opencode"),
        ):
            enrich_capture(capture_id, conn=db)

        capture = get_capture(capture_id, conn=db)
        assert capture["status"] == "unprocessed"

    def test_timeout_resets_status_to_unprocessed(
        self, db: sqlite3.Connection
    ) -> None:
        """On subprocess timeout: status resets to unprocessed and RuntimeError raised."""
        capture_id = save_capture("Test thought", conn=db)

        with (
            patch(
                "quick_capture.enrich.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["opencode"], timeout=120),
            ),
            pytest.raises(RuntimeError, match="timed out"),
        ):
            enrich_capture(capture_id, conn=db)

        capture = get_capture(capture_id, conn=db)
        assert capture["status"] == "unprocessed"

    def test_raises_value_error_for_missing_capture(
        self, db: sqlite3.Connection
    ) -> None:
        """enrich_capture raises ValueError if capture not found."""
        with pytest.raises(ValueError, match="not found"):
            enrich_capture("nonexistent-id", conn=db)

    def test_subprocess_uses_shell_false(self, db: sqlite3.Connection) -> None:
        """subprocess.run is called with shell=False (security: T-03-01)."""
        capture_id = save_capture("Test", conn=db)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "bucket": "Task",
            "enriched_text": "text",
            "tags": [],
            "wikilinks": [],
        })

        with patch("quick_capture.enrich.subprocess.run", return_value=mock_result) as mock_run:
            enrich_capture(capture_id, conn=db)
            # Verify the command is a list (not a string), ensuring shell=False behavior
            args = mock_run.call_args[0][0]
            assert isinstance(args, list)
            # Verify shell=False is explicitly set
            assert mock_run.call_args[1].get("shell") is False


class TestEnrichCliFlag:
    """Tests for --enrich CLI flag."""

    def test_enrich_flag_triggers_enrichment(self) -> None:
        """--enrich flag calls enrich_capture and exits with 0."""
        mock_result = {
            "bucket": "Task",
            "enriched_text": "text",
            "tags": [],
            "wikilinks": [],
        }
        from quick_capture.cli import main

        with (
            patch("sys.argv", ["quick-capture", "--enrich", "test-id"]),
            patch(
                "quick_capture.cli.enrich_capture",
                return_value=mock_result,
            ) as mock_enrich,
            patch.object(sys, "exit", side_effect=SystemExit) as mock_exit,
        ):
            with pytest.raises(SystemExit):
                main()
            mock_enrich.assert_called_once_with("test-id")
            mock_exit.assert_called_with(0)

    def test_enrich_flag_exits_1_on_failure(self) -> None:
        """--enrich flag prints error and exits with 1 on failure."""
        from quick_capture.cli import main

        with (
            patch("sys.argv", ["quick-capture", "--enrich", "bad-id"]),
            patch(
                "quick_capture.cli.enrich_capture",
                side_effect=RuntimeError("opencode failed"),
            ),
            patch.object(sys, "exit", side_effect=SystemExit) as mock_exit,
        ):
            with pytest.raises(SystemExit):
                main()
            mock_exit.assert_called_with(1)

