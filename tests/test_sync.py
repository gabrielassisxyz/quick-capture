"""Tests for wiki sync module."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import frontmatter
import httpx
import pytest

from quick_capture.db import get_enrichment, is_synced, save_capture, save_enrichment
from quick_capture.sync import (
    _validate_vault_path,
    create_daily_rollup,
    create_inbox_page,
    create_weekly_rollup,
    sync_all_to_wiki,
    sync_capture_to_wiki,
)


class TestCreateInboxPage:
    """Tests for create_inbox_page."""

    def test_creates_file(self, db, vault_path, enriched_capture):
        """create_inbox_page writes a .md file under vault_path/inbox/."""
        path = create_inbox_page(
            capture_id=enriched_capture["id"],
            original_text=enriched_capture["original_text"],
            enriched_text=enriched_capture["enriched_text"],
            bucket=enriched_capture["bucket"],
            tags=enriched_capture["tags"],
            wikilinks=enriched_capture["wikilinks"],
            created_at=enriched_capture["created_at"],
            vault_path=vault_path,
        )
        assert path.exists()
        assert path.suffix == ".md"
        assert "inbox" in str(path)

    def test_filename_format(self, db, vault_path, enriched_capture):
        """Filename follows YYYY-MM-DD-quick-capture-{short_id}.md format."""
        path = create_inbox_page(
            capture_id=enriched_capture["id"],
            original_text=enriched_capture["original_text"],
            enriched_text=enriched_capture["enriched_text"],
            bucket=enriched_capture["bucket"],
            tags=enriched_capture["tags"],
            wikilinks=enriched_capture["wikilinks"],
            created_at=enriched_capture["created_at"],
            vault_path=vault_path,
        )
        filename = path.name
        # Should start with date pattern and contain quick-capture + short_id
        assert filename.startswith("20")  # date starts with year
        assert "quick-capture" in filename
        assert enriched_capture["id"][:8] in filename

    def test_frontmatter(self, db, vault_path, enriched_capture):
        """Page frontmatter has type=inbox, source=inbox, capture_id, bucket, tags, status, related."""
        path = create_inbox_page(
            capture_id=enriched_capture["id"],
            original_text=enriched_capture["original_text"],
            enriched_text=enriched_capture["enriched_text"],
            bucket=enriched_capture["bucket"],
            tags=enriched_capture["tags"],
            wikilinks=enriched_capture["wikilinks"],
            created_at=enriched_capture["created_at"],
            vault_path=vault_path,
        )
        post = frontmatter.load(path)
        assert post.metadata["type"] == "inbox"
        assert post.metadata["source"] == "inbox"
        assert post.metadata["capture_id"] == enriched_capture["id"]
        assert post.metadata["bucket"] == enriched_capture["bucket"]
        assert "inbox" in post.metadata["tags"]
        assert "quick-capture" in post.metadata["tags"]
        assert post.metadata["status"] == "current"
        # related should contain wikilinks
        assert any("[[Artificial Intelligence]]" in str(r) for r in post.metadata["related"])

    def test_idempotent(self, db, vault_path, enriched_capture):
        """Calling create_inbox_page twice returns same path, only one file exists."""
        path1 = create_inbox_page(
            capture_id=enriched_capture["id"],
            original_text=enriched_capture["original_text"],
            enriched_text=enriched_capture["enriched_text"],
            bucket=enriched_capture["bucket"],
            tags=enriched_capture["tags"],
            wikilinks=enriched_capture["wikilinks"],
            created_at=enriched_capture["created_at"],
            vault_path=vault_path,
        )
        path2 = create_inbox_page(
            capture_id=enriched_capture["id"],
            original_text=enriched_capture["original_text"],
            enriched_text=enriched_capture["enriched_text"],
            bucket=enriched_capture["bucket"],
            tags=enriched_capture["tags"],
            wikilinks=enriched_capture["wikilinks"],
            created_at=enriched_capture["created_at"],
            vault_path=vault_path,
        )
        assert path1 == path2
        # Only one file should exist
        inbox_files = list((vault_path / "inbox").glob("*.md"))
        assert len(inbox_files) == 1

    def test_escapes_special_yaml(self, db, vault_path):
        """Page with colons/quotes in text produces valid YAML frontmatter."""
        cid = save_capture("Text with: colons, 'quotes', and \"double quotes\"", conn=db)
        save_enrichment(
            capture_id=cid,
            bucket="Idea",
            enriched_text="Enriched text with special chars",
            tags=["special"],
            wikilinks=[],
            conn=db,
        )
        enrichment = get_enrichment(cid, conn=db)

        path = create_inbox_page(
            capture_id=cid,
            original_text=enrichment["original_text"],
            enriched_text=enrichment["enriched_text"],
            bucket=enrichment["bucket"],
            tags=json.loads(enrichment["tags"]) if isinstance(enrichment["tags"], str) else enrichment["tags"],
            wikilinks=json.loads(enrichment["wikilinks"]) if isinstance(enrichment["wikilinks"], str) else enrichment["wikilinks"],
            created_at=enrichment["created_at"],
            vault_path=vault_path,
        )
        # Verify it can be loaded back without error
        post = frontmatter.load(path)
        assert post.metadata is not None
        assert "colons" in post.metadata["title"]


class TestValidateVaultPath:
    """Tests for _validate_vault_path."""

    def test_prevents_traversal(self, vault_path):
        """_validate_vault_path raises ValueError when resolved path escapes vault root."""
        with pytest.raises(ValueError, match="traversal"):
            _validate_vault_path(vault_path / ".." / ".." / "etc" / "passwd", vault_path)

    def test_allows_valid_path(self, vault_path):
        """_validate_vault_path returns resolved path for valid paths within vault."""
        result = _validate_vault_path(vault_path / "inbox" / "test.md", vault_path)
        assert str(result).startswith(str(vault_path.resolve()))


class TestDailyRollup:
    """Tests for create_daily_rollup."""

    def test_creates_file(self, vault_path):
        """create_daily_rollup writes YYYY-MM-DD.md under vault_path/inbox/rollups/daily/."""
        target_date = date(2026, 5, 9)
        entries = [
            {"capture_id": "abc12345", "title": "First thought", "bucket": "Idea"},
        ]
        path = create_daily_rollup(
            target_date=target_date,
            entries=entries,
            vault_path=vault_path,
        )
        assert path.exists()
        assert "rollups" in str(path)
        assert "daily" in str(path)
        assert path.name == "2026-05-09.md"

    def test_contains_capture_links(self, vault_path):
        """Daily rollup body contains wikilinks to individual capture pages."""
        target_date = date(2026, 5, 9)
        entries = [
            {"capture_id": "abc12345", "title": "First thought", "bucket": "Idea"},
            {"capture_id": "def67890", "title": "Second thought", "bucket": "Task"},
        ]
        path = create_daily_rollup(
            target_date=target_date,
            entries=entries,
            vault_path=vault_path,
        )
        content = path.read_text()
        # Should contain wikilinks to individual capture pages
        assert "abc12345" in content or "quick-capture-abc1" in content

    def test_frontmatter_has_children(self, vault_path):
        """Rollup frontmatter has type=rollup, rollup_type=daily, children list."""
        target_date = date(2026, 5, 9)
        entries = [
            {"capture_id": "abc12345", "title": "First thought", "bucket": "Idea"},
        ]
        path = create_daily_rollup(
            target_date=target_date,
            entries=entries,
            vault_path=vault_path,
        )
        post = frontmatter.load(path)
        assert post.metadata["type"] == "rollup"
        assert post.metadata["rollup_type"] == "daily"
        assert len(post.metadata["children"]) == 1


class TestWeeklyRollup:
    """Tests for create_weekly_rollup."""

    def test_creates_file(self, vault_path):
        """create_weekly_rollup writes YYYY-WNN.md under vault_path/inbox/rollups/weekly/."""
        year = 2026
        week_num = 19
        daily_entries = [
            {"date": "2026-05-05", "title": "Daily Rollup — 2026-05-05", "children": []},
        ]
        path = create_weekly_rollup(
            year=year,
            week_num=week_num,
            daily_entries=daily_entries,
            vault_path=vault_path,
        )
        assert path.exists()
        assert "rollups" in str(path)
        assert "weekly" in str(path)
        assert "W19" in path.name

    def test_links_daily_rollups(self, vault_path):
        """Weekly rollup contains wikilinks to daily rollup pages."""
        year = 2026
        week_num = 19
        daily_entries = [
            {"date": "2026-05-05", "title": "Daily Rollup — 2026-05-05", "children": []},
            {"date": "2026-05-07", "title": "Daily Rollup — 2026-05-07", "children": []},
        ]
        path = create_weekly_rollup(
            year=year,
            week_num=week_num,
            daily_entries=daily_entries,
            vault_path=vault_path,
        )
        content = path.read_text()
        assert "2026-05-05" in content
        assert "2026-05-07" in content


class TestSyncAllToWiki:
    """Tests for sync_all_to_wiki."""

    def test_processes_unsynced(self, db, vault_path):
        """sync_all_to_wiki creates pages for unsynced enriched captures."""
        # Create and enrich a capture
        cid = save_capture("Test thought", conn=db)
        save_enrichment(
            capture_id=cid,
            bucket="Idea",
            enriched_text="Expanded thought",
            tags=["test"],
            wikilinks=["[[Test]]"],
            conn=db,
        )
        count = sync_all_to_wiki(conn=db, vault_path=vault_path)
        assert count == 1
        # Verify file was created
        inbox_files = list((vault_path / "inbox").glob("*.md"))
        assert len(inbox_files) == 1

    def test_skips_already_synced(self, db, vault_path):
        """Calling sync_all_to_wiki twice only creates pages once (idempotent)."""
        cid = save_capture("Sync once", conn=db)
        save_enrichment(
            capture_id=cid,
            bucket="Task",
            enriched_text="Done",
            tags=["test"],
            wikilinks=[],
            conn=db,
        )
        count1 = sync_all_to_wiki(conn=db, vault_path=vault_path)
        assert count1 == 1
        count2 = sync_all_to_wiki(conn=db, vault_path=vault_path)
        assert count2 == 0


class TestSyncCaptureToWikiKarakeep:
    """Tests for Karakeep dispatch integration in sync_capture_to_wiki."""

    @patch("quick_capture.karakeep.KARAKEEP_API_KEY", "kk_test_key")
    @patch("quick_capture.karakeep.httpx.post")
    def test_dispatches_reference_to_karakeep(self, mock_post, db, vault_path):
        """Reference-classified captures are dispatched to Karakeep after wiki sync."""
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm1"}, raise_for_status=MagicMock()
        )
        cid = save_capture("Read https://example.com/article", conn=db)
        save_enrichment(
            capture_id=cid,
            bucket="Reference",
            enriched_text="Great article about Python",
            tags=["python", "reference"],
            wikilinks=[],
            conn=db,
        )
        result = sync_capture_to_wiki(capture_id=cid, conn=db, vault_path=vault_path)
        assert result is not None
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["title"] == "Read https://example.com/article"
        assert call_kwargs["json"]["note"] == "Great article about Python"

    def test_skips_karakeep_for_non_reference(self, db, vault_path):
        """Non-Reference captures are NOT dispatched to Karakeep."""
        cid = save_capture("A brilliant idea", conn=db)
        save_enrichment(
            capture_id=cid,
            bucket="Idea",
            enriched_text="Expanded idea",
            tags=["idea"],
            wikilinks=["[[Ideas]]"],
            conn=db,
        )
        with patch("quick_capture.karakeep.sync_reference_to_karakeep") as mock_kk:
            result = sync_capture_to_wiki(capture_id=cid, conn=db, vault_path=vault_path)
        assert result is not None
        mock_kk.assert_not_called()

    @patch("quick_capture.karakeep.KARAKEEP_API_KEY", "kk_test_key")
    @patch("quick_capture.karakeep.httpx.post")
    def test_sync_log_records_karakeep_target(self, mock_post, db, vault_path):
        """After Karakeep dispatch, sync_log records 'karakeep' as target."""
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm2"}, raise_for_status=MagicMock()
        )
        cid = save_capture("Check https://example.com", conn=db)
        save_enrichment(
            capture_id=cid,
            bucket="Reference",
            enriched_text="Notes on the link",
            tags=[],
            wikilinks=[],
            conn=db,
        )
        sync_capture_to_wiki(capture_id=cid, conn=db, vault_path=vault_path)
        assert is_synced(cid, "karakeep", conn=db) is True
        assert is_synced(cid, "wiki", conn=db) is True

    @patch("quick_capture.karakeep.KARAKEEP_API_KEY", "kk_test_key")
    @patch("quick_capture.karakeep.httpx.post")
    def test_wiki_sync_continues_on_karakeep_failure(self, mock_post, db, vault_path):
        """Karakeep failures do NOT prevent wiki sync success."""
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        cid = save_capture("Reference https://example.com", conn=db)
        save_enrichment(
            capture_id=cid,
            bucket="Reference",
            enriched_text="Ref notes",
            tags=[],
            wikilinks=[],
            conn=db,
        )
        result = sync_capture_to_wiki(capture_id=cid, conn=db, vault_path=vault_path)
        assert result is not None
        assert is_synced(cid, "wiki", conn=db) is True
        assert is_synced(cid, "karakeep", conn=db) is False
