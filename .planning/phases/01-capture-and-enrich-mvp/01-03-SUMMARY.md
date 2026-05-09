---
phase: 01-capture-and-enrich-mvp
plan: 03
subsystem: enrichment
tags: [enrichment, opencode, subprocess, api, cli]
dependency_graph:
  requires: ["01-01-PLAN", "01-02-PLAN"]
  provides: [enrich-pipeline, enrich-api, enrich-cli]
  affects: [quick-capture-enrich, nexus-captures-api]
tech_stack:
  added: [argparse, subprocess.run, execSync, createEnrichment]
  patterns: [TDD, subprocess-pipeline, status-state-machine]
key_files:
  created:
    - src/quick_capture/enrich.py
    - tests/test_enrich.py
  modified:
    - src/quick_capture/cli.py
    - nexus/server/api/captures.ts
    - nexus/server/db.ts
decisions:
  - "sys.exit() mocked with side_effect=SystemExit for testability of CLI --enrich flag"
  - "Parse enrichment output uses 3-tier JSON extraction: direct parse, code fence extraction, last-line fallback"
  - "Nexus enrich endpoint uses execSync (synchronous) matching existing opencode.ts pattern"
metrics:
  duration: 4m
  completed: 2026-05-09
  tasks: 2
  files: 5
---

# Phase 01 Plan 03: Enrichment Pipeline Summary

Python enrichment module via opencode run subprocess, Nexus enrich API endpoint, and CLI --enrich flag. Captures can now be enriched via CLI or API, producing bucket classification, enriched text, tags, and wikilinks.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Python enrichment module and CLI flag | 9af6610 | enrich.py, test_enrich.py, cli.py, test_cli.py |
| 2 | Nexus enrich API endpoint | 41e6c9f | captures.ts, db.ts |

## Key Changes

### Task 1: enrich.py, test_enrich.py, cli.py

- **enrich.py**: Module with `ENRICHMENT_PROMPT` (includes wiki-query instruction per ENRI-04), `VALID_BUCKETS` set, `parse_enrichment_output()` (handles plain JSON, code-fenced JSON, mixed output), and `enrich_capture()` (full pipeline: get capture → set enriching → run subprocess → parse → save enrichment → return)
- **Security**: `subprocess.run` uses `shell=False` and list args (T-03-01 mitigation); `subprocess.TimeoutExpired` caught with 120s timeout (T-03-03); bucket validation against `VALID_BUCKETS` set (T-03-02); status resets to "unprocessed" on any failure (T-03-04)
- **cli.py**: Added `--enrich CAPTURE_ID` argument via argparse; if provided, calls `enrich_capture()` and exits; otherwise runs existing TUI flow
- **test_enrich.py**: 15 tests covering parse_enrichment_output (6 tests), ENRICHMENT_PROMPT (1 test), enrich_capture pipeline (7 tests including status transitions, timeout handling, shell=False verification), and CLI flag (2 tests)

### Task 2: Nexus enrich API endpoint

- **db.ts**: Added `createEnrichment()` function that inserts into `capture_enrichments`, updates capture status to 'enriched', and returns hydrated `CaptureWithEnrichment`
- **captures.ts**: Added `POST /:id/enrich` endpoint that: (1) gets capture by ID (404 if not found), (2) sets status to 'enriching', (3) runs `opencode run --format json` via `execSync`, (4) parses JSON output with fallback parsing, (5) validates bucket, (6) creates enrichment, (7) returns updated capture. On failure: resets status to 'unprocessed' and returns 500

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CLI test mock pattern for sys.exit**
- **Found during:** Task 1 (test_enrich_cli_flag tests)
- **Issue:** Mocking `sys.exit` without `side_effect=SystemExit` allowed execution to fall through to the TUI branch after the enrich path, causing unexpected behavior in tests
- **Fix:** Changed mock pattern to `patch.object(sys, "exit", side_effect=SystemExit)` and wrapped calls in `pytest.raises(SystemExit)`, applied to both new and existing CLI tests
- **Commit:** 9af6610

**2. [Rule 1 - Bug] Test for subprocess failure with nonexistent capture ID**
- **Found during:** Task 1 (test_resets_status_to_unprocessed_on_subprocess_failure)
- **Issue:** Test called `enrich_capture("any-id", conn=db)` which raises `ValueError` before reaching the subprocess mock
- **Fix:** Merged with the "existing capture" test case — removed the "any-id" variant since it tested the same code path as the missing capture test
- **Commit:** 9af6610

**3. [Rule 2 - Security] Explicit shell=False in subprocess.run**
- **Found during:** Task 1 (plan verification)
- **Issue:** Initial ruff lint suppressed S603 without explicitly setting `shell=False`
- **Fix:** Added `shell=False` explicitly with security comment referencing T-03-01, added test verifying list args and `shell=False`
- **Commit:** 9af6610

**4. [Rule 3 - Build] argparse argv leak in existing tests**
- **Found during:** Task 1 (test_cli.py failures)
- **Issue:** Adding argparse to `main()` caused pytest's own argv to leak into argument parsing
- **Fix:** Added `patch("sys.argv", ["quick-capture"])` to all existing CLI tests
- **Commit:** 9af6610

## Known Stubs

None — all data paths are wired end-to-end.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: subprocess-injection | src/quick_capture/enrich.py | Capture text passed as argument to subprocess (mitigated: shell=False, list args) |
| threat_flag: subprocess-injection | nexus/server/api/captures.ts | Capture text interpolated into execSync command string (mitigated: JSON.stringify for escaping) |

## Verification

- `uv run pytest tests/ -x` — all 46 Python tests pass
- `cd ~/repositories/nexus && npm run build` — Nexus builds without errors## Self-Check: PASSED
