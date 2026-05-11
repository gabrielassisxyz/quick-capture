# Roadmap: Quick Capture

**Granularity:** Standard | **Mode:** MVP | **Created:** 2026-05-09

## Phase 1: Capture & Enrich MVP

**Goal:** End-to-end slice working: hotkey → multiline capture → save to DB → enrich via opencode run → view in Nexus
**Mode:** mvp
**Plans:** 3 plans
**Success Criteria:**
1. User presses Hyprland hotkey and a floating terminal appears
2. User types multiline text, presses submit, and the terminal closes
3. The raw capture is persisted in nexus.db with original text, timestamp, and status "unprocessed"
4. Running `opencode run` with the capture text produces an enriched version with bucket classification
5. The enriched entry is viewable in Nexus web UI with original text preserved

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAPT-01 | Phase 1 | ✓ Complete |
| CAPT-02 | Phase 1 | ✓ Complete |
| CAPT-03 | Phase 1 | ✓ Complete |
| CAPT-04 | Phase 1 | ✓ Complete |
| STOR-01 | Phase 1 | ✓ Complete |
| STOR-02 | Phase 1 | ✓ Complete |
| ENRI-01 | Phase 1 | ✓ Complete |
| ENRI-02 | Phase 1 | ✓ Complete |
| ENRI-03 | Phase 1 | ✓ Complete |
| ENRI-04 | Phase 1 | ✓ Complete |
| ENRI-05 | Phase 1 | ✓ Complete |
| REVW-01 | Phase 1 | ✓ Complete |

Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Capture Pipeline: Python project, DB module, TUI, Hyprland config (CAPT-01,02,03,04, STOR-01,02)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — Nexus Capture View: API routes, schema, frontend cards, detail panel (REVW-01)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-03-PLAN.md — Enrichment Pipeline: opencode run subprocess, enrich API, CLI flag (ENRI-01,02,03,04,05)

## Phase 2: Wiki Sync & Karakeep

**Goal:** Every capture lives in the wiki (individual pages + rollups) and references route to Karakeep
**Mode:** mvp
**Plans:** 2 plans
**Success Criteria:**
1. Each capture creates a wiki page under `wiki/inbox/` with proper frontmatter and source: inbox
2. Daily rollup page aggregates all captures for that day
3. Weekly rollup page aggregates daily rollups for that week
4. Reference-classified entries are sent to Karakeep with intent retrieval notes
5. Wiki pages include wikilinks to related concepts via enrichment output

| Requirement | Phase | Status |
|-------------|-------|--------|
| STOR-03 | Phase 2 | Pending |
| STOR-04 | Phase 2 | Pending |
| STOR-05 | Phase 2 | Pending |
| REVW-03 | Phase 2 | Pending |

Plans:
**Wave 1**
- [ ] 02-01-PLAN.md — Wiki sync pipeline: inbox pages, daily/weekly rollups, sync_log, CLI --sync (STOR-03, STOR-04, STOR-05)

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 02-02-PLAN.md — Karakeep dispatch: Reference bookmark creation, graceful degradation, sync integration (REVW-03)

## Phase 3: Flexible Processing

**Goal:** Enrichment can be triggered in batches or on-demand, and entries can be filtered by bucket
**Mode:** mvp
**Success Criteria:**
1. Unprocessed entries accumulate and can be batch-processed after N captures
2. User can trigger enrichment from Nexus UI for individual entries or all unprocessed
3. User can filter entries in Nexus by bucket (Task, Idea, Reference, Question)
4. Batch processing shows progress and handles partial failures gracefully
5. On-demand enrichment from TUI is available as a CLI command

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENRI-06 | Phase 3 | Pending |
| ENRI-07 | Phase 3 | Pending |
| REVW-02 | Phase 3 | Pending |

## Phase 4: Dispatch Discussion

**Goal:** User can discuss an enriched entry with the LLM before deciding to dispatch it to a project
**Mode:** mvp
**Success Criteria:**
1. User can start a discussion thread from any enriched entry in Nexus
2. LLM discussion produces a refined/developed version of the idea
3. User can mark an entry as "dispatched" to a specific project
4. Dispatched entries are linked to the project in nexus.db
5. Discussion history is preserved alongside the entry

| Requirement | Phase | Status |
|-------------|-------|--------|
| REVW-04 | Phase 4 | Pending |

---

## Coverage Check

- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓
