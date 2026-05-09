# Phase 1: Capture & Enrich MVP - Research

**Researched:** 2026-05-09
**Domain:** Python CLI tool, Hyprland floating terminal, SQLite storage, LLM enrichment via opencode run
**Confidence:** HIGH

## Summary

This phase builds an end-to-end capture pipeline: hotkey triggers a floating Ghostty terminal running a Python TUI, user types multiline text, submits, and the entry saves to SQLite in nexus.db. A separate enrichment step uses `opencode run` to classify and develop the capture using wiki context, persisting the enriched version alongside the original. The Nexus web UI then displays enriched entries.

The proven pattern from `quickask.py` shows exactly how to handle the Hyprland floating terminal with Ghostty window rules and Rich for terminal rendering. However, quickask.py uses Rich's single-line `Prompt.ask`, so for multiline capture we need `prompt_toolkit` which provides native multiline editing with custom key bindings (Ctrl+Enter or Ctrl+S to submit).

The Nexus project (Node.js/Hono/better-sqlite3/Alpine.js) already has a complete API pattern (`server/api/*.ts`, `shared/schema.ts`, `server/db.ts`) and web UI pattern. Quick Capture adds new tables to the same `nexus.db` but must NOT modify existing schema or code. The capture tool itself is a Python project using `uv`, with its own `pyproject.toml`, and communicates with nexus.db directly via Python's `sqlite3` (standard library, no external dependency needed).

**Primary recommendation:** Build the capture TUI as a standalone Python package (`quick-capture`) using `prompt_toolkit` for multiline input and `rich` for rendering, triggered by Hyprland hotkey via Ghostty. Store captures in new `captures` and `capture_enrichments` tables in `nexus.db`. Enrich via `opencode run` subprocess. Add capture viewing to the existing Nexus web UI by adding new API routes and a frontend view.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|-----------|-------------|----------------|-----------|
| Hotkey-triggered terminal capture | Browser/Client (Terminal) | — | Hyprland hotkey spawns Ghostty; TUI runs in terminal |
| Multiline text input & submit | Browser/Client (Terminal) | — | prompt_toolkit handles input; terminal closes on submit |
| SQLite persistence | Database/Storage | — | Direct sqlite3 writes to nexus.db; same file, new tables |
| LLM enrichment | API/Backend (subprocess) | — | `opencode run` is a CLI subprocess; no custom server needed |
| Enriched entry display | Frontend Server (Nexus web UI) | — | Nexus is a Hono/Alpine.js web app; add route + view |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| prompt_toolkit | 3.0.52 (latest) | Multiline TUI input with custom key bindings | Only Python library with robust multiline editing, history, and key binding customization [VERIFIED: Context7] |
| rich | 15.0.0 (installed) | Terminal rendering, panels, status displays | Proven pattern from quickask.py; project already installed [VERIFIED: pip show] |
| sqlite3 (stdlib) | 3.53.0 | Database access to nexus.db | Standard library, no dependency needed; Python 3.11+ ships with modern SQLite [VERIFIED: python3 check] |
| uv | 0.11.3 (installed) | Package management, project setup, script running | Project constraint: modern Python tooling [VERIFIED: uv --version] |
| ruff | 0.15.11 (installed) | Linting & formatting | Project constraint from modern-python skill [VERIFIED: ruff --version] |
| ty | latest | Type checking | Project constraint from modern-python skill [ASSUMED] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28.1 (installed) | HTTP client if needed for API calls | Only if we need to POST to Nexus API from Python (alternative: direct DB write) |
| pytest | latest | Testing | All db operations and TUI logic |
| pytest-cov | latest | Coverage enforcement | CI and development |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| prompt_toolkit | Textual (full TUI framework) | Textual is overkill for a single input field; adds ~2s startup latency for TUI app framework. prompt_toolkit gives multiline editing without framework overhead. |
| prompt_toolkit | Rich Prompt (single-line) | Rich Prompt.ask only supports single-line input. Cannot capture multiline thoughts. |
| Direct sqlite3 writes | Nexus API (HTTP POST) | Direct writes are faster (no network round-trip), but creates coupling to DB schema. Since we own both, direct writes win for <5s capture. |
| opencode run subprocess | Custom API server | opencode run leverages wiki-query skill and existing LLM config; no server to maintain. Custom API would add complexity. |

**Installation:**
```bash
uv init quick-capture
cd quick-capture
uv add prompt-toolkit rich
uv add --group dev pytest pytest-cov ruff ty
```

**Version verification:**
- prompt_toolkit: latest (confirmed via Context7, 3.0.x series)
- rich: 15.0.0 installed locally
- sqlite3: Python 3.14.4 stdlib with SQLite 3.53.0
- uv: 0.11.3 installed
- ruff: 0.15.11 installed

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hyprland (Wayland)                        │
│  bind = $mainMod, Q, exec, ghostty --title="QuickCapture" ...   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ spawns
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│               Ghostty Terminal (floating window)                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Quick Capture TUI (Python)                                │  │
│  │  ┌───────────────────────────────────────────────────────┐│  │
│  │  │ prompt_toolkit: multiline input                        ││  │
│  │  │ Ctrl+S or Ctrl+Enter → submit                        ││  │
│  │  │ Escape → cancel & close                               ││  │
│  │  └───────────────────────────────────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ on submit
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 quick-capture (Python package)                    │
│  1. Write raw text + timestamp → nexus.db (captures table)       │
│  2. Status = "unprocessed"                                       │
│  3. If --enrich flag: spawn opencode run                          │
│  4. Terminal exits (window closes)                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │ enrich (subprocess)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 opencode run (LLM enrichment)                    │
│  - Receives capture text as prompt                                │
│  - wiki-query skill pulls context from Obsidian vault             │
│  - Classifies bucket: Task | Idea | Reference | Question         │
│  - Returns enriched text + bucket + wikilinks                     │
│  - Python script writes enrichment → nexus.db                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │ read
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│               Nexus Web UI (Hono + Alpine.js)                    │
│  GET /api/captures → list captures with enrichment status        │
│  GET /api/captures/:id → full capture + enrichment               │
│  PATCH /api/captures/:id → update capture status                │
│  Frontend: new "Captures" view in sidebar                        │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
quick-capture/
├── pyproject.toml              # uv-managed project config
├── .python-version             # Python 3.11+
├── README.md
├── Makefile                    # dev, lint, format, test
├── src/
│   └── quick_capture/
│       ├── __init__.py
│       ├── cli.py              # Entry point: TUI, argument parsing
│       ├── db.py               # SQLite operations (captures table)
│       ├── enrich.py           # opencode run subprocess
│       ├── models.py           # Data models (Capture, Enrichment)
│       └── hyprland.py         # Hyprland config helpers (optional)
├── tests/
│   ├── conftest.py             # Shared fixtures, temp DB
│   ├── test_db.py              # DB operations tests
│   ├── test_enrich.py          # Enrichment subprocess tests
│   └── test_cli.py             # CLI integration tests
└── .config/
    └── hypr/
        └── quick-capture.conf  # Hyprland window rules (docs)
```

Nexus additions (separate repo, same nexus.db):
```
nexus/server/
├── api/
│   └── captures.ts             # New API route
└── db.ts                       # Extended with captures functions

nexus/src/
├── api.js                      # Add capture endpoints
└── components/
    └── captures.js             # New captures view
```

### Pattern 1: Floating Terminal Capture (Hyprland + Ghostty)

**What:** Hyprland hotkey spawns a floating Ghostty window running the Python capture TUI. Window auto-closes after submission.
**When to use:** Every capture event.

**Hyprland config** (in `~/.config/hypr/hyprland.conf`):
```ini
# Quick Capture — floating terminal overlay
bind = $mainMod, Q, exec, ghostty --title="QuickCapture" -e uv run --directory ~/repositories/quick-capture quick-capture

# Make it float, centered, reasonable size
windowrulev2 = float,        title:^(QuickCapture)$
windowrulev2 = size 900 600, title:^(QuickCapture)$
windowrulev2 = center,       title:^(QuickCapture)$
```

**Source:** Adapted from quickask.py Hyprland setup [VERIFIED: quickask.py lines 358-376]

### Pattern 2: Multiline TUI Input with prompt_toolkit

**What:** Use `prompt_toolkit` with multiline mode and custom key bindings for submit/cancel.
**When to use:** The capture TUI.

```python
# Source: Context7 - prompt_toolkit docs
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings

kb = KeyBindings()

@kb.add('c-s')  # Ctrl+S to submit
def submit(event):
    event.current_buffer.validate_and_handle()

text = prompt(
    "💭 ",  # Thought bubble prompt prefix
    multiline=True,
    key_bindings=kb,
    mouse_support=True,
    prompt_continuation=lambda w, ln, wrap: "... ",
)
```

**Key binding decisions:**
- **Ctrl+S or Ctrl+Enter** → Submit (accept input, save, close)
- **Escape** → Cancel and close (no save)
- **Enter** → Newline (multiline mode)

### Pattern 3: Direct SQLite Write for Capture Speed

**What:** Write captures directly to `nexus.db` using Python's `sqlite3` module. No HTTP overhead.
**When to use:** Every capture save. This is the <5s window — direct DB write is ~1ms vs ~50ms for HTTP round-trip.

```python
# Source: Python stdlib sqlite3 [VERIFIED]
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

NEXUS_DB = Path.home() / "repositories" / "nexus" / "nexus.db"

def save_capture(text: str) -> str:
    """Save raw capture and return its ID."""
    import uuid
    capture_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    conn = sqlite3.connect(str(NEXUS_DB))
    conn.execute(
        "INSERT INTO captures (id, original_text, status, created_at) VALUES (?, ?, ?, ?)",
        (capture_id, text, "unprocessed", now)
    )
    conn.commit()
    conn.close()
    return capture_id
```

### Pattern 4: LLM Enrichment via opencode run

**What:** Use `opencode run` as a subprocess to enrich captures, leveraging the wiki-query skill for context.
**When to use:** After capture (immediate or batch).

```python
# Source: opencode run --help [VERIFIED], nexus/server/api/opencode.ts [VERIFIED]
import subprocess
import json

def enrich_capture(capture_id: str, text: str) -> dict:
    """Run enrichment via opencode run subprocess."""
    prompt = f"""Analyze this captured thought and provide:
1. bucket: one of Task, Idea, Reference, Question
2. enriched_text: developed version of the original thought
3. tags: list of relevant tags
4. wikilinks: list of related wiki page names

Original: {text}

Return JSON only."""
    
    result = subprocess.run(
        ["opencode", "run", "--format", "json", prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    # Parse enrichment from result
    ...
```

### Pattern 5: Nexus API Extension for Capture Viewing

**What:** Add new API routes to the existing Hono server and a new Alpine.js view.
**When to use:** REVW-01 — displaying enriched entries.

```typescript
// Pattern from existing nexus/server/api/projects.ts [VERIFIED]
import { Hono } from 'hono'

export const capturesRoute = new Hono()

capturesRoute.get('/', (c) => {
  // List all captures, optionally filter by status/bucket
})

capturesRoute.get('/:id', (c) => {
  // Get single capture with enrichment
})

capturesRoute.patch('/:id', (c) => {
  // Update capture status
})
```

### Anti-Patterns to Avoid

- **Using Rich Prompt.ask for multiline input:** Rich only supports single-line input. Use prompt_toolkit for multiline.
- **Starting a custom API server for enrichment:** opencode run already provides LLM access with wiki-query skill. Don't build another server.
- **Modifying existing nexus.db tables:** Constraint: add NEW tables only, never alter existing schema.
- **Using Textual for capture TUI:** Textual adds ~2s startup latency for a full TUI framework. The capture window must appear and be ready in <1s. prompt_toolkit is ~100ms startup.
- **HTTP POST to Nexus for capture saving:** Adds network latency that violates the <5s constraint. Direct sqlite3 write is ~1ms.
- **Blocking the terminal on enrichment:** Enrichment takes 10-120s. The terminal must close immediately after capture is saved. Enrichment runs as background process or separate command.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multiline terminal input | Custom readline loop with stdin | prompt_toolkit | Handles history, cursor movement, line wrapping, Unicode, mouse support — deceptively complex |
| Terminal rendering | ANSI escape sequence spaghetti | Rich | Handles cross-terminal rendering, panels, colors, markdown |
| UUID generation | Custom ID scheme | uuid.uuid4() | Standard library, cryptographically random, no collisions |
| SQLite schema creation | Manual DDL string manipulation | Parameterized CREATE TABLE IF NOT EXISTS statements | SQL injection prevention, idempotent migrations |
| LLM invocation | Custom HTTP client to LLM API | opencode run | Already configured with provider, model, wiki-query skill context |
| Database access in Nexus API | Custom query builder | better-sqlite3 prepared statements | Nexus already uses these; follow existing pattern |

**Key insight:** prompt_toolkit handles the hardest part (multiline editing with custom bindings) and Rich handles rendering. Together they're <50 lines of TUI code. The real complexity is in the enrichment prompt design and the DB schema.

## Common Pitfalls

### Pitfall 1: Ghostty Window Spawn Latency
**What goes wrong:** Ghostty takes >1s to start, pushing total capture time past 5s.
**Why it happens:** Ghostty cold start involves font loading, shader compilation, etc.
**How to avoid:** Use `uv run` with cached dependencies; Ghostty warm start is ~300ms. Consider pre-warming with a daemon/socket approach if latency is too high.
**Warning signs:** User reports >3s delay between hotkey and input appearing.

### Pitfall 2: SQLite Lock Contention with Nexus
**What goes wrong:** Nexus Node.js process and Quick Capture Python process both write to nexus.db simultaneously, causing SQLITE_BUSY errors.
**Why it happens:** SQLite WAL mode allows concurrent reads but only one writer at a time. The default busy timeout is 0.
**How to avoid:** Set `busy_timeout` on all connections (both Python and Node.js). Nexus already uses WAL mode. Add: `conn.execute("PRAGMA busy_timeout = 5000")` in Python. Verify Nexus does the same.
**Warning signs:** Intermittent "database is locked" errors when both processes are active.

### Pitfall 3: opencode run Output Parsing Failure
**What goes wrong:** `opencode run --format json` output format may change or be unexpected, causing enrichment parsing to fail.
**Why it happens:** opencode's JSON output includes session metadata alongside the actual response; the format might not match assumptions.
**How to avoid:** Write robust parsing that handles multiple JSON formats. Use `--format json` and parse the last meaningful JSON object. Add fallback for plain text output. Test with a known prompt first.
**Warning signs:** Enrichment returns empty dict or throws JSONDecodeError.

### Pitfall 4: Terminal Doesn't Close After Save
**What goes wrong:** User saves capture but the Ghostty window stays open, defeating the zero-friction goal.
**Why it happens:** Python script completes but terminal session waits, or exception prevents sys.exit().
**How to avoid:** Use `sys.exit(0)` explicitly after save. Consider `os._exit(0)` as last resort. Wrap everything in try/except with guaranteed exit.
**Warning signs:** Terminal hangs after "Saved!" message.

### Pitfall 5: Enrichment Blocks Capture Terminal
**What goes wrong:** Running `opencode run` synchronously in the capture script keeps the terminal open for 10-30s.
**Why it happens:** LLM API calls are slow; opencode run includes initialization overhead.
**How to avoid:** Enrichment MUST be a separate step. Capture script saves to DB with status "unprocessed" and exits immediately. Enrichment is triggered separately (batch command, cron, or on-demand).
**Warning signs:** Terminal stays open for >5s after typing a thought.

### Pitfall 6: Hyprland Window Focus Stealing
**What goes wrong:** Other windows steal focus from the floating capture terminal.
**Why it happens:** Hyprland doesn't always give focus to newly spawned windows depending on config.
**How to avoid:** Add `windowrulev2 = stayfocused, title:^(QuickCapture)$` or similar Hyprland rules. Test that the window receives keyboard input immediately.
**Warning signs:** User presses hotkey, window appears, but typing goes to wrong window.

## Code Examples

### Multiline Capture TUI with prompt_toolkit

```python
# Source: Context7 - prompt-toolkit docs [VERIFIED]
import sys
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel

console = Console()

def run_capture_tui() -> str | None:
    """Display capture UI and return multiline text, or None on cancel."""
    console.print(Panel(
        "[bold cyan]Quick Capture[/bold cyan]\n"
        "[dim]Type your thought. Ctrl+S or Ctrl+Enter to save. Escape to cancel.[/dim]",
        border_style="cyan",
        padding=(0, 1),
    ))
    
    kb = KeyBindings()
    
    @kb.add('c-s')        # Ctrl+S → submit
    @kb.add('c-j', filter=lambda e: True)  # We'll handle Enter differently
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


if __name__ == "__main__":
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

### SQLite Schema for Captures (New Tables in nexus.db)

```sql
-- NEW tables added to nexus.db — do NOT modify existing tables
CREATE TABLE IF NOT EXISTS captures (
    id TEXT PRIMARY KEY,              -- UUID
    original_text TEXT NOT NULL,       -- Raw user input, preserved verbatim
    status TEXT NOT NULL DEFAULT 'unprocessed',  
    -- Values: unprocessed, enriching, enriched, dispatched
    created_at TEXT NOT NULL,           -- ISO 8601 UTC timestamp
    updated_at TEXT                     -- Last status change
);

CREATE TABLE IF NOT EXISTS capture_enrichments (
    id TEXT PRIMARY KEY,               -- UUID
    capture_id TEXT NOT NULL,          -- FK to captures
    bucket TEXT NOT NULL,              -- Task | Idea | Reference | Question
    enriched_text TEXT NOT NULL,        -- LLM-developed version
    tags TEXT,                          -- JSON array of tags
    wikilinks TEXT,                     -- JSON array of wiki page references
    opencode_session_id TEXT,          -- opencode run session ID for traceability
    created_at TEXT NOT NULL,
    FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE CASCADE
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_captures_status ON captures(status);
CREATE INDEX IF NOT EXISTS idx_captures_created ON captures(created_at);
CREATE INDEX IF NOT EXISTS idx_enrichments_capture ON capture_enrichments(capture_id);
```

### Enrichment Prompt Design for opencode run

```python
# Source: Derived from quickask.py system prompt pattern [VERIFIED]
ENRICHMENT_PROMPT = """You are a thought enrichment assistant. Analyze the captured text and return ONLY valid JSON:

{
  "bucket": "Task" | "Idea" | "Reference" | "Question",
  "enriched_text": "string - developed, clearer version of the thought",
  "tags": ["tag1", "tag2"],
  "wikilinks": ["wiki-page-name-1"],
  "actionable": true/false,
  "priority": "low" | "medium" | "high"
}

CLASSIFICATION RULES:
- Task: Something to DO. Has an action verb or deadline.
- Idea: A concept, possibility, or creative thought to develop later.
- Reference: A URL, citation, or fact worth remembering.
- Question: An open question that needs research or an answer.

ENRICHMENT RULES:
- Preserve ALL original meaning. Never lose information.
- Add context the original thought implies but didn't state.
- Make the thought clearer and more actionable.
- If it's a Task, suggest next steps.
- If it's an Idea, suggest related concepts or expansion paths.
- If it's a Reference, summarize key points.
- If it's a Question, suggest where to find the answer.

Use wiki-query to find related content in the Obsidian wiki. Reference relevant pages.

Original capture:
"""
```

### Hyprland Configuration Setup Script

```python
# Source: Adapted from quickask.py pattern [VERIFIED]
HYPR_CONFIG = """
# Quick Capture — floating terminal overlay
bind = $mainMod, Q, exec, ghostty --title="QuickCapture" -e uv run --directory ~/repositories/quick-capture quick-capture
windowrulev2 = float,        title:^(QuickCapture)$
windowrulev2 = size 900 600, title:^(QuickCapture)$
windowrulev2 = center,       title:^(QuickCapture)$
"""
# The user must add this to ~/.config/hypr/hyprland.conf manually
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rich Prompt.ask for all input | prompt_toolkit for multiline, Rich for display | Design choice | Rich only supports single-line; prompt_toolkit required for multiline |
| Custom LLM API server | opencode run with wiki-query skill | 2026-05-09 | No server to maintain; leverages existing LLM config and wiki context |
| New database per project | Extend nexus.db with new tables | Design choice | Single source of truth; Nexus UI already reads from this DB |
| Manual Hyprland config | Script to generate config + docs | Design choice | Reduce setup friction; user still adds manually for safety |

**Deprecated/outdated:**
- Textual for simple input: Too heavy for a capture window that must appear in <1s. Use prompt_toolkit instead.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | opencode run --format json returns parseable JSON with enrichment content | Architecture Patterns | Need to parse as text or adjust enrichment strategy |
| A2 | Ghostty warm start is <500ms, keeping total capture time <5s | Common Pitfalls | May need daemon/socket pre-warm if cold starts are too slow |
| A3 | Nexus db.ts uses WAL mode and busy_timeout is compatible with concurrent Python writes | Common Pitfalls | May need to add busy_timeout to Python connections only |
| A4 | opencode run can be invoked from within any directory (not just project directories) | Architecture Patterns | May need to set --dir flag or cd to a project directory |
| A5 | The capture CLI can be invoked as `uv run --directory ~/repositories/quick-capture quick-capture` | Architecture Patterns | May need to adjust entry point in pyproject.toml |
| A6 | ty is available and suitable for type checking (project constraint from modern-python skill) | Standard Stack | Standard fallback: use mypy or skip type checking |

## Open Questions

1. **opencode run --format json output format**
   - What we know: opencode run supports `--format json` flag; the Nexus API already uses it in `opencode.ts` to capture session IDs
   - What's unclear: Exact JSON schema of the output (is it streaming JSONL? a single JSON object? what fields are included?)
   - Recommendation: Test `opencode run --format json "test"` on the actual system before finalizing the enrichment parser. Examine existing opencode logs in `~/.local/share/opencode/runs/`

2. **wiki-query skill invocation from opencode run**
   - What we know: wiki-query is a skill available in the opencode config; it reads wiki/hot.md and wiki/index.md
   - What's unclear: Whether opencode run automatically loads project skills, or if `--agent` flag or directory matters
   - Recommendation: Test `opencode run --format json "what do you know about X"` from within the quick-capture project directory to verify wiki-query activation

3. **Enrichment execution model**
   - What we know: ENRI-05 says user can trigger "process-now" flag for immediate enrichment
   - What's unclear: Should process-now keep the terminal open (showing progress) or save-and-then-enrich-in-background?
   - Recommendation: Save first, then optionally enrich. Terminal closes immediately. Process-now launches a detached subprocess.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All Python code | ✓ | 3.14.4 | — |
| uv | Package management | ✓ | 0.11.3 | — |
| ruff | Linting/formatting | ✓ | 0.15.11 | — |
| Ghostty | Terminal emulator | ✓ | — | Alacritty/Kitty (window rules differ) |
| Hyprland | Window manager | ✓ | 0.54.3 | — |
| SQLite (in Python) | Database access | ✓ | 3.53.0 | — |
| opencode CLI | LLM enrichment | ✓ | 1.14.41 | — |
| hyprctl | Window management testing | ✓ | — | — |
| Node.js | Nexus web UI | ✓ | — (nexus uses it) | — |
| better-sqlite3 | Nexus DB access | ✓ | ^12.0.0 | — |

**Missing dependencies with no fallback:**
- None — all dependencies are available.

**Missing dependencies with fallback:**
- None — all dependencies are installed and compatible.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (per modern-python skill) |
| Config file | pyproject.toml [tool.pytest] |
| Quick run command | `uv run pytest tests/ -x` |
| Full suite command | `uv run pytest tests/ --cov=quick_capture --cov-fail-under=80` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAPT-01 | Hotkey triggers floating terminal | manual-only (Hyprland config) | — | ❌ Wave 0 |
| CAPT-02 | Multiline text input in floating terminal | unit | `uv run pytest tests/test_cli.py::test_multiline_input -x` | ❌ Wave 0 |
| CAPT-03 | Save and close without confirmation | unit | `uv run pytest tests/test_cli.py::test_save_exits -x` | ❌ Wave 0 |
| CAPT-04 | Terminal auto-closes after save | manual-only (integration) | — | ❌ Wave 0 |
| STOR-01 | Entry saved to SQLite with text, timestamp, status | unit | `uv run pytest tests/test_db.py::test_save_capture -x` | ❌ Wave 0 |
| STOR-02 | New tables in nexus.db, not modifying existing | unit | `uv run pytest tests/test_db.py::test_new_tables_only -x` | ❌ Wave 0 |
| ENRI-01 | LLM enrichment runs via opencode run | integration | `uv run pytest tests/test_enrich.py::test_enrich_capture -x` | ❌ Wave 0 |
| ENRI-02 | Original text preserved alongside enriched version | unit | `uv run pytest tests/test_db.py::test_original_text_preserved -x` | ❌ Wave 0 |
| ENRI-03 | Classification into Task/Idea/Reference/Question | unit | `uv run pytest tests/test_enrich.py::test_bucket_classification -x` | ❌ Wave 0 |
| ENRI-04 | Wiki-query used for context in enrichment | integration | `uv run pytest tests/test_enrich.py::test_wiki_context_used -x` | ❌ Wave 0 |
| ENRI-05 | User can trigger enrichment immediately (process-now) | unit | `uv run pytest tests/test_enrich.py::test_process_now_flag -x` | ❌ Wave 0 |
| REVW-01 | Nexus web UI displays enriched entries | integration | manual + `uv run pytest tests/test_db.py::test_api_routes -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x`
- **Per wave merge:** `uv run pytest tests/ --cov=quick_capture`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` — shared fixtures (temp DB, mock captures)
- [ ] `tests/test_db.py` — covers STOR-01, STOR-02
- [ ] `tests/test_cli.py` — covers CAPT-02, CAPT-03
- [ ] `tests/test_enrich.py` — covers ENRI-01, ENRI-03, ENRI-04, ENRI-05
- [ ] Framework install: `uv add --group dev pytest pytest-cov` — Wave 0

## Security Domain

> security_enforcement not explicitly disabled in config; including this section.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local-only tool, no auth needed |
| V3 Session Management | no | Single-shot capture, no sessions |
| V4 Access Control | no | Single-user local tool |
| V5 Input Validation | yes | prompt_toolkit handles keyboard input; validate text length/encoding before DB write |
| V6 Cryptography | no | No crypto needed; local SQLite |
| V7 Error Handling | yes | Handle DB write failures, opencode subprocess errors gracefully |
| V9 Communication | no | No network communication (except opencode run subprocess) |

### Known Threat Patterns for Python CLI + SQLite

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection | Tampering | Parameterized queries (never string concatenation) |
| Command injection (opencode run) | Tampering, Elevation | Sanitize capture text before passing to subprocess; avoid shell=True |
| Path traversal | Tampering | Use Path.resolve() for nexus.db path; never accept paths from user input |
| DoS via large input | Denial | Limit capture text size (reasonable max like 10KB) |

## Sources

### Primary (HIGH confidence)
- `/textualize/rich` (Context7) - Rich API, Prompt.ask capabilities and limitations
- `/prompt-toolkit/python-prompt-toolkit` (Context7) - multiline input, key bindings, PromptSession
- `/astral-sh/uv` (Context7) - uv project setup, PEP 723 scripts, dependency management
- quickask.py (local codebase) - Hyprland floating terminal, Ghostty window rules, Rich TUI pattern
- nexus/server/db.ts (local codebase) - SQLite schema, better-sqlite3 patterns, WAL mode, insert/update conventions
- nexus/server/api/opencode.ts (local codebase) - opencode run invocation pattern
- nexus/shared/schema.ts (local codebase) - Zod schema pattern, ID generation, datetime handling

### Secondary (MEDIUM confidence)
- Nexus web app (Alpine.js + Hono) - API patterns, frontend component structure
- wiki-query skill (local) - OpennCode skill structure, wiki context retrieval
- Python 3.11+ stdlib sqlite3 docs - Connection management, WAL mode, busy_timeout

### Tertiary (LOW confidence)
- Exact opencode run --format json output schema (needs manual testing)
- opencode run skill loading from non-project directories (needs testing)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified locally or via Context7
- Architecture: HIGH - Proven patterns from quickask.py and existing Nexus codebase
- Pitfalls: HIGH - Based on direct code inspection and known SQLite concurrency patterns
- Capture TUI: HIGH - prompt_toolkit docs confirm multiline + key bindings
- Enrichment: MEDIUM - opencode run output format needs empirical verification
- Nexus UI extension: MEDIUM - Nexus codebase examined but extension not yet tested

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (stable — no fast-moving dependencies)