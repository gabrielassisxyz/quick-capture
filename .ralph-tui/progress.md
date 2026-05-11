# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

- **Module-level env vars**: Constants like `KARAKEEP_API_URL = os.environ.get(...)` are set at import time. Tests must `patch("module.CONSTANT", value)` rather than `patch.dict("os.environ", ...)` to override them.
- **Sync pattern**: `sync_*` functions wrap `dispatch_*` in try/except, call `log_sync()` on success, return `None` on failure. Matches wiki sync pattern in `sync.py`.
- **httpx for HTTP**: Project uses `httpx` (not `requests`) for HTTP calls. Use `httpx.post(..., timeout=30.0)` with `raise_for_status()`.
- **Test env isolation**: Module-level constants read from `os.environ` at import; mock the module attribute directly, not the env dict.
- **Karakeep dispatch isolation**: `sync_capture_to_wiki` calls Karakeep dispatch AFTER the wiki try/except block so that Karakeep failures (including unexpected ones) cannot prevent wiki sync from succeeding. The `sync_reference_to_karakeep` wrapper catches expected errors and returns None; any unexpected errors bubble up but don't affect the already-completed wiki path.
- **Cross-module patching order**: When patching both a module-level constant and `httpx.post` in `quick_capture.karakeep`, decorators stack bottom-up — place `KARAKEEP_API_KEY` decorator first (outer), `httpx.post` second (inner).

---

## 2026-05-11 - quick-capture-66h.2
- Created `src/quick_capture/karakeep.py` with `dispatch_reference_to_karakeep` and `sync_reference_to_karakeep`
- Created `tests/test_karakeep.py` with 25 tests covering all acceptance criteria
- Acceptance: URL detection via `_URL_PATTERN`, text/link bookmark types, Bearer auth, timeout=30.0, ValueError on missing key, graceful degradation on HTTP/Connect/Value errors, API key never in logs, env var defaults
- **Learnings:**
  - Module-level env vars (`KARAKEEP_API_URL`, `KARAKEEP_API_KEY`) need `patch("module.ATTR", value)` in tests, not `patch.dict("os.environ", ...)`
  - `httpx.post` URL is a positional arg (first), not a kwarg — test assertions need `call_args.args[0]`
  - `ruff` SIM117: use single `with` statement instead of nested `with` for multiple context managers
  - `ruff` PT017: use `pytest.raises()` instead of try/except + assert on exception
  - `ruff` PT011: `pytest.raises(ValueError)` needs `match=` parameter
  - `ruff` S105: test hardcoded passwords need `noqa: S105`

## 2026-05-11 - quick-capture-66h.1
- Modified `src/quick_capture/sync.py` to import and call `sync_reference_to_karakeep` for Reference-classified captures after wiki sync
- Added `TestSyncCaptureToWikiKarakeep` class in `tests/test_sync.py` with 4 tests
- Acceptance: Reference dispatch, non-Reference skip, sync_log karakeep target, wiki success on Karakeep failure
- **Learnings:**
  - Karakeep dispatch must run AFTER wiki try/except (not inside) to isolate failure domains — otherwise unexpected errors from Karakeep would cause wiki sync to return None
  - `sync_capture_to_wiki` now returns `Path` on wiki success even when Karakeep dispatch returns None
  - When testing cross-module integration, must patch `KARAKEEP_API_KEY` at the `quick_capture.karakeep` module level before `httpx.post`
---