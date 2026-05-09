"""Shared test fixtures for Quick Capture tests."""

import sqlite3

import pytest

from quick_capture.db import init_captures_db, save_capture


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