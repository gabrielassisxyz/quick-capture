---
phase: 01-capture-and-enrich-mvp
plan: 02
subsystem: nexus-api, nexus-frontend
tags: [hono, alpine-js, zod, better-sqlite3, captures-api, captures-ui]

# Dependency graph
requires:
  - phase: 01-capture-and-enrich-mvp/01-01
    provides: Python capture CLI and SQLite schema for captures tables
provides:
  - Nexus API routes for captures CRUD (GET list, GET by ID, PATCH status)
  - Frontend Captures tab with card grid, filter bar, and slide-panel detail view
  - API client functions (getCaptures, getCapture, updateCapture, enrichCapture)
  - Alpine.js store integration with captures state and filter/view switching
affects: [nexux-web-ui, captures-viewing]

# Tech tracking
tech-stack:
  added: []
  patterns: [zod-validated-hono-routes, left-join-enrichment-hydration, alpine-store-view-switching, escapeHtml-xss-prevention, css-variable-status-colors]

key-files:
  created:
    - nexus/server/api/captures.ts
    - nexus/src/components/captures.js
  modified:
    - nexus/shared/schema.ts
    - nexus/server/db.ts
    - nexus/server/index.ts
    - nexus/src/api.js
    - nexus/src/app.js
    - nexus/index.html
    - nexus/src/style.css

key-decisions:
  - "Used LEFT JOIN with enrichment prefix (e_id, e_bucket, etc.) for getAllCaptures to avoid column name collisions between captures and capture_enrichments tables"
  - "All user-generated text escaped with escapeHtml() in captures.js cards and detail panel (threat T-02-03 mitigation)"
  - "Captures tab uses Alpine.js x-show for view switching between Projects and Captures — no router needed"
  - "Filter bar shows unprocessed count badge on 'All' filter using Alpine store computed unprocessedCount"
  - "Enrich endpoint (POST /captures/:id/enrich) defined in api.js for future use — route not yet implemented server-side (enrichment is Plan 03)"

patterns-established:
  - "LEFT JOIN hydration pattern: prefix enrichment columns (e_*) to avoid collisions, reconstruct enrichment object in mapper"
  - "View switching pattern: captureViewOpen boolean toggle between Projects and Captures views"
  - "Filter + computed pattern: filteredCaptures computed property + setCaptureFilter method on Alpine store"
  - "Slide panel reuse: captures detail panel reuses existing .slide-panel and .panel-overlay CSS classes"

---

# Phase 01 Plan 02: Nexus Capture View Summary

One-liner: Nexus Captures API (schema, DB, routes) and frontend view (cards, filters, detail panel) for browsing captured entries.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Nexus API — schema, DB functions, capture routes | f5b3403 | schema.ts, db.ts, captures.ts, index.ts |
| 2 | Nexus frontend — Captures view, API client, app integration | faddd6e | api.js, app.js, captures.js, index.html, style.css |

## Verification Results

- ✅ Nexus server starts without error
- ✅ GET /api/captures returns `[]` (empty array)
- ✅ GET /api/captures/:id returns 404 for nonexistent IDs
- ✅ Frontend builds with `npm run build` (exit 0)
- ✅ All Zod schemas export correctly (CaptureStatus, Bucket, CaptureSchema, etc.)
- ✅ All DB functions present (initCapturesTables, getAllCaptures, getCaptureById, getCapturesByBucket, createCapture, patchCapture)
- ✅ All API client functions present (getCaptures, getCapture, updateCapture, enrichCapture)
- ✅ Alpine store integration complete (captures, selectedCapture, captureFilter, captureViewOpen, computed properties)
- ✅ CSS status classes added (status-unprocessed, status-enriching, status-enriched, status-queued)
- ✅ XSS prevention: all user text rendered via escapeHtml()

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| enrichCapture API function | nexus/src/api.js | POST /captures/:id/enrich will be implemented in Plan 03 (enrichment pipeline). Frontend "Enrich entry" button calls this, but server route not yet implemented. |

## Threat Flags

No new threat surfaces beyond those documented in the plan's threat_model. All mitigations in place:
- T-02-01: Zod validation on PATCH body, parameterized queries ✅
- T-02-03: escapeHtml() on all user-generated text in HTML templates ✅