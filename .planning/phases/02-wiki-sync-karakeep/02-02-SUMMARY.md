---
phase: 02-wiki-sync-karakeep
plan: 02
subsystem: karakeep-dispatch
tags: [karakeep, bookmarks, api, sync, references]
dependency_graph:
  requires: ["02-01-PLAN"]
  provides: [karakeep-client, dispatch-pipeline, reference-bookmarks]
tech_stack:
  added: [httpx, regex-URL-detection]
  patterns: [TDD, graceful-degradation, env-var-config]
key_files:
  created:
    - src/quick_capture/karakeep.py
    - tests/test_karakeep.py
  modified:
    - src/quick_capture/sync.py
    - tests/test_sync.py
decisions:
  - "URL detection via regex _URL_PATTERN.search(text) — no external dependency"
  - "sync_reference_to_karakeep wraps dispatch in try/except for graceful degradation"
  - "Karakeep dispatch happens inside sync_capture_to_wiki after wiki sync succeeds"
  - "KARAKEEP_API_URL defaults to http://localhost:3000 (dev-friendly), overridable via env"
metrics:
  duration: ~30m
  completed: 2026-05-12
  tasks: 2
  files: 4
---

# Phase 02 Plan 02: Karakeep Dispatch Summary

Karakeep HTTP client module and sync pipeline integration. Reference-classified captures are sent to Karakeep as bookmarks (type=text or type=link), with enriched text as the note field for intent retrieval.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Karakeep HTTP client and tests | 8cec1f3 | karakeep.py, test_karakeep.py |
| 2 | Integrate dispatch into sync pipeline | 8720b2b | sync.py, test_sync.py |

## Key Changes

### Task 1: karakeep.py, test_karakeep.py

- **karakeep.py**: Module with `dispatch_reference_to_karakeep()` (POST bookmark with auto URL detection) and `sync_reference_to_karakeep()` (wraps dispatch with graceful error handling + sync_log)
- **URL detection**: Regex-based `_URL_PATTERN.search(text)` — text with URL creates `type=link` bookmark, plain text creates `type=text`
- **Security**: `KARAKEEP_API_KEY` never logged or exposed in error messages (T-2-02); `httpx.ConnectError`, `httpx.HTTPStatusError`, and `ValueError` caught with `logger.exception` but key value masked
- **Config**: `KARAKEEP_API_URL` and `KARAKEEP_API_KEY` read from env vars, with function parameter overrides for testability
- **test_karakeep.py**: 7 tests covering text/link bookmark types, tags, missing API key error, HTTP failure propagation, key-in-log prevention, and env var default usage

### Task 2: Sync pipeline integration

- **sync.py**: `sync_capture_to_wiki()` now dispatches Reference-classified captures to Karakeep after wiki sync succeeds. Karakeep failures do not affect the wiki sync return value.
- **test_sync.py**: 4 tests in `TestKarakeepDispatch` class covering dispatch invocation for Reference captures, skip for non-Reference, sync_log recording, and graceful continuation on Karakeep failure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Build] os.replace → Path.replace lint**
- **Found during**: Post-implementation lint check
- **Issue**: `ruff` flagged `os.replace()` as PTH105, preferring `Path.replace()`
- **Fix**: Changed `os.replace(tmp_path, path)` to `Path(tmp_path).replace(path)` in `_atomic_write()`
- **Commit**: (post-summary fix commit)

**2. [Architecture] Karakeep dispatch moved inside sync_capture_to_wiki**
- **Found during**: Task 2 implementation
- **Issue**: Plan specified dispatching from `sync_all_to_wiki()` in a separate pass, but `sync_capture_to_wiki()` already had the enrichment data in scope
- **Fix**: Placed dispatch inside `sync_capture_to_wiki()` after wiki sync succeeds, using `sync_reference_to_karakeep` with graceful error handling. This is cleaner — dispatch happens per-capture in the same function that handles wiki sync.

**3. [Design] sync_reference_to_karakeep signature takes individual fields instead of row dict**
- **Found during**: Task 1 implementation
- **Issue**: Plan showed passing `enrichment=row` as a dict, but the function is more testable and explicit with individual `text`, `enriched_text`, `tags` parameters
- **Fix**: Function takes `text`, `enriched_text`, `tags` directly. Caller in sync_capture_to_wiki passes fields from enrichment dict.

## Known Stubs

None — all data paths are wired end-to-end.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: secret-in-logs | src/quick_capture/karakeep.py | KARAKEEP_API_KEY used in Bearer token header (mitigated: key excluded from log messages; test_api_key_never_in_logged_error verifies) |
| threat_flag: external-http | src/quick_capture/karakeep.py | Outbound HTTPS POST to Karakeep API with Bearer token (mitigated: env-var config, graceful degradation, timeout=30s) |

## Verification

- `uv run pytest tests/test_karakeep.py tests/test_sync.py -x -q` — all tests pass
- `uv run ruff check src/quick_capture/karakeep.py src/quick_capture/sync.py` — no lint errors
- `uv run pytest -x -q` — full test suite (97 tests) green
- `uv run python -c "from quick_capture.karakeep import dispatch_reference_to_karakeep, sync_reference_to_karakeep"` — imports succeed

## Self-Check: PASSED
