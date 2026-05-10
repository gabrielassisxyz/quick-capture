"""Shared test fixtures for Quick Capture tests."""

import json

import pytest

from quick_capture.db import get_enrichment, init_captures_db, save_capture, save_enrichment


@pytest.fixture
def db():
    """Provide a fresh in-memory database for each test."""
    conn = init_captures_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def sample_capture(db):
    """Insert a sample capture and return its data."""
    capture_id = save_capture("Test thought", conn=db)
    return {"id": capture_id, "original_text": "Test thought"}


@pytest.fixture
def vault_path(tmp_path):
    """Provide a temporary Obsidian vault directory for each test."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    return tmp_path


@pytest.fixture
def enriched_capture(db):
    """Insert a capture with enrichment and return its data."""
    capture_id = save_capture("Test thought about AI", conn=db)
    save_enrichment(
        capture_id=capture_id,
        bucket="Idea",
        enriched_text="AI is transforming how we think",
        tags=["ai", "ideas"],
        wikilinks=["[[Artificial Intelligence]]"],
        conn=db,
    )
    enrichment = get_enrichment(capture_id, conn=db)
    return {
        "id": capture_id,
        "original_text": "Test thought about AI",
        "bucket": enrichment["bucket"],
        "enriched_text": enrichment["enriched_text"],
        "tags": json.loads(enrichment["tags"]) if isinstance(enrichment["tags"], str) else enrichment["tags"],
        "wikilinks": json.loads(enrichment["wikilinks"]) if isinstance(enrichment["wikilinks"], str) else enrichment["wikilinks"],
        "created_at": enrichment["created_at"],
    }
