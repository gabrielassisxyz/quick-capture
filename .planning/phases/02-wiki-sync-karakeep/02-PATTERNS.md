# Phase 2: Wiki Sync & Karakeep - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 7
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/quick_capture/sync.py` | service | file-I/O | `src/quick_capture/db.py` | exact |
| `src/quick_capture/karakeep.py` | service | request-response | `src/quick_capture/enrich.py` | exact |
| `src/quick_capture/db.py` (modify) | model | CRUD | `src/quick_capture/db.py` (self — add table) | exact |
| `tests/test_sync.py` | test | file-I/O | `tests/test_db.py` | exact |
| `tests/test_karakeep.py` | test | request-response | `tests/test_enrich.py` | exact |
| `tests/conftest.py` (modify) | config | — | `tests/conftest.py` (self — add fixtures) | exact |
| `pyproject.toml` (modify) | config | — | `pyproject.toml` (self — add deps) | exact |

## Pattern Assignments

### `src/quick_capture/sync.py` (service, file-I/O)

**Analog:** `src/quick_capture/db.py`

sync.py writes structured data to the filesystem (Obsidian vault) instead of SQLite, but follows the same organizing principles: idempotency via existence checks, connection-accepting pattern for testability, and graceful error handling.

**Imports pattern** (adapted from db.py lines 1-8):
```python
"""Wiki sync — create inbox pages, daily rollups, and weekly rollups."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

import frontmatter
```

**Idempotency pattern — check before write** (adapted from db.py's connection-accepting pattern, lines 62-88):
```python
# db.py pattern: conn parameter is optional, creates default if not provided
# sync.py follows the same pattern: vault_path parameter is optional

VAULT_PATH = Path.home() / "Documents" / "obsidian" / "Akademia" / "wiki"


def create_inbox_page(
    capture_id: str,
    original_text: str,
    enriched_text: str,
    bucket: str,
    tags: list[str],
    wikilinks: list[str],
    created_at: str,
    vault_path: Path | None = None,
) -> Path:
    """Create an Obsidian wiki page for an enriched capture.

    Idempotent: if a page with the same capture_id already exists, returns its path.
    Uses capture_id[:8] in filename for deterministic deduplication.
    """
    vault = vault_path or VAULT_PATH
    page_date = date.fromisoformat(created_at[:10])
    short_id = capture_id[:8]
    filename = f"{page_date.isoformat()}-quick-capture-{short_id}.md"
    page_path = vault / "inbox" / filename

    # Idempotency: check frontmatter capture_id
    if page_path.exists():
        existing = frontmatter.load(page_path)
        if existing.metadata.get("capture_id") == capture_id:
            return page_path  # Already synced — no-op

    # Build page content + frontmatter
    content = f"# {original_text[:80]}\n\n{enriched_text}\n"
    if wikilinks:
        content += "\n## Related\n\n"
        for wl in wikilinks:
            content += f"- [[{wl}]]\n"

    post = frontmatter.Post(
        content=content,
        metadata={
            "type": "inbox",
            "title": original_text[:80],
            "source": "inbox",
            "capture_id": capture_id,
            "bucket": bucket,
            "created": page_date.isoformat(),
            "updated": page_date.isoformat(),
            "tags": tags + ["inbox", "quick-capture", bucket.lower()],
            "status": "current",
            "related": [f"[[{wl}]]" for wl in wikilinks],
        },
    )

    # Atomic write: create dir, write to temp, rename
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(frontmatter.dumps(post))
    return page_path
```

**Atomic file write pattern** (from RESEARCH.md Pitfall #2, applies to rollups):
```python
# For rollups (write-to-temp + rename for crash safety)
import os
import tempfile

def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically using temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp_path, path)  # Atomic on same filesystem
    except BaseException:
        # Clean up temp file on any error
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

**Query captures for sync** (adapted from db.py list_captures, lines 148-181):
```python
def get_unsynced_captures(
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Get enriched captures that haven't been synced to wiki yet."""
    c = conn or sqlite3.connect(str(NEXUS_DB))
    c.row_factory = sqlite3.Row
    try:
        rows = c.execute(
            """
            SELECT c.*, e.bucket, e.enriched_text, e.tags, e.wikilinks
            FROM captures c
            JOIN capture_enrichments e ON c.id = e.capture_id
            LEFT JOIN sync_log sl ON c.id = sl.capture_id AND sl.target = 'wiki'
            WHERE sl.id IS NULL AND c.status = 'enriched'
            ORDER BY c.created_at
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        if conn is None:
            c.close()
```

**Note on sync function signature — the conn-accepting pattern** (from db.py lines 77-88):
```python
# db.py pattern: every function accepts conn=None and creates a default connection
# sync.py functions should follow the same pattern with vault_path=None
# For DB queries within sync, also accept conn=None
```

**Error handling — graceful degradation** (adapted from enrich.py lines 127-150):
```python
# enrich.py pattern: on failure, reset state and raise
# sync.py should log warnings and continue, not crash — wiki sync failure
# should not prevent other captures from being synced
import logging

logger = logging.getLogger(__name__)

def sync_capture_to_wiki(capture_id: str, conn=None, vault_path=None) -> Path | None:
    """Sync a single capture to wiki. Returns path or None on failure."""
    try:
        capture = get_capture(capture_id, conn=conn)
        enrichment = get_enrichment(capture_id, conn=conn)
        # ... build page ...
        path = create_inbox_page(...)
        log_sync(capture_id, "wiki", conn=conn)
        return path
    except Exception:
        logger.exception("Failed to sync capture %s to wiki", capture_id)
        return None  # Graceful degradation, not crash
```

---

### `src/quick_capture/karakeep.py` (service, request-response)

**Analog:** `src/quick_capture/enrich.py`

Both make outbound calls to external services (enrich.py → subprocess, karakeep.py → HTTP). The pattern: validate inputs, call external service, handle errors with graceful degradation.

**Imports pattern** (adapted from enrich.py lines 1-11):
```python
"""Karakeep HTTP client — send Reference-classified captures as bookmarks."""

from __future__ import annotations

import os
from typing import Any

import httpx

KARAKEEP_API_URL = os.getenv("KARAKEEP_API_URL", "https://karakeep.assislab.duckdns.org")
KARAKEEP_API_KEY = os.getenv("KARAKEEP_API_KEY", "")

# URL detection regex for auto-detecting link vs text bookmark type
import re
_URL_PATTERN = re.compile(r"https?://\S+")
```

**Core HTTP client pattern** (adapted from enrich.py's subprocess pattern, lines 106-161):
```python
# enrich.py pattern: validate → call external service → handle errors
# karakeep.py follows: validate config → call API → handle HTTP errors

def dispatch_reference_to_karakeep(
    text: str,
    enriched_text: str,
    tags: list[str] | None = None,
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Send a Reference-classified capture to Karakeep as a text bookmark.

    Auto-detects URLs in text: uses type='link' if URL found, else type='text'.
    Returns the API response dict on success.
    Raises ValueError if KARAKEEP_API_KEY is not configured.
    Raises httpx.HTTPStatusError on API failure.
    """
    url = (api_url or KARAKEEP_API_URL).rstrip("/")
    key = api_key or KARAKEEP_API_KEY

    if not key:
        msg = "KARAKEEP_API_KEY not configured"
        raise ValueError(msg)

    # Auto-detect URLs for link vs text bookmark type
    url_match = _URL_PATTERN.search(text)
    bookmark_type = "link" if url_match else "text"

    payload: dict[str, Any] = {
        "type": bookmark_type,
        "title": text[:200],
        "note": enriched_text,  # Intent retrieval notes
        "source": "api",
    }
    if bookmark_type == "link":
        payload["url"] = url_match.group(0)
    else:
        payload["text"] = text

    if tags:
        payload["tags"] = tags

    response = httpx.post(
        f"{url}/api/v1/bookmarks",
        headers={"Authorization": f"Bearer {key}"},
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()
```

**Error handling — graceful degradation** (adapted from enrich.py lines 136-149):
```python
# enrich.py pattern: on subprocess failure → reset status and raise RuntimeError
# karakeep.py pattern: on HTTP failure → log warning, don't crash the sync pipeline
# The caller (sync.py) should catch httpx errors and continue

def sync_reference_to_karakeep(
    capture_id: str,
    enrichment: dict[str, Any],
    conn: sqlite3.Connection | None = None,
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any] | None:
    """Sync a Reference capture to Karakeep. Returns response or None on failure."""
    try:
        result = dispatch_reference_to_karakeep(
            text=enrichment["original_text"],
            enriched_text=enrichment["enriched_text"],
            tags=json.loads(enrichment["tags"]) if isinstance(enrichment["tags"], str) else enrichment["tags"],
            api_url=api_url,
            api_key=api_key,
        )
        log_sync(capture_id, "karakeep", conn=conn)
        return result
    except (httpx.HTTPStatusError, httpx.ConnectError, ValueError) as e:
        logger.warning("Karakeep sync failed for capture %s: %s", capture_id, e)
        return None  # Graceful degradation
```

**Timeout pattern** (from enrich.py line 128):
```python
# enrich.py: timeout=120 for subprocess (LLM calls are slow)
# karakeep.py: timeout=30 for httpx (API calls should be fast)
```

---

### `src/quick_capture/db.py` (modify — add sync_log table) (model, CRUD)

**Analog:** `src/quick_capture/db.py` (self — existing pattern)

Add a `sync_log` table following the exact same pattern used for `captures` and `capture_enrichments`.

**New table pattern** (follows db.py lines 33-56):
```python
# Add to init_captures_db() executescript, after existing CREATE INDEX statements:
"""
CREATE TABLE IF NOT EXISTS sync_log (
    id TEXT PRIMARY KEY,
    capture_id TEXT NOT NULL,
    target TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sync_log_capture ON sync_log(capture_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_target ON sync_log(target);
"""
```

**New CRUD function — log_sync** (follows save_enrichment pattern, db.py lines 209-253):
```python
def log_sync(
    capture_id: str,
    target: str,  # "wiki" or "karakeep"
    conn: sqlite3.Connection | None = None,
) -> str:
    """Record that a capture has been synced to a target. Returns sync log ID."""
    sync_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    c = conn or sqlite3.connect(str(NEXUS_DB))
    try:
        c.execute(
            "INSERT INTO sync_log (id, capture_id, target, synced_at) VALUES (?, ?, ?, ?)",
            (sync_id, capture_id, target, now),
        )
        c.commit()
    finally:
        if conn is None:
            c.close()
    return sync_id
```

**New query function — is_synced** (follows get_enrichment pattern, db.py lines 184-206):
```python
def is_synced(
    capture_id: str,
    target: str,
    conn: sqlite3.Connection | None = None,
) -> bool:
    """Check if a capture has been synced to a specific target."""
    c = conn or sqlite3.connect(str(NEXUS_DB))
    try:
        row = c.execute(
            "SELECT id FROM sync_log WHERE capture_id = ? AND target = ?",
            (capture_id, target),
        ).fetchone()
        return row is not None
    finally:
        if conn is None:
            c.close()
```

**Critical constraint** (from db.py docstring line 17-18):
```python
# "Only adds new tables — never drops or alters existing ones."
# Add CREATE TABLE IF NOT EXISTS sync_log AFTER the existing tables/indexes
# Do NOT modify the captures or capture_enrichments table definitions
```

---

### `tests/test_sync.py` (test, file-I/O)

**Analog:** `tests/test_db.py`

Same pytest class-based structure, in-memory DB fixtures from conftest.py, plus filesystem mocking for vault writes.

**Test fixture pattern** (from conftest.py lines 1-20):
```python
"""Tests for wiki sync module."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from quick_capture.db import (
    get_enrichment,
    init_captures_db,
    save_capture,
    save_enrichment,
)
from quick_capture.sync import (
    create_daily_rollup,
    create_inbox_page,
    create_weekly_rollup,
    get_unsynced_captures,
    sync_capture_to_wiki,
)


@pytest.fixture
def vault_path(tmp_path):
    """Provide a temporary vault directory for each test."""
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
    return {
        "id": capture_id,
        "original_text": "Test thought about AI",
        "bucket": "Idea",
        "enriched_text": "AI is transforming how we think",
        "tags": ["ai", "ideas"],
        "wikilinks": ["[[Artificial Intelligence]]"],
    }
```

**Test class pattern** (from test_db.py lines 16-48):
```python
class TestCreateInboxPage:
    """Tests for create_inbox_page."""

    def test_creates_markdown_file(self, enriched_capture, vault_path, db):
        """create_inbox_page writes a .md file to vault/inbox/."""
        enrichment = get_enrichment(enriched_capture["id"], conn=db)
        path = create_inbox_page(
            capture_id=enriched_capture["id"],
            original_text=enriched_capture["original_text"],
            enriched_text=enrichment["enriched_text"],
            bucket=enrichment["bucket"],
            tags=json.loads(enrichment["tags"]),
            wikilinks=json.loads(enrichment["wikilinks"]),
            created_at=enrichment["created_at"],
            vault_path=vault_path,
        )
        assert path.exists()
        assert path.suffix == ".md"
        assert "inbox" in str(path)

    def test_page_has_correct_frontmatter(self, enriched_capture, vault_path, db):
        """Frontmatter includes type: inbox, source: inbox, capture_id."""
        import frontmatter
        # ... create page, load with frontmatter.load(), assert metadata ...

    def test_idempotent_rerun_returns_existing_path(self, enriched_capture, vault_path, db):
        """Running create_inbox_page twice returns same path, no duplicate files."""
        # ... create page twice, assert same path, assert only one file ...
```

**Rollup test pattern** (follows test_db.py structure):
```python
class TestDailyRollup:
    """Tests for create_daily_rollup."""

    def test_creates_rollup_file(self, enriched_capture, vault_path, db):
        """Daily rollup file exists with correct date-based filename."""
        # ...

    def test_rollup_contains_capture_links(self, enriched_capture, vault_path, db):
        """Rollup body contains wikilinks to individual capture pages."""
        # ...

    def test_rollup_frontmatter_has_children(self, enriched_capture, vault_path, db):
        """Rollup frontmatter lists children with capture_id and page reference."""
        # ...
```

---

### `tests/test_karakeep.py` (test, request-response)

**Analog:** `tests/test_enrich.py`

Same pattern: mock external HTTP calls with `unittest.mock.patch`, assert correct payloads, test error handling.

**Test pattern** (from test_enrich.py lines 109-213):
```python
"""Tests for Karakeep HTTP client."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from quick_capture.karakeep import dispatch_reference_to_karakeep


class TestDispatchReferenceToKarakeep:
    """Tests for dispatch_reference_to_karakeep."""

    def test_sends_text_bookmark_for_text_capture(self):
        """Pure text reference creates type=text bookmark."""
        with patch("quick_capture.karakeep.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"id": "bk-123"}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = dispatch_reference_to_karakeep(
                text="Interesting thought about Rust",
                enriched_text="Developed thought about Rust",
                tags=["programming"],
                api_key="test-key",
            )

            call_args = mock_post.call_args
            assert call_args[1]["json"]["type"] == "text"
            assert call_args[1]["json"]["text"] == "Interesting thought about Rust"
            assert call_args[1]["json"]["note"] == "Developed thought about Rust"

    def test_sends_link_bookmark_for_url_capture(self):
        """Reference containing a URL creates type=link bookmark."""
        with patch("quick_capture.karakeep.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"id": "bk-456"}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = dispatch_reference_to_karakeep(
                text="Check https://example.com/article",
                enriched_text="Key insights from the article",
                api_key="test-key",
            )

            call_args = mock_post.call_args
            assert call_args[1]["json"]["type"] == "link"
            assert "url" in call_args[1]["json"]

    def test_raises_value_error_without_api_key(self):
        """Missing API key raises ValueError."""
        with pytest.raises(ValueError, match="KARAKEEP_API_KEY"):
            dispatch_reference_to_karakeep(
                text="Test", enriched_text="Test", api_key=""
            )

    def test_raises_http_status_error_on_api_failure(self):
        """HTTP error from Karakeep raises httpx.HTTPStatusError."""
        with patch("quick_capture.karakeep.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401", request=MagicMock(), response=MagicMock()
            )
            mock_post.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                dispatch_reference_to_karakeep(
                    text="Test", enriched_text="Test", api_key="bad-key"
                )
```

**Mock external I/O pattern** (from test_enrich.py lines 124-133 — the mock_result pattern):
```python
# test_enrich.py pattern: create MagicMock, set returncode/stdout, patch subprocess.run
# test_karakeep.py follows: create MagicMock, set json return value, patch httpx.post

mock_response = MagicMock()
mock_response.json.return_value = {"id": "bk-123"}
mock_response.raise_for_status = MagicMock()
mock_post.return_value = mock_response
```

---

### `tests/conftest.py` (modify — add vault and enriched fixtures) (config, —)

**Analog:** `tests/conftest.py` (self — extend)

Add vault_path and enriched_capture fixtures alongside existing db and sample_capture fixtures.

**New fixtures to add** (following existing conftest.py pattern, lines 1-20):
```python
# Add to existing conftest.py — do NOT remove existing fixtures

@pytest.fixture
def vault_path(tmp_path):
    """Provide a temporary Obsidian vault directory for each test."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    rollups_daily = tmp_path / "inbox" / "rollups" / "daily"
    rollups_daily.mkdir(parents=True)
    rollups_weekly = tmp_path / "inbox" / "rollups" / "weekly"
    rollups_weekly.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def enriched_capture(db):
    """Insert a capture with enrichment and return its data."""
    from quick_capture.db import save_capture, save_enrichment, get_enrichment

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
```

---

### `pyproject.toml` (modify — add dependencies) (config, —)

**Analog:** `pyproject.toml` (self — extend)

Add `python-frontmatter` and `httpx` to the dependencies list.

**Pattern** (from pyproject.toml lines 22-25):
```toml
dependencies = [
    "prompt-toolkit>=3.0.52",
    "rich>=13.0.0",
    "python-frontmatter>=1.1.0",
    "httpx>=0.28.1",
]
```

**Note:** PyYAML is a transitive dependency of python-frontmatter, no need to add explicitly.

---

## Shared Patterns

### SQLite Connection Management

**Source:** `src/quick_capture/db.py` lines 15-58
**Apply to:** All new DB functions in db.py (log_sync, is_synced, get_unsynced_captures)

```python
# Every function accepts conn=None, creates default connection if not provided
# Every function uses try/finally to close self-created connections
# Every function sets row_factory = sqlite3.Row

def some_function(conn: sqlite3.Connection | None = None):
    c = conn or sqlite3.connect(str(NEXUS_DB))
    c.row_factory = sqlite3.Row
    try:
        # ... DB operations ...
    finally:
        if conn is None:
            c.close()
```

### Parameterized Queries (Security)

**Source:** `src/quick_capture/db.py` lines 80-82, 96-98, 127-138
**Apply to:** All new DB functions (log_sync, is_synced, get_unsynced_captures)

```python
# ALWAYS use ? placeholders, NEVER f-string interpolation
c.execute("INSERT INTO sync_log (id, capture_id, target, synced_at) VALUES (?, ?, ?, ?)", (sync_id, capture_id, target, now))
c.execute("SELECT id FROM sync_log WHERE capture_id = ? AND target = ?", (capture_id, target))
```

### Vault Path Configuration

**Source:** `src/quick_capture/db.py` line 10 (NEXUS_DB pattern)
**Apply to:** sync.py, karakeep.py

```python
# db.py pattern: module-level default constant, overridable in function params
VAULT_PATH = Path.home() / "Documents" / "obsidian" / "Akademia" / "wiki"
KARAKEEP_API_URL = os.getenv("KARAKEEP_API_URL", "https://karakeep.assislab.duckdns.org")
KARAKEEP_API_KEY = os.getenv("KARAKEEP_API_KEY", "")
```

### Graceful Error Handling — Don't Crash on External Failure

**Source:** `src/quick_capture/enrich.py` lines 127-150
**Apply to:** sync.py (wiki write failures), karakeep.py (API failures)

```python
# enrich.py resets status on failure — but sync.py should be more forgiving
# Wiki sync: log warning, continue to next capture
# Karakeep: log warning, continue with wiki-only sync

import logging
logger = logging.getLogger(__name__)

# Pattern: try/except with logging, return None on failure
try:
    result = external_call(...)
except ExternalError as e:
    logger.warning("External call failed: %s", e)
    return None  # Graceful degradation
```

### Input Validation — Size Limits

**Source:** `src/quick_capture/db.py` lines 66-71
**Apply to:** sync.py (frontmatter content validation), karakeep.py (API payload size)

```python
# db.py validates capture text size
MAX_CAPTURE_SIZE = 10_000

# sync.py should validate frontmatter doesn't produce excessively large files
# karakeep.py should truncate title to 200 chars (already in RESEARCH.md code example)
```

### Test Fixture Pattern — In-Memory DB + tmp_path

**Source:** `tests/conftest.py` lines 1-20, `tests/test_db.py` lines 16-19
**Apply to:** test_sync.py, test_karakeep.py

```python
# Existing pattern: db fixture provides in-memory SQLite
@pytest.fixture
def db():
    conn = init_captures_db(":memory:")
    yield conn
    conn.close()

# New pattern: vault_path fixture provides temp directory
@pytest.fixture
def vault_path(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    return tmp_path

# Combined pattern: use both db and vault_path in sync tests
def test_sync_creates_page(self, db, vault_path, enriched_capture):
    # ... test with real in-memory DB and real temp filesystem ...
```

### Atomic File Writes — Prevent Corruption

**Source:** RESEARCH.md Pitfall #2 (race condition on rollups)
**Apply to:** sync.py (all file writes to vault)

```python
# Write to temp file, then atomic rename
import os
import tempfile

def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically using temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp_path, path)  # Atomic on same filesystem
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

### Path Traversal Prevention

**Source:** `src/quick_capture/db.py` line 27 (path resolve pattern)
**Apply to:** sync.py (validate vault paths stay within allowed directory)

```python
# db.py pattern: resolve paths to prevent traversal
path = str(Path(path).resolve()) if path != ":memory:" else path

# sync.py should validate resolved paths stay within vault
def _validate_vault_path(page_path: Path, vault_path: Path) -> Path:
    """Ensure page_path resolves to within the vault directory."""
    resolved = page_path.resolve()
    vault_root = vault_path.resolve()
    if not str(resolved).startswith(str(vault_root)):
        msg = f"Path traversal detected: {resolved} is outside vault {vault_root}"
        raise ValueError(msg)
    return resolved
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | — | — | All files have close analogs in the existing codebase |

## Metadata

**Analog search scope:** `src/quick_capture/`, `tests/`
**Files scanned:** 9 (`db.py`, `enrich.py`, `sync.py`, `models.py`, `cli.py`, `conftest.py`, `test_db.py`, `test_enrich.py`, `pyproject.toml`)
**Pattern extraction date:** 2026-05-09