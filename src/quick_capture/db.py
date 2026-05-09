"""SQLite module for captures and capture_enrichments tables in nexus.db."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

NEXUS_DB = Path.home() / "repositories" / "nexus" / "nexus.db"

MAX_CAPTURE_SIZE = 10_000  # 10KB limit per security threat model


def init_captures_db(db_path: str | None = None) -> sqlite3.Connection:
    """Initialize captures tables in nexus.db. Creates tables if not exist.

    Only adds new tables — never drops or alters existing ones.
    Sets WAL mode, foreign keys, and busy timeout for safe concurrent access.

    Args:
        db_path: Path to the database file, ":memory:" for in-memory,
                 or None to use the default NEXUS_DB path.
    """
    path = db_path or str(NEXUS_DB)
    # Resolve path to prevent path traversal (skip for in-memory DB)
    path = str(Path(path).resolve()) if path != ":memory:" else path
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS captures (
            id TEXT PRIMARY KEY,
            original_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'unprocessed',
            created_at TEXT NOT NULL,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS capture_enrichments (
            id TEXT PRIMARY KEY,
            capture_id TEXT NOT NULL,
            bucket TEXT NOT NULL,
            enriched_text TEXT NOT NULL,
            tags TEXT,
            wikilinks TEXT,
            opencode_session_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_captures_status ON captures(status);
        CREATE INDEX IF NOT EXISTS idx_captures_created ON captures(created_at);
        CREATE INDEX IF NOT EXISTS idx_enrichments_capture ON capture_enrichments(capture_id);
    """
    )
    conn.commit()
    return conn


def save_capture(text: str, conn: sqlite3.Connection | None = None) -> str:
    """Save a raw capture and return its ID.

    Validates text is not empty and under 10KB (DoS mitigation).
    """
    if not text or not text.strip():
        msg = "Capture text cannot be empty"
        raise ValueError(msg)
    if len(text) > MAX_CAPTURE_SIZE:
        msg = f"Capture text exceeds maximum size of {MAX_CAPTURE_SIZE} characters"
        raise ValueError(msg)

    capture_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    c = conn or sqlite3.connect(str(NEXUS_DB))
    c.row_factory = sqlite3.Row
    try:
        c.execute(
            "INSERT INTO captures (id, original_text, status, created_at) VALUES (?, ?, ?, ?)",
            (capture_id, text, "unprocessed", now),
        )
        c.commit()
    finally:
        if conn is None:
            c.close()
    return capture_id


def get_capture(capture_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    """Retrieve a capture by ID. Returns dict with column names as keys, or None."""
    c = conn or sqlite3.connect(str(NEXUS_DB))
    c.row_factory = sqlite3.Row
    try:
        row = c.execute(
            "SELECT * FROM captures WHERE id = ?",
            (capture_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        if conn is None:
            c.close()


def update_capture(
    capture_id: str, patch: dict[str, Any], conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    """Update capture fields from patch dict. Uses parameterized queries.

    Dynamically builds SET clause from patch keys. Sets updated_at to current UTC time.
    Returns the updated row as a dict, or None if not found.
    """
    if not patch:
        return get_capture(capture_id, conn=conn)

    now = datetime.now(tz=UTC).isoformat()
    patch["updated_at"] = now

    sets = []
    values: list[Any] = []
    for key, value in patch.items():
        # Allowlisted column names — prevent SQL injection via key names
        allowed_columns = {"status", "updated_at"}
        if key not in allowed_columns:
            continue
        sets.append(f"{key} = ?")
        values.append(value)
    values.append(capture_id)

    c = conn or sqlite3.connect(str(NEXUS_DB))
    c.row_factory = sqlite3.Row
    try:
        c.execute(
            f"UPDATE captures SET {', '.join(sets)} WHERE id = ?",  # noqa: S608
            values,
        )
        c.commit()
        result = get_capture(capture_id, conn=c)
    finally:
        if conn is None:
            c.close()
    return result


def list_captures(
    status: str | None = None,
    bucket: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """List all captures, optionally filtered by status and/or bucket.

    When bucket filter is given, JOINs capture_enrichments.
    """
    c = conn or sqlite3.connect(str(NEXUS_DB))
    c.row_factory = sqlite3.Row
    try:
        if bucket:
            query = (
                "SELECT c.* FROM captures c "
                "JOIN capture_enrichments e ON c.id = e.capture_id "
                "WHERE e.bucket = ?"
            )
            params: list[str] = [bucket]
            if status:
                query += " AND c.status = ?"
                params.append(status)
            rows = c.execute(query, params).fetchall()
        elif status:
            rows = c.execute(
                "SELECT * FROM captures WHERE status = ?",
                (status,),
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM captures").fetchall()
        return [dict(row) for row in rows]
    finally:
        if conn is None:
            c.close()


def get_enrichment(
    capture_id: str, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    """Get enrichment for a capture. JOINs captures and capture_enrichments."""
    c = conn or sqlite3.connect(str(NEXUS_DB))
    c.row_factory = sqlite3.Row
    try:
        row = c.execute(
            """
            SELECT c.*, e.bucket, e.enriched_text, e.tags, e.wikilinks,
                   e.opencode_session_id, e.created_at as enrichment_created_at
            FROM captures c
            JOIN capture_enrichments e ON c.id = e.capture_id
            WHERE c.id = ?
            """,
            (capture_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        if conn is None:
            c.close()


def save_enrichment(  # noqa: PLR0913
    capture_id: str,
    bucket: str,
    enriched_text: str,
    tags: list[str],
    wikilinks: list[str],
    opencode_session_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> str:
    """Insert enrichment row and update capture status to 'enriched'.

    Tags and wikilinks are stored as JSON text. Returns enrichment ID.
    """
    enrichment_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    c = conn or sqlite3.connect(str(NEXUS_DB))
    try:
        c.execute(
            """
            INSERT INTO capture_enrichments
               (id, capture_id, bucket, enriched_text, tags, wikilinks,
                opencode_session_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                enrichment_id,
                capture_id,
                bucket,
                enriched_text,
                json.dumps(tags),
                json.dumps(wikilinks),
                opencode_session_id,
                now,
            ),
        )
        c.execute(
            "UPDATE captures SET status = ?, updated_at = ? WHERE id = ?",
            ("enriched", now, capture_id),
        )
        c.commit()
    finally:
        if conn is None:
            c.close()
    return enrichment_id
