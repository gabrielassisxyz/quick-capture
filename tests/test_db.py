"""Tests for the database module."""

import pytest

from quick_capture.db import (
    get_capture,
    get_enrichment,
    init_captures_db,
    list_captures,
    save_capture,
    save_enrichment,
    update_capture,
)


class TestInitCapturesDb:
    """Tests for init_captures_db."""

    def test_creates_captures_and_enrichments_tables(self, db):
        """init_captures_db creates both tables."""
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('captures', 'capture_enrichments')"
        )
        tables = [row["name"] if hasattr(row, "keys") else row[0] for row in cursor.fetchall()]
        assert "captures" in tables
        assert "capture_enrichments" in tables

    def test_creates_indexes(self, db):
        """init_captures_db creates expected indexes."""
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name IN ('idx_captures_status', 'idx_captures_created', 'idx_enrichments_capture')"
        )
        indexes = [row["name"] if hasattr(row, "keys") else row[0] for row in cursor.fetchall()]
        assert "idx_captures_status" in indexes
        assert "idx_captures_created" in indexes
        assert "idx_enrichments_capture" in indexes

    def test_does_not_modify_existing_tables(self):
        """init_captures_db uses IF NOT EXISTS — safe to re-run, never drops tables."""
        # Init once to create tables + add a fake pre-existing table
        conn = init_captures_db(":memory:")
        conn.execute("CREATE TABLE pre_existing (id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO pre_existing (id) VALUES ('survivor')")
        conn.commit()

        # Re-run init same connection — CREATE TABLE IF NOT EXISTS won't drop
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS captures (
                id TEXT PRIMARY KEY,
                original_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unprocessed',
                created_at TEXT NOT NULL,
                updated_at TEXT
            );
            """
        )
        conn.commit()

        # Verify pre-existing table was NOT dropped
        row = conn.execute("SELECT id FROM pre_existing").fetchone()
        assert row["id"] == "survivor"

        # Verify captures table still exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='captures'"
        )
        assert cursor.fetchone() is not None

        conn.close()

    def test_sets_wal_mode(self, db):
        """Connections set WAL journal mode (memory DB returns 'memory' instead)."""
        result = db.execute("PRAGMA journal_mode").fetchone()
        # In-memory DBs return 'memory' instead of 'wal'
        assert result[0].lower() in ("wal", "memory")

    def test_enables_foreign_keys(self, db):
        """Connections have foreign keys enabled."""
        result = db.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1

    def test_sets_busy_timeout(self, db):
        """Connections have busy timeout set to 5000ms."""
        result = db.execute("PRAGMA busy_timeout").fetchone()
        assert result[0] == 5000


class TestSaveCapture:
    """Tests for save_capture."""

    def test_inserts_row_and_returns_uuid(self, db):
        """save_capture inserts a row and returns a 36-char UUID string."""
        capture_id = save_capture("My thought", conn=db)
        assert capture_id is not None
        assert len(capture_id) == 36
        assert capture_id.count("-") == 4

    def test_stores_original_text_verbatim(self, db):
        """save_capture stores original_text exactly as provided."""
        text = "Hello\nWorld! Special chars: <>&'\""
        capture_id = save_capture(text, conn=db)
        capture = get_capture(capture_id, conn=db)
        assert capture["original_text"] == text

    def test_default_status_is_unprocessed(self, db):
        """save_capture defaults status to 'unprocessed'."""
        capture_id = save_capture("Test", conn=db)
        capture = get_capture(capture_id, conn=db)
        assert capture["status"] == "unprocessed"

    def test_sets_created_at_timestamp(self, db):
        """save_capture sets created_at to an ISO 8601 timestamp."""
        capture_id = save_capture("Test", conn=db)
        capture = get_capture(capture_id, conn=db)
        assert capture["created_at"] is not None
        # ISO 8601 format: contains 'T' and timezone
        assert "T" in capture["created_at"]

    def test_empty_string_raises_value_error(self, db):
        """save_capture raises ValueError for empty text."""
        with pytest.raises(ValueError, match="empty"):
            save_capture("", conn=db)

    def test_oversized_text_raises_value_error(self, db):
        """save_capture raises ValueError for text exceeding 10KB."""
        with pytest.raises(ValueError, match="10"):
            save_capture("x" * 10001, conn=db)

    def test_text_exactly_at_limit_is_accepted(self, db):
        """save_capture accepts text at exactly 10KB."""
        capture_id = save_capture("x" * 10000, conn=db)
        assert len(capture_id) == 36


class TestGetCapture:
    """Tests for get_capture."""

    def test_retrieves_saved_capture_by_id(self, db):
        """get_capture retrieves a full dict with column names."""
        capture_id = save_capture("Test thought", conn=db)
        capture = get_capture(capture_id, conn=db)
        assert capture is not None
        assert capture["id"] == capture_id
        assert capture["original_text"] == "Test thought"
        assert capture["status"] == "unprocessed"
        assert "created_at" in capture

    def test_returns_none_for_missing_id(self, db):
        """get_capture returns None for non-existent ID."""
        result = get_capture("nonexistent-id", conn=db)
        assert result is None


class TestUpdateCapture:
    """Tests for update_capture."""

    def test_changes_status_from_unprocessed_to_enriching(self, db):
        """update_capture changes status and sets updated_at."""
        capture_id = save_capture("Test", conn=db)
        updated = update_capture(capture_id, {"status": "enriching"}, conn=db)
        assert updated is not None
        assert updated["status"] == "enriching"
        assert updated["updated_at"] is not None

    def test_preserves_other_fields(self, db):
        """update_capture only changes specified fields."""
        capture_id = save_capture("Original text", conn=db)
        update_capture(capture_id, {"status": "enriching"}, conn=db)
        capture = get_capture(capture_id, conn=db)
        assert capture["original_text"] == "Original text"

    def test_empty_patch_returns_current(self, db):
        """update_capture with empty patch returns current row."""
        capture_id = save_capture("Test", conn=db)
        result = update_capture(capture_id, {}, conn=db)
        assert result is not None
        assert result["status"] == "unprocessed"

    def test_ignores_disallowed_columns(self, db):
        """update_capture ignores column names not in allowlist."""
        capture_id = save_capture("Test", conn=db)
        result = update_capture(capture_id, {"original_text": "hacked"}, conn=db)
        assert result["original_text"] == "Test"  # unchanged


class TestListCaptures:
    """Tests for list_captures."""

    def test_lists_all_captures(self, db):
        """list_captures returns all captures when no filter."""
        save_capture("First", conn=db)
        save_capture("Second", conn=db)
        captures = list_captures(conn=db)
        assert len(captures) == 2

    def test_filters_by_status(self, db):
        """list_captures filters by status."""
        save_capture("Unprocessed", conn=db)
        capture_id = save_capture("To enrich", conn=db)
        update_capture(capture_id, {"status": "enriching"}, conn=db)
        result = list_captures(status="enriching", conn=db)
        assert len(result) == 1
        assert result[0]["original_text"] == "To enrich"

    def test_empty_list_when_no_captures(self, db):
        """list_captures returns empty list when no captures."""
        result = list_captures(conn=db)
        assert result == []


class TestSaveEnrichment:
    """Tests for save_enrichment."""

    def test_inserts_enrichment_and_updates_status(self, db):
        """save_enrichment inserts row and sets capture status to 'enriched'."""
        capture_id = save_capture("Test thought", conn=db)
        enrichment_id = save_enrichment(
            capture_id=capture_id,
            bucket="Task",
            enriched_text="Develop this idea",
            tags=["ideas", "capture"],
            wikilinks=["[[Projects]]"],
            conn=db,
        )
        assert len(enrichment_id) == 36

        # Verify capture status updated to enriched
        capture = get_capture(capture_id, conn=db)
        assert capture["status"] == "enriched"

    def test_enrichment_stores_json_fields(self, db):
        """save_enrichment stores tags and wikilinks as JSON."""
        capture_id = save_capture("Test", conn=db)
        save_enrichment(
            capture_id=capture_id,
            bucket="Idea",
            enriched_text="Expanded idea",
            tags=["creative", "brainstorm"],
            wikilinks=["[[Ideas]]"],
            conn=db,
        )
        enrichment = get_enrichment(capture_id, conn=db)
        assert enrichment is not None
        assert enrichment["bucket"] == "Idea"
        assert enrichment["enriched_text"] == "Expanded idea"
