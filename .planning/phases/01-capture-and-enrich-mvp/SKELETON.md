# Walking Skeleton: Quick Capture

**Phase:** 1 — Capture & Enrich MVP
**Created:** 2026-05-09

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.11+ | Project constraint from modern-python skill; stdlib sqlite3, subprocess |
| Package manager | uv | Project constraint; fast dependency resolution, PEP 735 groups |
| Linting/Formatting | ruff | Project constraint from modern-python skill |
| Type checking | ty | Project constraint from modern-python skill |
| Testing | pytest + pytest-cov | Project constraint; enforced 80% coverage |
| Terminal UI | prompt_toolkit + Rich | prompt_toolkit for multiline input (Rich can't do multiline); Rich for rendering |
| Database | SQLite (nexus.db) | Shared with Nexus; direct writes for <5s capture speed |
| DB access (Python) | sqlite3 stdlib | No external dependency needed; parameterized queries |
| DB access (Node.js) | better-sqlite3 | Existing Nexus pattern; prepared statements |
| API framework | Hono (existing) | Extends Nexus server; same patterns as sessions/projects |
| Frontend framework | Alpine.js + Tailwind v4 + DaisyUI v5 | Existing Nexus stack; no new registries |
| LLM enrichment | opencode run (subprocess) | Project constraint; leverages wiki-query skill; no custom server |
| Entry point | `quick-capture` CLI via pyproject.toml scripts | `uv run --directory ~/repositories/quick-capture quick-capture` |
| Hotkey trigger | Ghostty terminal via Hyprland keybind | Proven pattern from quickask.py |

## Directory Layout

```
quick-capture/                          # Project root
├── pyproject.toml                      # uv project config, deps, scripts, tools
├── .python-version                     # Python 3.11+
├── src/
│   └── quick_capture/
│       ├── __init__.py                 # Version string
│       ├── cli.py                      # TUI entry point (prompt_toolkit + Rich)
│       ├── db.py                       # SQLite operations (captures tables)
│       ├── enrich.py                   # opencode run subprocess enrichment
│       └── models.py                  # Data models (Capture, Enrichment, enums)
├── tests/
│   ├── conftest.py                     # Shared fixtures (temp DB, mock data)
│   ├── test_db.py                      # DB operations tests
│   ├── test_cli.py                     # CLI/TUI tests (mocked prompt)
│   └── test_enrich.py                  # Enrichment parsing tests

nexus/                                  # Existing Nexus repo (extensions)
├── shared/
│   └── schema.ts                       # ADD: CaptureSchema, CaptureEnrichmentSchema
├── server/
│   ├── index.ts                        # MODIFY: Register /api/captures route
│   ├── db.ts                           # MODIFY: Add capture DB functions
│   └── api/
│       └── captures.ts                  # NEW: GET /, GET /:id, PATCH /:id, POST /:id/enrich
├── src/
│   ├── api.js                          # MODIFY: Add capture API functions
│   ├── app.js                          # MODIFY: Add capture state + methods
│   ├── style.css                       # MODIFY: Add capture-specific styles
│   └── components/
│       └── captures.js                 # NEW: renderCaptures(), renderCaptureDetail()
```

## Key Routes

| Path | Method | Handler | Purpose |
|------|--------|---------|---------|
| `/api/captures` | GET | capturesRoute | List captures with `?status=` and `?bucket=` filters |
| `/api/captures/:id` | GET | capturesRoute | Get single capture with enrichment |
| `/api/captures/:id` | PATCH | capturesRoute | Update capture status |
| `/api/captures/:id/enrich` | POST | capturesRoute | Trigger enrichment for capture |

## Database Schema

Two new tables in existing `nexus.db`, NO modifications to existing tables:

```sql
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
```

## Dev Deployment

```bash
# Python project
cd ~/repositories/quick-capture
uv sync --all-groups           # Install all deps (prod + dev)
uv run pytest -x               # Run tests
uv run quick-capture           # Run TUI

# Nexus server (existing, extended)
cd ~/repositories/nexus
npm run server:watch            # Starts on port 3001
npm run dev                     # Vite dev server

# Hyprland hotkey (manual config)
# Add to ~/.config/hypr/hyprland.conf:
# bind = $mainMod, Q, exec, ghostty --title="QuickCapture" -e uv run --directory ~/repositories/quick-capture quick-capture
# windowrulev2 = float, title:^(QuickCapture)$
# windowrulev2 = size 900 600, title:^(QuickCapture)$
# windowrulev2 = center, title:^(QuickCapture)$
```

## Verified End-to-End Flow

1. User presses `$mainMod+Q` → Ghostty appears with Quick Capture TUI
2. User types multiline text → prompt_toolkit accepts input
3. User presses Ctrl+S → TUI saves to `nexus.db` captures table, prints confirmation, terminal exits
4. User opens Nexus web UI → "Captures" tab shows captured entry
5. User clicks "Enrich entry" → `opencode run` processes capture, stores enrichment
6. Detail panel shows original text + enrichment (bucket, tags, wikilinks)