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
