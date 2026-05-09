# Requirements: Quick Capture

**Defined:** 2026-05-09
**Core Value:** Capture a thought in under 5 seconds, from hotkey to saved entry. Enrichment and review come after.

## v1 Requirements

### Capture

- [ ] **CAPT-01**: User can trigger a floating terminal via Hyprland hotkey
- [ ] **CAPT-02**: User can type multiline text in the floating terminal
- [ ] **CAPT-03**: User can save and close the terminal instantly (no confirmation needed)
- [ ] **CAPT-04**: Floating terminal auto-closes after save

### Storage

- [ ] **STOR-01**: Entry is saved to SQLite with original text, timestamp, and processing status
- [ ] **STOR-02**: New tables are created in existing nexus.db (separate tables, not extending existing schema)
- [ ] **STOR-03**: Each capture gets a wiki page in the Obsidian vault under `wiki/inbox/` with source: inbox
- [ ] **STOR-04**: Daily rollup pages are auto-generated aggregating captures for that day
- [ ] **STOR-05**: Weekly rollup pages are auto-generated aggregating daily rollups

### Enrichment

- [ ] **ENRI-01**: LLM enrichment runs via `opencode run` with the capture text as prompt
- [ ] **ENRI-02**: Enrichment preserves the original capture text alongside the enriched version
- [ ] **ENRI-03**: LLM classifies each entry into one of: Task, Idea, Reference, Question
- [ ] **ENRI-04**: Enrichment uses wiki-query skill to pull context from the Obsidian wiki
- [ ] **ENRI-05**: User can trigger enrichment immediately after capture (process-now flag)
- [ ] **ENRI-06**: Enrichment can batch-process N unprocessed entries automatically
- [ ] **ENRI-07**: User can trigger enrichment on-demand from Nexus UI or TUI

### Review & Dispatch

- [ ] **REVW-01**: Nexus web UI displays enriched entries from the database
- [ ] **REVW-02**: User can filter entries by bucket (Task, Idea, Reference, Question)
- [ ] **REVW-03**: Reference entries are sent to Karakeep with intent retrieval notes
- [ ] **REVW-04**: User can discuss an enriched entry with the LLM before dispatching to a project

## v2 Requirements

### TUI Review

- **TUI-01**: Nexus TUI for reviewing enriched entries from the terminal
- **TUI-02**: TUI supports same filtering and dispatching as web UI

### Advanced Capture

- **CAPT-A01**: Template pre-fills for common capture patterns
- **CAPT-A02**: Auto-detection of URLs for reference classification

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile capture | Desktop-only tool (Hyprland hotkey) |
| Voice input | Text input only — voice adds complexity without enough value |
| Real-time sync across devices | Local-first architecture; sync is a separate problem |
| Automatic task execution | Quick Capture enriches and dispatches, it doesn't execute (GSD does that) |
| Custom LLM provider configuration | Will use whatever OpenCode is already configured with |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAPT-01 | Phase 1 | Pending |
| CAPT-02 | Phase 1 | Pending |
| CAPT-03 | Phase 1 | Pending |
| CAPT-04 | Phase 1 | Pending |
| STOR-01 | Phase 1 | Pending |
| STOR-02 | Phase 1 | Pending |
| ENRI-01 | Phase 1 | Pending |
| ENRI-02 | Phase 1 | Pending |
| ENRI-03 | Phase 1 | Pending |
| ENRI-04 | Phase 1 | Pending |
| ENRI-05 | Phase 1 | Pending |
| REVW-01 | Phase 1 | Pending |
| STOR-03 | Phase 2 | Pending |
| STOR-04 | Phase 2 | Pending |
| STOR-05 | Phase 2 | Pending |
| REVW-03 | Phase 2 | Pending |
| ENRI-06 | Phase 3 | Pending |
| ENRI-07 | Phase 3 | Pending |
| REVW-02 | Phase 3 | Pending |
| REVW-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-09*
*Last updated: 2026-05-09 after initial definition*