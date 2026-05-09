---
phase: 1
slug: capture-and-enrich-mvp
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml [tool.pytest] |
| **Quick run command** | `uv run pytest -x` |
| **Full suite command** | `uv run pytest --cov=quick_capture --cov-fail-under=80` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x`
- **After every plan wave:** Run `uv run pytest --cov=quick_capture --cov-fail-under=80`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (to be filled per-plan during execution) | | | | | | | | | |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_capture.py` — stubs for CAPT-01 through CAPT-04
- [ ] `tests/test_storage.py` — stubs for STOR-01, STOR-02
- [ ] `tests/test_enrichment.py` — stubs for ENRI-01 through ENRI-05
- [ ] `tests/test_nexus_view.py` — stubs for REVW-01
- [ ] `tests/conftest.py` — shared fixtures (temp DB, mock capture data)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hotkey triggers floating terminal | CAPT-01 | Requires running Hyprland compositor | Press hotkey, verify Ghostty window appears |
| Floating terminal auto-closes after save | CAPT-04 | Requires terminal process lifecycle | Submit capture, verify window closes |
| LLM enrichment produces classified output | ENRI-03 | Requires live opencode run with wiki context | Run enrichment on a test capture, verify bucket classification |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending