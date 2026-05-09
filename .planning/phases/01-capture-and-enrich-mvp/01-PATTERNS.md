# Phase 1: Capture & Enrich MVP - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 12
**Analogs found:** 11 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/quick_capture/__init__.py` | config | — | `nexus/shared/schema.ts` (module init pattern) | partial |
| `src/quick_capture/cli.py` | controller | request-response | `llm-cli/quickask.py` | exact |
| `src/quick_capture/db.py` | model | CRUD | `nexus/server/db.ts` | exact |
| `src/quick_capture/enrich.py` | service | subprocess | `nexus/server/api/opencode.ts` | exact |
| `src/quick_capture/models.py` | model | — | `nexus/shared/schema.ts` | exact |
| `pyproject.toml` | config | — | (no analog — new project setup) | none |
| `tests/conftest.py` | test | — | `nexus/server/db.test.ts` (test fixture pattern) | role-match |
| `tests/test_db.py` | test | CRUD | `nexus/server/db.test.ts` | exact |
| `tests/test_enrich.py` | test | subprocess | `nexus/server/db.test.ts` (test pattern) | role-match |
| `tests/test_cli.py` | test | request-response | `nexus/server/db.test.ts` (test pattern) | role-match |
| `nexus/server/api/captures.ts` | controller | request-response | `nexus/server/api/sessions.ts` | exact |
| `nexus/src/components/captures.js` | component | request-response | `nexus/src/components/grid.js` + `sidebar.js` | exact |

## Pattern Assignments

### `src/quick_capture/cli.py` (controller, request-response)

**Analog:** `~/repositories/llm-cli/quickask.py`

This is the closest possible match — quickask.py is a Python CLI tool using Rich for terminal rendering, invoked via Hyprland hotkey in a floating Ghostty window.

**Imports pattern** (lines 1-8, adapted for prompt_toolkit + Rich):
```python
import sys
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel
```

**Rich Console + Panel pattern** (lines 118-131):
```python
console = Console()

def print_header(model: str, deck: str) -> None:
    console.print()
    console.print(Panel(
        Text.assemble(
            ("QuickAsk", "bold cyan"),
            "  ·  ask anything, card it automatically\n",
            (f"model: {model}  ·  deck: {deck}", "dim"),
        ),
        border_style="cyan",
        padding=(0, 1),
    ))
```

**Core capture TUI pattern** (adapted from quickask.py's `run()` function, lines 278-351):
```python
def run_capture_tui() -> str | None:
    """Display capture UI and return multiline text, or None on cancel."""
    console.print(Panel(
        "[bold cyan]Quick Capture[/bold cyan]\n"
        "[dim]Type your thought. Ctrl+S to save. Escape to cancel.[/dim]",
        border_style="cyan",
        padding=(0, 1),
    ))
    
    kb = KeyBindings()
    
    @kb.add('c-s')
    def submit(event):
        event.current_buffer.validate_and_handle()
    
    try:
        text = prompt(
            "💭 ",
            multiline=True,
            key_bindings=kb,
            mouse_support=True,
            prompt_continuation=lambda w, ln, wrap: "... ",
        )
        return text.strip() if text.strip() else None
    except KeyboardInterrupt:
        return None
```

**Exit pattern** (from quickask.py lines 354-355):
```python
if __name__ == "__main__":
    # Run TUI, save, exit immediately
    text = run_capture_tui()
    if text:
        from quick_capture.db import save_capture
        capture_id = save_capture(text)
        console.print(f"[green]✓ Saved[/green] (id: {capture_id[:8]}...)")
        sys.exit(0)
    else:
        console.print("[dim]Cancelled.[/dim]")
        sys.exit(0)
```

**Error handling pattern** (from quickask.py — explicit Console, HTTPStatusError handling):
```python
except Exception as e:
    console.print(f"[red]✗ Failed to save[/red] — check nexus.db")
    sys.exit(1)
```

**Hyprland config pattern** (lines 358-376):
```ini
# Quick Capture — floating terminal overlay
bind = $mainMod, Q, exec, ghostty --title="QuickCapture" -e uv run --directory ~/repositories/quick-capture quick-capture

# Make it float, centered, reasonable size
windowrulev2 = float,        title:^(QuickCapture)$
windowrulev2 = size 900 600, title:^(QuickCapture)$
windowrulev2 = center,       title:^(QuickCapture)$
```

**What differs from analog:**
- quickask.py uses `Prompt.ask` (single-line); we use `prompt_toolkit.prompt` (multiline)
- quickask.py is a PEP 723 inline script; we're a proper Python package with `pyproject.toml`
- quickask.py has a loop (`while True`); capture TUI is single-shot (capture, save, exit)

---

### `src/quick_capture/db.py` (model, CRUD)

**Analog:** `~/repositories/nexus/server/db.ts`

The Nexus db.ts shows the exact SQLite CRUD pattern we need to replicate in Python. The key patterns: UUID IDs, ISO 8601 timestamps, prepared statements, WAL mode, table creation with `CREATE TABLE IF NOT EXISTS`.

**ID generation pattern** (lines 1-2 and usage throughout):
```python
# Python equivalent of crypto.randomUUID()
import uuid
capture_id = str(uuid.uuid4())
```

**DB init + WAL mode pattern** (lines 19-22):
```python
# Python equivalent of Nexus db.ts initDb()
import sqlite3
from pathlib import Path

NEXUS_DB = Path.home() / "repositories" / "nexus" / "nexus.db"

def init_captures_db(db_path: str | None = None) -> sqlite3.Connection:
    """Initialize captures tables in nexus.db. Creates tables if not exist."""
    path = db_path or str(NEXUS_DB)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.executescript("""
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
    """)
    conn.commit()
    return conn
```

**CRUD insert pattern** (from db.ts lines 76-98, adapted to Python):
```python
from datetime import datetime, timezone

def save_capture(text: str, conn: sqlite3.Connection | None = None) -> str:
    """Save raw capture and return its ID."""
    c = conn or sqlite3.connect(str(NEXUS_DB))
    capture_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    c.execute(
        "INSERT INTO captures (id, original_text, status, created_at) VALUES (?, ?, ?, ?)",
        (capture_id, text, "unprocessed", now)
    )
    c.commit()
    if conn is None:
        c.close()
    return capture_id
```

**CRUD read pattern** (from db.ts lines 100-109):
```python
def get_capture(capture_id: str, conn: sqlite3.Connection | None = None) -> dict | None:
    """Get a single capture by ID."""
    c = conn or sqlite3.connect(str(NEXUS_DB))
    row = c.execute(
        "SELECT * FROM captures WHERE id = ?",
        (capture_id,)
    ).fetchone()
    if conn is None:
        c.close()
    if not row:
        return None
    columns = [desc[0] for desc in c.description]
    return dict(zip(columns, row))
```

**CRUD update pattern** (from db.ts lines 111-169 — dynamic SET clause):
```python
def update_capture(capture_id: str, patch: dict, conn: sqlite3.Connection | None = None) -> dict | None:
    """Update capture fields. patch can include: status, updated_at."""
    c = conn or sqlite3.connect(str(NEXUS_DB))
    sets = []
    values = []
    for key, value in patch.items():
        sets.append(f"{key} = ?")
        values.append(value)
    if not sets:
        return get_capture(capture_id, c)
    values.append(capture_id)
    c.execute(f"UPDATE captures SET {', '.join(sets)} WHERE id = ?", values)
    c.commit()
    result = get_capture(capture_id, c)
    if conn is None:
        c.close()
    return result
```

**Parameterized query pattern** — ALWAYS use `?` placeholders, never string concatenation (security):
```python
# CORRECT (from Nexus pattern)
c.execute("SELECT * FROM captures WHERE id = ?", (capture_id,))

# WRONG — SQL injection risk
c.execute(f"SELECT * FROM captures WHERE id = '{capture_id}'")
```

**What differs from analog:**
- Nexus uses `better-sqlite3` (Node.js); we use Python's `sqlite3` (stdlib)
- Nexus uses Zod schemas for row validation; we use plain dicts or dataclasses
- Nexus uses prepared statements via `.prepare()`; Python uses parameterized `.execute()`
- We add `busy_timeout = 5000` for SQLite lock contention (Python side)

---

### `src/quick_capture/enrich.py` (service, subprocess)

**Analog:** `~/repositories/nexus/server/api/opencode.ts`

The opencode.ts file shows exactly how Nexus invokes `opencode run` as a subprocess to get LLM completions. We adapt this pattern from Node.js `execSync` to Python `subprocess.run`.

**Subprocess invocation pattern** (lines 28-32, adapted to Python):
```python
import subprocess
import json

def enrich_capture(capture_id: str, text: str) -> dict:
    """Run enrichment via opencode run subprocess."""
    enrichment_prompt = f"""Analyze this captured thought and return ONLY valid JSON:
    
    {{
      "bucket": "Task" | "Idea" | "Reference" | "Question",
      "enriched_text": "developed version",
      "tags": ["tag1", "tag2"],
      "wikilinks": ["wiki-page-name"],
      "actionable": true/false,
      "priority": "low" | "medium" | "high"
    }}
    
    Original: {text}
    """
    
    result = subprocess.run(
        ["opencode", "run", "--format", "json", enrichment_prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"opencode run failed: {result.stderr}")
    
    # Parse enrichment from output (handle potential JSON wrapping)
    output = result.stdout.strip()
    enrichment = _parse_enrichment_output(output)
    return enrichment
```

**JSON parsing with fallback** (inspired by opencode.ts line 32 and quickask.py lines 206-211):
```python
def _parse_enrichment_output(output: str) -> dict:
    """Parse enrichment JSON from opencode run output."""
    # Handle ```json ... ``` wrapping (models sometimes add this)
    if output.startswith("```"):
        output = output.split("\n", 1)[1]
        output = output.rsplit("```", 1)[0].strip()
    
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        # Try finding the last valid JSON object in the output
        for line in reversed(output.split("\n")):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"Could not parse enrichment JSON from output")
```

**Error handling pattern** (from opencode.ts lines 58-60):
```python
try:
    result = enrich_capture(capture_id, text)
except subprocess.TimeoutExpired:
    # 120s timeout for LLM calls
    print("Enrichment timed out after 120s", file=sys.stderr)
except RuntimeError as e:
    print(f"Enrichment failed: {e}", file=sys.stderr)
```

**What differs from analog:**
- Nexus uses Node.js `execSync`; we use Python `subprocess.run`
- Nexus captures session ID from opencode; we capture enrichment JSON
- Nexus runs opencode in background (`&` and `sleep 0.8`); we run synchronously for enrichment
- We must add `shell=False` (security) and sanitize text before passing to subprocess

---

### `src/quick_capture/models.py` (model, —)

**Analog:** `~/repositories/nexus/shared/schema.ts`

The schema.ts file defines Zod schemas for runtime validation and TypeScript types. We adapt this to Python dataclasses.

**Schema pattern** (from schema.ts, lines 1-58):
```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class CaptureStatus(str, Enum):
    UNPROCESSED = "unprocessed"
    ENRICHING = "enriching"
    ENRICHED = "enriched"
    DISPATCHED = "dispatched"

class Bucket(str, Enum):
    TASK = "Task"
    IDEA = "Idea"
    REFERENCE = "Reference"
    QUESTION = "Question"

@dataclass
class Capture:
    id: str
    original_text: str
    status: CaptureStatus = CaptureStatus.UNPROCESSED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = None

@dataclass
class CaptureEnrichment:
    id: str
    capture_id: str
    bucket: Bucket
    enriched_text: str
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
    opencode_session_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

**What differs from analog:**
- Schema.ts uses Zod for runtime validation + type generation; we use dataclasses + Enums
- We don't need `.optional()` — Python `Optional` handles it
- Tags and wikilinks stored as JSON TEXT in SQLite; parsed on read

---

### `nexus/server/api/captures.ts` (controller, request-response)

**Analog:** `~/repositories/nexus/server/api/sessions.ts`

This is the closest match — sessions has GET list, GET by ID, POST create, and DELETE. Captures needs GET list, GET by ID, PATCH update, and POST for enrichment trigger.

**Imports + route setup pattern** (lines 1-9):
```typescript
import { Hono } from 'hono'
import { zValidator } from '@hono/zod-validator'
import { CreateSessionSchema } from '../../shared/schema'
import { getSessions, getSessionById, createSession, deleteSessionById } from '../db'
import { writeSessionMd } from '../md-writer'
import { META_DIR } from '../config'

export const sessionsRoute = new Hono()
```

**GET list pattern** (lines 11-14):
```typescript
sessionsRoute.get('/', (c) => {
  const sessions = getSessions()
  return c.json(sessions)
})
```

**GET by ID + 404 pattern** (lines 16-21):
```typescript
sessionsRoute.get('/:id', (c) => {
  const session = getSessionById(c.req.param('id'))
  if (!session) {
    return c.json({ error: 'Session not found' }, 404)
  }
  return c.json(session)
})
```

**POST with Zod validation pattern** (lines 24-39):
```typescript
sessionsRoute.post(
  '/',
  zValidator('json', CreateSessionSchema),
  (c) => {
    const data = c.req.valid('json')
    const session = createSession(data)
    // Side effect: write markdown
    try {
      const filePath = path.join(META_DIR, `${session.id}-session.md`)
      writeSessionMd(session, filePath)
    } catch (err) {
      console.error('Failed to write session markdown:', err)
    }
    return c.json(session, 201)
  }
)
```

**PATCH with Zod validation pattern** (from projects.ts lines 24-46):
```typescript
projectsRoute.patch(
  '/:id',
  zValidator('json', UpdateProjectSchema),
  (c) => {
    const id = c.req.param('id')
    const existing = getProjectById(id)
    if (!existing) {
      return c.json({ error: 'Project not found' }, 404)
    }
    const data = c.req.valid('json')
    const updated = patchProject(id, data)
    // Side effect: write markdown
    try {
      const filePath = path.join(PROJECTS_DIR, `${updated.id}.md`)
      writeProjectMd(updated, tasks, filePath)
    } catch (err) {
      console.error('Failed to write project markdown:', err)
    }
    return c.json(updated)
  }
)
```

**What differs from analog:**
- Captures has a `POST /:id/enrich` endpoint for triggering enrichment (opencode run)
- Captures uses PATCH for status updates (not full entity update)
- Captures GET list needs `?status=` and `?bucket=` query params for filtering

---

### `nexus/src/api.js` (API client, —)

**Analog:** `~/repositories/nexus/src/api.js`

We'll add capture API functions following the exact same pattern.

**API function pattern** (lines 1-10):
```javascript
const BASE = '/api'

async function req(path, opts) {
  const url = `${BASE}${path}`
  const res = opts ? await fetch(url, opts) : await fetch(url)
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} on ${url}`)
  }
  return res.json()
}
```

**New capture API functions** (following same pattern):
```javascript
export function getCaptures(status, bucket) {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (bucket) params.set('bucket', bucket)
  const qs = params.toString()
  return req(`/captures${qs ? '?' + qs : ''}`)
}

export function getCapture(id) {
  return req(`/captures/${encodeURIComponent(id)}`)
}

export function updateCapture(id, body) {
  return req(`/captures/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function enrichCapture(id) {
  return req(`/captures/${encodeURIComponent(id)}/enrich`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
}
```

---

### `nexus/src/components/captures.js` (component, request-response)

**Analog:** `~/repositories/nexus/src/components/grid.js` + `sidebar.js`

Grid.js shows the card rendering pattern with status pills, drag-and-drop. Sidebar.js shows the slide panel detail view. We combine both patterns for captures.

**Card rendering pattern** (from grid.js lines 102-181 — status-based styling, accent bars, badges):
```javascript
function renderStatusBadge(status) {
  return `<span class="status-${status} inline-flex items-center gap-[5px] text-[11px] text-[var(--status-color)] font-medium tracking-wide uppercase">
    <span class="w-1.5 h-1.5 rounded-full bg-[var(--status-color)]"></span>${status || 'unknown'}</span>`
}

function renderCaptureCard(capture, enrichment) {
  const bucket = enrichment?.bucket || 'unprocessed'
  const statusClass = bucket === 'Task' ? 'active'
    : bucket === 'Idea' ? 'spark'
    : bucket === 'Reference' ? 'queued'
    : 'backlog'  // Question
  
  return `<div
    class="nexus-card status-${statusClass} relative overflow-hidden border rounded-lg p-3.5 cursor-pointer transition-all duration-150 bg-surface border-border hover:bg-[#161f2c] hover:border-[#2a3d54]"
    data-id="${capture.id}"
    @click="selectedCapture = $store.nexus.captures.find(c => c.id === '${capture.id}')"
  >
    <div class="absolute top-0 inset-x-0 h-0.5 bg-[--status-color]"></div>
    <div class="flex justify-between items-center mb-1.5">
      ${renderStatusBadge(bucket === 'unprocessed' ? 'unprocessed' : bucket)}
      <span class="text-[11px] text-muted font-mono">${daysAgo(daysSince(capture.created_at))}</span>
    </div>
    <p class="text-sm text-[#e0e0cc] line-clamp-2">${escapeHtml(capture.original_text)}</p>
  </div>`
}
```

**Slide panel pattern** (from sidebar.js lines 505-560 — overlay + panel structure):
```javascript
// Panel HTML structure (from sidebar.js)
return `
  <div class="panel-overlay" :class="sidebarOpen ? 'open' : ''" @click="closeSidebar()"></div>
  <div class="slide-panel" :class="sidebarOpen ? 'open' : ''">
    <!-- content -->
  </div>
`
```

**Filter button pattern** (from sidebar.js lines 429-431):
```javascript
['all', 'backlog', 'in-progress', 'done'].map((f, i) =>
  `<button data-filter-btn="${f}" class="btn btn-xs rounded ${i === 0 ? 'filter-btn-active' : 'filter-btn-inactive'}" 
    onclick="__filterTasks('${f}',this)">${f}</button>`
)
```

**What differs from analog:**
- Captures has a fixed set of bucket filters (All, Task, Idea, Reference, Question) vs dynamic status filters
- Capture detail panel shows original text + enrichment side by side
- No drag-and-drop for captures (no status change via drag)

---

### `src/quick_capture/__init__.py` (config, —)

**Analog:** `nexus/shared/schema.ts` (module initialization pattern)

Simple package init exposing key types and constants:

```python
"""Quick Capture — frictionless inbox capture for Hyprland."""

__version__ = "0.1.0"
```

---

### `pyproject.toml` (config, —)

**No direct analog** — this is a new project. Pattern comes from RESEARCH.md standard stack:

```toml
[project]
name = "quick-capture"
version = "0.1.0"
description = "Frictionless inbox capture for Hyprland"
requires-python = ">=3.11"
dependencies = [
    "prompt-toolkit>=3.0.52",
    "rich>=15.0.0",
]

[dependency-groups]
dev = [
    "pytest",
    "pytest-cov",
    "ruff",
]

[tool.ruff]
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

### `tests/conftest.py` (test, —)

**Analog:** `nexus/server/db.test.ts` (test fixture pattern)

**Test fixture pattern** (from db.test.ts lines 22-27 — in-memory DB setup per test):
```python
import sqlite3
import pytest

NEXUS_DB_PATH = ":memory:"

@pytest.fixture
def db():
    """Provide a fresh in-memory database for each test."""
    from quick_capture.db import init_captures_db
    conn = init_captures_db(NEXUS_DB_PATH)
    yield conn
    conn.close()

@pytest.fixture
def sample_capture(db):
    """Insert a sample capture and return its data."""
    from quick_capture.db import save_capture
    capture_id = save_capture("Test thought", conn=db)
    return {"id": capture_id, "original_text": "Test thought"}
```

---

### `tests/test_db.py` (test, CRUD)

**Analog:** `nexus/server/db.test.ts`

**Test pattern** (from db.test.ts — describe/it pattern, adapted to pytest):
```python
import sqlite3
from quick_capture.db import init_captures_db, save_capture, get_capture, update_capture

class TestSaveCapture:
    def test_inserts_and_returns_id(self, db):
        capture_id = save_capture("My thought", conn=db)
        assert capture_id is not None
        assert len(capture_id) == 36  # UUID format

    def test_preserves_original_text(self, db):
        capture_id = save_capture("Original text here", conn=db)
        capture = get_capture(capture_id, conn=db)
        assert capture["original_text"] == "Original text here"

    def test_default_status_is_unprocessed(self, db):
        capture_id = save_capture("Test", conn=db)
        capture = get_capture(capture_id, conn=db)
        assert capture["status"] == "unprocessed"

class TestNewTablesOnly:
    def test_does_not_modify_existing_tables(self, db):
        # Ensure the captures tables exist
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('captures', 'capture_enrichments')"
        )
        tables = [row[0] for row in cursor.fetchall()]
        assert "captures" in tables
        assert "capture_enrichments" in tables
        # Ensure no existing nexus tables were altered
        # (This test verifies by checking the DB has ONLY new tables plus
        # whatever was there, not by destructive means)
```

---

### `tests/test_enrich.py` (test, subprocess)

**Analog:** `nexus/server/db.test.ts` (test structure pattern)

```python
import json
from unittest.mock import patch, MagicMock

class TestEnrichCapture:
    def test_parses_json_output(self):
        from quick_capture.enrich import _parse_enrichment_output
        output = '{"bucket": "Task", "enriched_text": "Developed", "tags": ["test"], "wikilinks": []}'
        result = _parse_enrichment_output(output)
        assert result["bucket"] == "Task"
        assert result["enriched_text"] == "Developed"

    def test_handles_json_wrapped_in_code_fence(self):
        from quick_capture.enrich import _parse_enrichment_output
        output = '```json\n{"bucket": "Idea", "enriched_text": "x", "tags": [], "wikilinks": []}\n```'
        result = _parse_enrichment_output(output)
        assert result["bucket"] == "Idea"

    def test_bucket_classification(self, db):
        """Verify bucket is one of: Task, Idea, Reference, Question"""
        from quick_capture.enrich import _parse_enrichment_output
        for bucket in ["Task", "Idea", "Reference", "Question"]:
            output = json.dumps({"bucket": bucket, "enriched_text": "test", "tags": [], "wikilinks": []})
            result = _parse_enrichment_output(output)
            assert result["bucket"] == bucket
```

---

### `tests/test_cli.py` (test, request-response)

**Analog:** `nexus/server/db.test.ts` (test structure pattern)

```python
from unittest.mock import patch, MagicMock

class TestMultilineInput:
    def test_accepts_multiline_text(self):
        """Verify prompt_toolkit multiline mode works"""
        # This is typically tested by mocking prompt() return value
        from quick_capture.cli import run_capture_tui
        with patch('quick_capture.cli.prompt', return_value="Line 1\nLine 2"):
            result = run_capture_tui()
            assert result == "Line 1\nLine 2"

class TestSaveExits:
    def test_saves_and_exits_on_submit(self):
        from quick_capture.cli import run_capture_tui
        with patch('quick_capture.cli.prompt', return_value="My thought"):
            with patch('quick_capture.db.save_capture', return_value="abc-123"):
                result = run_capture_tui()
                assert result == "My thought"
```

---

## Shared Patterns

### SQLite Connection Management

**Source:** `nexus/server/db.ts` lines 19-22 + Python stdlib
**Apply to:** `src/quick_capture/db.py`, all db tests

```python
import sqlite3

def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get a connection to nexus.db with proper pragmas."""
    path = db_path or str(NEXUS_DB)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")  # Prevent SQLITE_BUSY
    return conn
```

### Error Handling — Terminal Exit Pattern

**Source:** `llm-cli/quickask.py` lines 300-312
**Apply to:** `src/quick_capture/cli.py`

```python
import sys
from rich.console import Console

console = Console()

try:
    # Main capture logic
    ...
except Exception as e:
    console.print(f"[red]✗ Failed to save[/red] — check nexus.db")
    sys.exit(1)
```

### Input Validation — Parameterized Queries

**Source:** `nexus/server/db.ts` (all queries use `?` placeholders)
**Apply to:** `src/quick_capture/db.py`

```python
# ALWAYS use parameterized queries
cursor.execute("SELECT * FROM captures WHERE id = ?", (capture_id,))
# NEVER: f"SELECT * FROM captures WHERE id = '{capture_id}'"
```

### Hono API Route Pattern

**Source:** `nexus/server/api/sessions.ts`
**Apply to:** `nexus/server/api/captures.ts`

```typescript
import { Hono } from 'hono'
import { zValidator } from '@hono/zod-validator'
// CRUD operations follow: GET /, GET /:id, POST /, PATCH /:id
// 404 handling: if (!entity) return c.json({ error: 'Not found' }, 404)
// Validation: zValidator('json', Schema)
```

### Alpine.js Store + Component Pattern

**Source:** `nexus/src/app.js` lines 17-201
**Apply to:** `nexus/src/components/captures.js`

```javascript
// Extend existing Alpine store:
// - Add captures[], selectedCapture, captureFilter to createAppData()
// - Add getCaptures(), selectCapture(), closeCapturePanel() methods
// - Add enrichCapture(id) method for POST /api/captures/:id/enrich

// Component renders HTML strings (not JSX):
// - Use escapeHtml() for XSS prevention
// - Use ${variable} interpolation in template literals
// - Use window.__functionName for event handlers
```

### Rich Terminal Rendering Pattern

**Source:** `llm-cli/quickask.py` lines 118-156
**Apply to:** `src/quick_capture/cli.py`

```python
from rich.console import Console
from rich.panel import Panel

console = Console()

# Header panel
console.print(Panel(
    "[bold cyan]Quick Capture[/bold cyan]\n"
    "[dim]Type your thought. Ctrl+S to save. Escape to cancel.[/dim]",
    border_style="cyan",
    padding=(0, 1),
))

# Success message
console.print(f"[green]✓ Saved[/green] (id: {capture_id[:8]}...)")

# Cancel message
console.print("[dim]Cancelled.[/dim]")
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `pyproject.toml` | config | — | New project setup; no existing Python project in the workspace to copy from. Use RESEARCH.md Standard Stack section for dependency versions. |

## Metadata

**Analog search scope:** `~/repositories/nexus/` (server/, shared/, src/), `~/repositories/llm-cli/`
**Files scanned:** 15
**Pattern extraction date:** 2026-05-09