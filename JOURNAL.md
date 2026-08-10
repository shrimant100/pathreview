## Week 7 - Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/43

**Issue title:** Agent session state is not cleared between reviews for the same user

**Tier:** [x] Tier 1 [ ] Tier 2 [ ] Tier 3

**Problem summary:**

The agent system stores session data in Redis keyed by user/profile ID via `session_store.py`. When a user runs a portfolio review, tool results and orchestrator state are cached for that ID. If the same user updates their portfolio and requests a new review, the orchestrator loads the old cached session instead of starting fresh. That means stale tool outputs from the previous review can influence the second one, so feedback may not reflect the user's latest changes. A successful fix would ensure session state is cleared or scoped per review so each new review re-runs the agent tools against current data.

**Branch name:** fix/43-clear-agent-session-state

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger

---

## Is this issue right for me?

### Part 1 — Understanding the issue

- [x] **Can I explain what this issue is asking for in my own words?**  
  The agent caches review session data in Redis by profile ID. When the same user starts a second review, that old cache is reused instead of resetting. I need to clear or isolate session state so each review runs against fresh portfolio data.

- [x] **Do I understand which part of the app is affected?**  
  This is in the **agent** subsystem. The main files are `agent/memory/session_store.py` (Redis get/set/delete) and `agent/orchestrator.py` (loads session at the start of `run()` and persists merged results at the end).

- [x] **Do I understand what "done" looks like?**  
  **Before:** A user runs review #1, updates their resume or repos, runs review #2 — the second review can reflect stale tool output from review #1. **After:** Each new review starts with a clean session (or a session scoped to that review), tools re-run on current data, and feedback matches the updated portfolio.

### Part 2 — Tier fit

- [x] **Tier 1 is appropriate.** The fix is localized to the agent memory layer — likely `session_store.py` and/or a small change in `orchestrator.py` to delete or skip stale cache at review start. No full RAG pipeline or frontend changes required. Estimated effort: 3–4 hours (within Tier 1 range).

### Part 3 — Codebase readiness

- [x] **Can I find the relevant code?**  
  I read `SessionStore.get/set/delete` in `session_store.py` and the session load/persist block in `Orchestrator.run()` (lines 46–67). The bug path is: `get(profile_id)` → execute tools → `session_state.update(results)` → `set(profile_id, session_state)`.

- [x] **Do I understand the surrounding code well enough to change it safely?**  
  `Orchestrator.run()` builds a tool plan from profile data, executes each tool, and optionally persists results. A fix would likely call `session_store.delete(profile_id)` before a new review, or stop merging old state into the new session. I need to confirm where reviews are triggered in the API layer when implementing.

- [x] **Have I read the relevant test file?**  
  There is no existing `test_session_store.py` or orchestrator session test yet. I will need to add a new unit test (e.g. `tests/unit/test_session_store.py` or `test_orchestrator.py`) that verifies session state is cleared between two review runs for the same profile ID.

### Part 4 — Scope and time

- [x] **Checked cohort ledger claims** — issue claimed; comfortable with competition level for a Tier 1 task.

- [x] **Scope is realistic for Weeks 8–9.** Tier 1 estimate is 3–6 hours. This fits: small code change, one new test, PR by Week 9.

- [x] **No blockers or dependencies.** Issue #43 is not blocked by another open issue.

### Verdict

All checklist items pass. Ready to implement in Weeks 8–9.

---

## Week 8 - Reproduction & solution planning

**Reproduction commit link:** https://github.com/shrimant100/pathreview/commit/33edc43

**Reproduction summary:**

I reproduced the bug with a unit test in `tests/unit/test_orchestrator_session.py`. The test runs two reviews for the same `profile_id`: first with `readme_content` (triggers `readme_scorer`), then with `resume_text` only (triggers `skill_extractor`). After the second run, the Redis-backed session still contains the `readme_scorer` key from review #1 because `Orchestrator.run()` merges old session state via `session_state.update(results)` instead of starting fresh.

**PLAN.md link:** [PLAN.md](https://github.com/shrimant100/pathreview/blob/fix/43-clear-agent-session-state/PLAN.md)

**Walkthrough video (recommended):** Not recorded (optional)

**Blockers or open questions:**

None at time of submission.

---

## Week 9 - Solution building & PR submission

### Check-in 1 (mid-week)

**Current progress:**

Implemented PLAN.md steps 2–3 in `agent/orchestrator.py`: each review now calls `session_store.delete(profile_id)` before running tools and persists only the current `results` dict (no merge with prior session state). Updated `tests/unit/test_orchestrator_session.py` with two additional edge-case tests (first review, empty plan). All 3 orchestrator session tests pass. Ran `make test-unit` and `make check` and recorded the pre-existing baseline (see appendix below).

**Next steps:**

Submit PR and complete Check-in 2.

**Blockers:**

None.

---

### Check-in 2 (end of week)

**PR link:** https://github.com/shrimant100/pathreview/pull/1

**Branch:** fix/43-clear-agent-session-state

**What you built:**

Fixed issue #43 by clearing Redis session state at the start of each orchestrator review and persisting only the current run's tool results. Previously, `Orchestrator.run()` loaded prior session data and merged it with new results, leaving stale tool keys from earlier reviews. Now each review starts fresh so updated portfolio data drives tool execution.

**Tests added or updated:**

`tests/unit/test_orchestrator_session.py` — reproduction test for stale session keys between reviews, plus edge cases for first review and empty tool plan (3 tests total, all passing).

**Self-review confirmation:** [x] make check passes (no new lint/type errors from my changes; 82 pre-existing ruff errors in upstream)   [x] make test-unit passes (no new test failures; all 3 orchestrator session tests pass; 53 pre-existing failures in upstream)

**Draft PR feedback received from:** none

---

### Appendix: Pre-existing baseline (`make test-unit` / `make check`)

Per course guidance, **"passes" means this PR introduces no new failures** — not that the entire upstream suite is green.

**`make test-unit`:** 53 failed, 378 passed (431 collected) before and after my changes. All 3 tests in `tests/unit/test_orchestrator_session.py` pass. Pre-existing failures are in unrelated modules (`test_bias_detector`, `test_faithfulness_checker`, `test_review_service`, etc.).

**`make check`:** fails at lint with 82 pre-existing ruff errors in api/, ingestion/, rag/, safety/, and tests/. My edited files do not add new lint or type errors.

---

## Week 10 – Iteration & reflection

### Reviewer feedback

**Feedback received:** [ ] Yes  [x] No – still awaiting review

**Summary of feedback:**

No comments or reviews on [PR #1](https://github.com/shrimant100/pathreview/pull/1) as of submission. Per course notes, formal reviewer feedback is not expected for Summer 2026 — documented here and moving on.

**How you responded:**

N/A — no feedback received.

---

### Reflection

**What was harder than you expected?**

Environment setup on Windows took longer than the fix itself: ChromaDB crashed on NumPy 2.x, `make setup` failed in PowerShell, and the first pre-commit run hung while installing hook environments. I also underestimated how many upstream unit tests and lint errors already existed — it took a while to understand that "passes" meant no *new* failures, not a fully green suite.

**What did you learn about working in a large codebase?**

You have to read before you edit. The bug looked like a one-line merge problem, but tracing it meant following `Orchestrator.run()` → `SessionStore` → the test plan in `_build_plan()`. In someone else's repo you also inherit their tooling (pre-commit, ruff, mypy, conventional commits) and need to match those conventions instead of treating it like a solo project.

**How did AI tools help – and where did they fall short?**

AI was most useful for Docker troubleshooting, drafting `PLAN.md` and the failing repro test, and navigating git remotes/fork setup. It fell short when it almost committed dozens of unrelated formatter changes from my working tree — I had to stage only the files for issue #43. It also couldn't replace actually running `make test-unit` and reading the pre-existing failure baseline myself.

**What would you do differently if you started over?**

Use Git Bash from day one on Windows, run `make test-unit` and `make check` once before touching code to establish a baseline, and commit in smaller chunks (repro test → fix → journal) without letting formatter runs dirty unrelated files.

**What are you most proud of from this module?**

Writing a failing test that reproduced the exact stale-session behavior before implementing the fix — when it turned green after two small changes in `orchestrator.py`, I was confident the PR solved the real bug and not just a symptom.
