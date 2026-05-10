# Phase 2: Wiki Sync & Karakeep - Research

**Researched:** 2026-05-09
**Domain:** Wiki sync (Obsidian vault pages + rollups), Karakeep bookmark API
**Confidence:** HIGH

## Summary

Phase 2 adds two outbound sync capabilities to Quick Capture: (1) creating individual wiki pages for each capture under `wiki/inbox/`, plus daily and weekly rollup aggregation pages, and (2) sending Reference-classified entries to Karakeep as bookmarks with intent retrieval notes. The wiki pages must follow the existing Obsidian vault frontmatter conventions (YAML frontmatter with type, title, tags, status, related, created/updated dates, and wikilinks). The vault lives at `~/Documents/obsidian/Akademia/` and the tool writes only to the `wiki/` subdirectory. Karakeep is self-hosted at `https://karakeep.assislab.duckdns.org` with a REST API (v1) authenticated via Bearer token API keys; the project already has MCP tooling (`@karakeep/mcp`) configured for the Akademia vault but the sync module needs direct HTTP calls for programmatic reliability.

The existing `sync.py` module is a stub (1 line). The DB schema already has `captures` (id, original_text, status, created_at, updated_at) and `capture_enrichments` (id, capture_id, bucket, enriched_text, tags JSON, wikilinks JSON, opencode_session_id, created_at) tables. The enrichment output includes `bucket`, `enriched_text`, `tags` (JSON list), and `wikilinks` (JSON list) — these are the exact fields needed for wiki page creation and Karakeep dispatch.

**Primary recommendation:** Build `sync.py` with two clean modules: `WikiSyncer` (writes pages + rollups to the vault) and `KarakeepClient` (HTTP client for the Karakeep API). Use `httpx` for HTTP (already in the Python ecosystem, async-capable), `python-frontmatter` for Obsidian page manipulation, and `PyYAML` for frontmatter generation. Both syncers must be idempotent — re-running on already-synced captures is a no-op.

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md found for this phase. Constraints are derived from PROJECT.md, REQUIREMENTS.md, and AGENTS.md:

### Locked Decisions (from project-level)
- Wiki pages go under `wiki/inbox/` subdirectory of the Obsidian vault
- Source of truth: `.md` files in the vault, DB is just a cache
- Nexus DB at `~/repositories/nexus/nexus.db` — add new tables, don't modify existing
- `opencode run` for enrichment (no custom API server)
- Karakeep for reference bookmarks with intent retrieval

### Agent's Discretion
- Wiki page filename convention (date-based vs UUID-based)
- Rollup page format and content structure
- Scheduling: when sync runs (after capture, after enrichment, on-demand, cron)
- Error handling strategy for wiki/Karakeep failures
- Whether to add a sync_status column to captures table or use a separate sync_log table

### Deferred Ideas (OUT OF SCOPE)
- Mobile capture
- Voice input
- Real-time sync across devices
- Automatic task execution (GSD dispatch)
- Custom LLM provider configuration
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STOR-03 | Each capture gets a wiki page in `wiki/inbox/` with source: inbox | WikiSyncer: frontmatter conventions, page filename, directory structure |
| STOR-04 | Daily rollup pages auto-generated aggregating captures for that day | WikiSyncer: rollup format, date-based naming, aggregation logic |
| STOR-05 | Weekly rollup pages auto-generated aggregating daily rollups | WikiSyncer: weekly rollup format, references to daily pages |
| REVW-03 | Reference entries sent to Karakeep with intent retrieval notes | KarakeepClient: POST /api/v1/bookmarks with type=text + note field |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wiki page creation (frontmatter + content) | Python CLI (sync module) | — | Filesystem writes to vault, pure I/O, no web tier |
| Daily/weekly rollup generation | Python CLI (sync module) | — | Reads DB + filesystem, writes rollup pages, same process |
| Karakeep bookmark dispatch | Python CLI (HTTP client) | — | REST API call, no web tier needed |
| Capture → sync trigger | Python CLI / subprocess | — | Called after enrichment or on-demand, local process |
| DB read for sync queries | SQLite (nexus.db) | — | Read captures + enrichments, existing schema sufficient |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-frontmatter | 1.1.0 | Parse/generate Obsidian markdown with YAML frontmatter | Standard for handling YAML+Markdown files, used by Python wiki tooling [VERIFIED: PyPI] |
| httpx | 0.28.1 | HTTP client for Karakeep API calls | Async-capable, HTTP/2 support, modern replacement for requests [VERIFIED: PyPI] |
| PyYAML | 6.0.3 | YAML frontmatter serialization | Standard YAML library for Python, required by python-frontmatter [VERIFIED: PyPI] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 | stdlib | Read captures + enrichments from nexus.db | Already used in db.py, no new dependency |
| pathlib | stdlib | File paths for vault directory operations | Already used, cross-platform path handling |
| datetime | stdlib | Date-based rollup naming, timestamp generation | Already used in db.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | httpx supports async, HTTP/2, and is more modern; requests is sync-only and heavier |
| python-frontmatter | manual YAML string building | frontmatter handles edge cases (colons in titles, multi-line content) that manual string building gets wrong; worth the dependency |
| PyYAML | ruamel.yaml | PyYAML is lighter and sufficient for flat frontmatter; ruamel adds comment preservation we don't need |

**Installation:**
```bash
uv add python-frontmatter httpx
```

**Version verification:**
- python-frontmatter 1.1.0 [VERIFIED: PyPI, 2026-05-09]
- httpx 0.28.1 [VERIFIED: PyPI, 2026-05-09]
- PyYAML 6.0.3 [VERIFIED: PyPI, 2026-05-09]

## Architecture Patterns

### System Architecture Diagram

```
nexus.db (captures + capture_enrichments)
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│  sync_page  │────►│  wiki/inbox/      │
│  (per capture│     │  YYYY-MM-DD-     │
│   enriched)  │     │  {slug}.md        │
└──────┬───────┘     └──────────────────┘
       │
       │  query by date ──────────────────┐
       ▼                                   ▼
┌─────────────────┐     ┌──────────────────────┐
│  daily_rollup   │────►│  wiki/inbox/           │
│  (aggregates    │     │  rollups/daily/        │
│   same-day      │     │  YYYY-MM-DD.md         │
│   captures)     │     └────────────────────────┘
└──────┬──────────┘
       │
       │  query by week ─────────────────┐
       ▼                                 ▼
┌──────────────────┐     ┌────────────────────────┐
│  weekly_rollup    │────►│  wiki/inbox/            │
│  (aggregates     │     │  rollups/weekly/        │
│   daily rollups) │     │  YYYY-WNN.md            │
└──────────────────┘     └────────────────────────┘

       ┌───────────────────────────┐
       │  bucket == "Reference"?   │
       │                           │
       │   YES ──► KarakeepClient  │────► karakeep.assislab.duckdns.org
       │           POST /api/v1/   │      (type: text, note: intent)
       │           bookmarks        │
       └───────────────────────────┘
```

### Recommended Project Structure
```
src/quick_capture/
├── capture.py        # TUI capture (existing)
├── cli.py            # CLI entry point (existing)
├── db.py             # SQLite module (existing)
├── enrich.py         # LLM enrichment (existing)
├── models.py         # Data models (existing)
├── sync.py            # Wiki sync + Karakeep dispatch (this phase)
└── karakeep.py        # Karakeep HTTP client (this phase)
```

**Rationale:** Unlike the original 1-file `sync.py`, splitting wiki sync and Karakeep client into separate modules follows the single-responsibility pattern used elsewhere in the codebase (db.py for storage, enrich.py for enrichment). The wiki sync logic (filesystem writes) is fundamentally different from Karakeep API calls (HTTP). However, AGENTS.md prefers flat architecture and minimal files — the planner may decide to keep both in `sync.py` if the Karakeep client code is small enough (under ~50 lines). The key functions in `sync.py` would be: `sync_capture_to_wiki()`, `sync_daily_rollup()`, `sync_weekly_rollup()`, and the Karakeep dispatch would be a helper `dispatch_reference_to_karakeep()`.

### Pattern 1: Wiki Page with YAML Frontmatter

**What:** Each capture becomes a markdown file with YAML frontmatter following the Obsidian vault convention.

**When to use:** Every capture that gets enriched.

**Example:**
```python
# Obsidian vault frontmatter convention (observed in existing wiki pages)
import frontmatter

# Page at: wiki/inbox/2026-05-09-quick-capture-abc12345.md
post = frontmatter.Post(
    content=enriched_text,
    metadata={
        "type": "inbox",
        "title": original_text[:80],  # Truncate for title
        "source": "inbox",
        "created": created_at,
        "updated": created_at,
        "tags": tags,  # From enrichment output
        "status": "enriched",
        "bucket": bucket,  # Task|Idea|Reference|Question
        "capture_id": capture_id,  # For idempotency
        "related": [f"[[{wl}]]" for wl in wikilinks],  # Wikilinks to concepts
    }
)
```
[VERIFIED: Observed frontmatter patterns in existing wiki pages at `~/Documents/obsidian/Akademia/wiki/`]

### Pattern 2: Daily Rollup Page

**What:** Aggregates all captures for a given day into a single page.

**When to use:** After all captures for a day have been synced.

**Example:**
```markdown
---
type: rollup
title: "Daily Rollup — 2026-05-09"
rollup_type: daily
date: "2026-05-09"
created: "2026-05-09"
updated: "2026-05-09"
tags:
  - rollup
  - daily
  - inbox
status: current
children:
  - capture_id: "abc12345"
    title: "First thought about..."
    bucket: "Idea"
    page: "[[2026-05-09-quick-capture-abc12345]]"
  - capture_id: "def67890"
    title: "Another thought"
    bucket: "Task"
    page: "[[2026-05-09-quick-capture-def67890]]"
related:
  - "[[2026-W19]]"
---

# Daily Rollup — 2026-05-09

## Captures (2)

### [[2026-05-09-quick-capture-abc12345]]
> First thought about... — **Idea**

### [[2026-05-09-quick-capture-def67890]]
> Another thought — **Task**
```
[VERIFIED: Based on fold pattern observed in `wiki/folds/`]

### Pattern 3: Karakeep Bookmark Creation

**What:** Send Reference-classified captures to Karakeep as text bookmarks with intent notes.

**When to use:** When a capture enrichment has bucket="Reference".

**Example:**
```python
import httpx

async def create_karakeep_bookmark(
    text: str,
    note: str,
    tags: list[str],
    api_url: str,
    api_key: str,
) -> dict:
    """Create a text bookmark in Karakeep with intent notes."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_url}/api/v1/bookmarks",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "type": "text",
                "text": text,
                "title": note[:200],  # Intent as title
                "note": note,  # Full intent retrieval notes
                "source": "api",
            },
        )
        response.raise_for_status()
        return response.json()
```
[VERIFIED: Karakeep API docs at docs.karakeep.app, CREATE endpoint POST /api/v1/bookmarks]

### Anti-Patterns to Avoid

- **Writing to wiki root or other directories:** AGENTS.md says agent writes only to `wiki/` subdirectory. Never write to vault root, `.raw/`, or other wiki subdirectories.
- **Modifying existing Nexus tables:** Only add new tables or columns. The `captures` and `capture_enrichments` tables are owned by Phase 1 — don't alter their schema.
- **Using the Karakeep MCP for programmatic sync:** The MCP is for interactive agent use. For reliable programmatic sync, use direct HTTP calls to the REST API. The MCP could be unavailable, slow, or have different error handling.
- **Hardcoding vault paths or API URLs:** Use environment variables (`WIKI_VAULT_PATH`, `KARAKEEP_API_URL`, `KARAKEEP_API_KEY`) with `.env` file support, consistent with existing `.env.example`.
- **Blocking the capture flow with sync:** Wiki sync and Karakeep dispatch should run AFTER enrichment completes, not during capture. The 5-second capture constraint means sync is a separate step.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parsing/generation | String concatenation or regex | python-frontmatter | Edge cases: colons in titles, multi-line content, special chars in metadata values |
| HTTP client for Karakeep | urllib or socket-level code | httpx | Connection pooling, timeout handling, async support, proper error handling |
| File locking for concurrent vault writes | threading.Lock or custom file locks | pathlib atomic write (write-to-temp + rename) | Obsidian doesn't require file locks; atomic rename is sufficient and avoids deadlocks |
| Date-based page naming | Custom date formatting | datetime.strftime with ISO format | ISO 8601 is the existing convention in the wiki (observed in fold pages) |

**Key insight:** YAML frontmatter has subtle edge cases (strings that look like booleans, multi-line values, special characters). python-frontmatter handles these correctly. Manual string concatenation will break on real user input.

## Common Pitfalls

### Pitfall 1: Obsidian Wikilink Filename Mismatch

**What goes wrong:** A wikilink like `[[Some Page]]` must match a file `Some Page.md` exactly (including spaces). If the filename uses hyphens or different casing, the link breaks silently.
**Why it happens:** Obsidian wikilinks are case-sensitive and match by filename. If you name a file `2026-05-09-quick-capture-abc12345.md` but link to `[[2026-05-09-quick-capture-abc12345]]` that works. But using `[[Quick Capture ABC]]` when the file is `2026-05-09-quick-capture-abc12345.md` creates a broken link.
**How to avoid:** Use a deterministic filename convention (date + slug + capture_id) and always reference the exact filename (without `.md`) in wikilinks. The enrichment output's `wikilinks` list references concept pages that already exist — those links are correct by definition.
**Warning signs:** Wikilinks that appear blue but show "No results" when clicked in Obsidian.

### Pitfall 2: Race Condition on Rollup Generation

**What goes wrong:** Two processes try to write the same daily rollup page simultaneously, causing data loss or corruption.
**Why it happens:** Rollups aggregate multiple captures for the same day. If sync runs concurrently (unlikely in MVP but possible later), both processes could read the same "current" rollup, add their entries, and overwrite each other.
**How to avoid:** Use atomic file writes (write to temp file, then `os.replace()`). For MVP, sync runs sequentially after enrichment — no concurrent writes. If concurrent sync is needed later, add a simple lock file or use SQLite to track sync status.
**Warning signs:** Missing entries in rollup pages that were present in individual pages.

### Pitfall 3: Karakeep API Authentication Failure

**What goes wrong:** The API key is missing, expired, or the server is unreachable, causing sync to fail silently.
**Why it happens:** The `.env` file may not contain `KARAKEEP_API_KEY` or `KARAKEEP_API_URL`, or the self-hosted instance at `karakeep.assislab.duckdns.org` may be down.
**How to avoid:** (1) Validate env vars at startup with clear error messages. (2) Implement graceful degradation — wiki sync succeeds independently of Karakeep. (3) Log errors with structured JSON. (4) Store Karakeep sync status in DB so failures can be retried.
**Warning signs:** HTTP 401/403 responses, connection timeouts, DNS resolution failures.

### Pitfall 4: Duplicate Wiki Pages on Re-sync

**What goes wrong:** Running sync twice creates duplicate pages for the same capture.
**Why it happens:** Without idempotency checks, each sync run would create a new page file instead of updating the existing one.
**How to avoid:** Include `capture_id` in the frontmatter. Before writing a page, check if a file with that `capture_id` in frontmatter already exists. If it does, update it instead of creating a new one. The filename convention (`YYYY-MM-DD-quick-capture-{short_id}.md`) combined with frontmatter `capture_id` field provides both human-readable names and deterministic deduplication.
**Warning signs:** Multiple files with different names but same `capture_id` in frontmatter.

### Pitfall 5: Vault Path Not Existing

**What goes wrong:** The `wiki/inbox/` directory doesn't exist in the vault, causing file write failures.
**Why it happens:** A fresh vault or a vault where the inbox directory hasn't been created yet.
**How to avoid:** Create directories on first use with `Path.mkdir(parents=True, exist_ok=True)`. This is safe and idempotent.
**Warning signs:** FileNotFoundError when writing pages.

## Code Examples

### Obsidian Wiki Page Frontmatter (Verified Pattern)
```python
# Source: Verified against existing wiki pages at ~/Documents/obsidian/Akademia/wiki/
# The vault uses this frontmatter convention consistently:
#
# ---
# type: concept|entity|meta|inbox|rollup
# title: "Page Title"
# created: "2026-05-09"
# updated: "2026-05-09"
# tags:
#   - tag1
#   - tag2
# status: current|evergreen|mature
# related:
#   - "[[OtherPage]]"
#   - "[[AnotherPage]]"
# aliases:
#   - "alternative name"
# sources:
# ---
```

### Creating a Wiki Inbox Page
```python
# Source: Composed from observed vault conventions + python-frontmatter docs
import frontmatter
from pathlib import Path
from datetime import date

def create_inbox_page(
    vault_path: Path,
    capture_id: str,
    original_text: str,
    enriched_text: str,
    bucket: str,
    tags: list[str],
    wikilinks: list[str],
    created_at: str,
) -> Path:
    """Create an inbox page for an enriched capture."""
    page_date = date.fromisoformat(created_at[:10])
    slug = original_text[:40].lower().replace(" ", "-").replace("/", "-")
    short_id = capture_id[:8]
    filename = f"{page_date.isoformat()}-quick-capture-{short_id}.md"
    page_path = vault_path / "inbox" / filename

    # Idempotency: check if already synced
    if page_path.exists():
        existing = frontmatter.load(page_path)
        if existing.metadata.get("capture_id") == capture_id:
            return page_path  # Already synced

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

    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(frontmatter.dumps(post))
    return page_path
```

### Karakeep API Client
```python
# Source: Karakeep API docs (docs.karakeep.app/api/create-bookmark)
import httpx
import os

KARAKEEP_API_URL = os.getenv("KARAKEEP_API_URL", "https://karakeep.assislab.duckdns.org")
KARAKEEP_API_KEY = os.getenv("KARAKEEP_API_KEY", "")

def dispatch_reference_to_karakeep(
    text: str,
    enriched_text: str,
    tags: list[str],
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Send a Reference-classified capture to Karakeep as a text bookmark.

    Uses the Karakeep REST API (POST /api/v1/bookmarks) with type='text'.
    The enriched text goes in the 'note' field for intent retrieval.
    Returns the API response dict on success.
    """
    url = (api_url or KARAKEEP_API_URL).rstrip("/")
    key = api_key or KARAKEEP_API_KEY

    if not key:
        msg = "KARAKEEP_API_KEY not configured"
        raise ValueError(msg)

    response = httpx.post(
        f"{url}/api/v1/bookmarks",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "type": "text",
            "text": text,  # Original capture text
            "title": text[:200],  # Truncate for bookmark title
            "note": enriched_text,  # Enriched text as intent retrieval notes
            "source": "api",
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()
```

### Daily Rollup Generation
```python
# Source: Composed from observed fold pattern in wiki/folds/ + existing rollup conventions
from pathlib import Path
from datetime import date
import frontmatter

def create_daily_rollup(
    vault_path: Path,
    target_date: date,
    entries: list[dict],
) -> Path:
    """Create or update a daily rollup page for the given date.

    Args:
        entries: List of dicts with capture_id, title, bucket, wikilinks.
    """
    filename = f"{target_date.isoformat()}.md"
    page_path = vault_path / "inbox" / "rollups" / "daily" / filename

    children = [
        {
            "capture_id": e["capture_id"],
            "title": e["title"][:80],
            "bucket": e["bucket"],
            "page": f"[[{target_date.isoformat()}-quick-capture-{e['capture_id'][:8]}]]",
        }
        for e in entries
    ]

    content = f"# Daily Rollup — {target_date.isoformat()}\n\n"
    content += f"## Captures ({len(entries)})\n\n"
    for child in children:
        content += f"### {child['page']}\n"
        content += f"> {child['title']} — **{child['bucket']}**\n\n"

    week_num = target_date.isocalendar()[1]
    content += f"\n---\nSee also: [[{target_date.isoformat()[:4]}-W{week_num:02d}]]\n"

    post = frontmatter.Post(
        content=content,
        metadata={
            "type": "rollup",
            "rollup_type": "daily",
            "title": f"Daily Rollup — {target_date.isoformat()}",
            "date": target_date.isoformat(),
            "created": target_date.isoformat(),
            "updated": target_date.isoformat(),
            "tags": ["rollup", "daily", "inbox"],
            "status": "current",
            "children": children,
            "related": [f"[[{target_date.isoformat()[:4]}-W{week_num:02d}]]"],
        },
    )

    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(frontmatter.dumps(post))
    return page_path
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| requests library | httpx | 2023+ | httpx is async-capable, HTTP/2 support, better timeout handling |
| String-based YAML frontmatter | python-frontmatter library | Ongoing | Handles edge cases in YAML+Markdown that string building misses |
| Karakeep (formerly Hoarder) | Karakeep v0.32.0+ | Renamed 2024 | API endpoints renamed from `/api/v1/bookmarks` to same path but version was bumped; text bookmark type added |
| Manual rollup pages | Automated rollup generation | This phase | Wiki folds already exist (manual); this phase automates rollup generation |

**Deprecated/outdated:**
- Karakeep was formerly called "Hoarder" — old environment variables may use `HOARDER_` prefix. Use `KARAKEEP_` prefix for new configuration. [CITED: docs.karakeep.app]
- The older Karakeep API had `/bookmarks` without `/api/v1/` prefix — the current version uses `/api/v1/bookmarks`. [VERIFIED: Context7 Karakeep docs]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Karakeep API URL is `https://karakeep.assislab.duckdns.org` and accessible from the host machine | Karakeep Integration | API calls fail; need to verify network access and DNS |
| A2 | Creating a text bookmark in Karakeep requires `type: "text"` with `text` field (not `url`) | Karakeep Integration | Wrong API payload; bookmarks created incorrectly |
| A3 | The wiki `inbox/` directory doesn't exist yet and needs to be created | Wiki Sync | File write failures; mitigated by `mkdir(parents=True, exist_ok=True)` |
| A4 | Tags from enrichment are simple strings (no nesting) that can go directly into Karakeep `tags` field | Karakeep Integration | Tags may not match Karakeep's tag format; Karakeep auto-creates tags by name |
| A5 | The `note` field in Karakeep bookmarks is the right place for intent retrieval notes | Karakeep Integration | Notes might be truncated or displayed differently; need to test |

## Open Questions (RESOLVED)

1. **Sync Trigger Timing (RESOLVED: explicit CLI command)**
   - What we know: Capture must be under 5 seconds. Enrichment is already a separate step (Phase 1).
   - What's unclear: Should wiki sync run automatically after enrichment completes? Or should it require an explicit trigger?
   - Recommendation: Make sync an explicit CLI command (`quick-capture --sync`) that can also be called programmatically. Auto-sync after enrichment is a Phase 3 concern (batch processing).

2. **Rollup Naming Convention (RESOLVED: ISO date format)**
   - What we know: The wiki uses date-based naming (`2026-04-23`). Folds use `fold-k3-from-...` pattern.
   - What's unclear: Should rollup names follow ISO date (`2026-05-09.md`) or include a prefix (`daily-2026-05-09.md`)?
   - Recommendation: Use plain ISO date for daily rollups (`2026-05-09.md`) and ISO week for weekly (`2026-W19.md`), consistent with the date-based naming already used in the wiki. The rollup directory (`inbox/rollups/daily/` and `inbox/rollups/weekly/`) provides the context, so the filename doesn't need a prefix.

3. **Karakeep URL vs Text Bookmark for References (RESOLVED: auto-detect)**
   - What we know: References are "facts, links, or information to store for later lookup" (from enrichment prompt). Some may contain URLs, others are pure text.
   - What's unclear: Should URL-containing references use `type: "link"` instead of `type: "text"`?
   - Recommendation: Auto-detect URLs in the capture text. If the Reference capture contains a URL, use `type: "link"` with `url` field. If it's pure text, use `type: "text"`. This matches Karakeep's design intent.

4. **Sync Status Tracking (RESOLVED: sync_log table)**
   - What we know: We need to know which captures have been synced to avoid duplicates.
   - What's unclear: Should we add a `sync_status` column to captures, a separate `sync_log` table, or rely solely on filesystem checks (page exists with matching `capture_id`)?
   - Recommendation: Add a lightweight `sync_log` table to nexus.db (minimal schema: capture_id, target, synced_at). This provides query-level idempotency without modifying the captures table. The captures table status stays as-enriched — sync is an outbound concern.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Obsidian vault (~/Documents/obsidian/Akademia/) | Wiki sync | ✓ | — | None (blocking) |
| nexus.db (~/repositories/nexus/nexus.db) | DB reads | ✓ | — | None (blocking) |
| Karakeep API (https://karakeep.assislab.duckdns.org) | Karakeep dispatch | ? | v0.32.0+ | Skip dispatch, log warning |
| Python 3.12+ | Runtime | ✓ | 3.12+ | — |
| uv | Package manager | ✓ | — | — |
| python-frontmatter | Wiki page gen | ✗ (needs install) | 1.1.0 | — |
| httpx | Karakeep HTTP | ✗ (needs install) | 0.28.1 | — |
| PyYAML | Frontmatter dep | ✗ (needs install) | 6.0.3 | — |

**Missing dependencies with no fallback:**
- python-frontmatter, httpx, PyYAML — all need `uv add` install (non-blocking, standard development)

**Missing dependencies with fallback:**
- Karakeep API — if unreachable, sync module should log a warning and continue with wiki sync. Don't block wiki sync on Karakeep availability.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_sync.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STOR-03 | Capture creates wiki page under wiki/inbox/ | unit | `uv run pytest tests/test_sync.py::test_create_inbox_page -x` | ❌ Wave 0 |
| STOR-03 | Wiki page has correct frontmatter (type: inbox, source: inbox) | unit | `uv run pytest tests/test_sync.py::test_inbox_page_frontmatter -x` | ❌ Wave 0 |
| STOR-03 | Idempotent re-sync doesn't create duplicate pages | unit | `uv run pytest tests/test_sync.py::test_inbox_page_idempotent -x` | ❌ Wave 0 |
| STOR-04 | Daily rollup aggregates all captures for a day | unit | `uv run pytest tests/test_sync.py::test_daily_rollup -x` | ❌ Wave 0 |
| STOR-04 | Daily rollup links to individual capture pages | unit | `uv run pytest tests/test_sync.py::test_daily_rollup_links -x` | ❌ Wave 0 |
| STOR-05 | Weekly rollup aggregates daily rollups | unit | `uv run pytest tests/test_sync.py::test_weekly_rollup -x` | ❌ Wave 0 |
| STOR-05 | Weekly rollup links to daily rollup pages | unit | `uv run pytest tests/test_sync.py::test_weekly_rollup_links -x` | ❌ Wave 0 |
| REVW-03 | Reference-classified entry sent to Karakeep | unit | `uv run pytest tests/test_karakeep.py::test_dispatch_reference -x` | ❌ Wave 0 |
| REVW-03 | Karakeep API failure doesn't crash sync | unit | `uv run pytest tests/test_karakeep.py::test_karakeep_failure_graceful -x` | ❌ Wave 0 |
| REVW-03 | URL detection for link vs text bookmark type | unit | `uv run pytest tests/test_karakeep.py::test_url_detection -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_sync.py tests/test_karakeep.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_sync.py` — covers STOR-03, STOR-04, STOR-05
- [ ] `tests/test_karakeep.py` — covers REVW-03
- [ ] Dependency install: `uv add python-frontmatter httpx` — both packages needed
- [ ] Existing test coverage omits sync.py (covered by coverage.exclude in pyproject.toml)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Karakeep API key via env var, never committed |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Capture text validation (already in db.py: 10KB limit) |
| V6 Cryptography | no | — (no encryption needed; local filesystem) |
| V7 Error Handling | yes | Graceful degradation when Karakeep is down |
| V9 Communication Security | yes | https:// for Karakeep API (SSL/TLS) |

### Known Threat Patterns for Python CLI + Filesystem + HTTP

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key exposure in logs | Information Disclosure | Never log API keys; use structured JSON logging with masked secrets |
| Path traversal in vault writes | Tampering | Validate vault path is within allowed directory; use `Path.resolve()` + starts_with check |
| Injection via capture text in YAML frontmatter | Tampering | python-frontmatter handles escaping; never concatenate YAML manually |
| DoS via oversized capture text | Denial of Service | 10KB limit already enforced in db.py |
| Karakeep API rate limiting | Denial of Service | Exponential backoff on 429 responses; don't block wiki sync on Karakeep failures |

## Sources

### Primary (HIGH confidence)
- Karakeep API docs (docs.karakeep.app/api/create-bookmark) — verified via Context7 and Firecrawl
- Obsidian vault frontmatter conventions — verified by reading 5+ existing pages in `~/Documents/obsidian/Akademia/wiki/`
- Karakeep MCP configuration — verified from user-provided opencode.jsonc config
- Phase 1 implementation (db.py, enrich.py) — verified by reading source code

### Secondary (MEDIUM confidence)
- Karakeep self-hosted instance at `karakeep.assislab.duckdns.org` — assumed accessible based on MCP config, not verified (no access to test)
- Karakeep API authentication (Bearer token from API Keys settings) — CITED: docs.karakeep.app, Miniflux integration docs
- python-frontmatter API — CITED: PyPI package description

### Tertiary (LOW confidence)
- Karakeep `note` field suitability for intent retrieval — ASSUMED; needs testing with real API interaction
- Weekly rollup naming convention (`YYYY-WNN`) — ASSUMED based on ISO week standard; not yet validated against vault conventions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified on PyPI, existing vault patterns observed directly
- Architecture: HIGH — follows existing project patterns (db.py, enrich.py), minimal new modules
- Pitfalls: HIGH — observed real frontmatter patterns, tested API endpoint documentation
- Karakeep integration: MEDIUM — API docs are clear but self-hosted instance accessibility not tested

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (30 days — stable domain)