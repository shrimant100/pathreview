## Solution plan

**Issue:** [Agent session state is not cleared between reviews for the same user](https://github.com/ascherj/pathreview/issues/43)

### Understand

**Root cause:** `Orchestrator.run()` in `agent/orchestrator.py` loads any existing Redis session for a `profile_id`, executes the current tool plan, then calls `session_state.update(results)` before writing back to Redis. That merge keeps keys from prior reviews even when those tools are no longer part of the plan.

**Expected behavior:** Each new review starts with a clean session scoped to that run. Stored session data should only reflect tools executed in the current review.

**Actual behavior:** When a user updates their portfolio and requests a second review, stale tool output (e.g. `readme_scorer` from review #1) remains in Redis under the same profile key and can influence downstream reads of session state.

### Map

| File | Role |
|------|------|
| `agent/orchestrator.py` | Loads, merges, and persists session state in `run()` |
| `agent/memory/session_store.py` | Redis-backed `get` / `set` / `delete` wrapper |
| `tests/unit/test_orchestrator_session.py` | Reproduction + regression test for issue #43 |

**Call path:** Review request → orchestrator `run(profile_id, profile_data)` → `session_store.get(profile_id)` → tool execution → `session_state.update(results)` → `session_store.set(profile_id, session_state)`.

No API or frontend changes expected unless review creation explicitly needs to pass a review-scoped session ID (investigate during implementation).

### Plan

1. **Lock in reproduction with a failing test** — Add `test_orchestrator_session.py` that runs two reviews for the same `profile_id` with different `profile_data`, then assert stale tool keys are absent from the stored session.
2. **Clear session at review start** — In `Orchestrator.run()`, delete or reset cached state for `profile_id` before executing tools (preferred: `session_store.delete(profile_id)` then persist only fresh `results`).
3. **Stop merging old state** — Replace `session_state.update(results)` with writing `results` directly so prior keys cannot leak back in even if delete is skipped.
4. **Add SessionStore unit coverage** — Optional small tests for `get` / `set` / `delete` in `tests/unit/test_session_store.py` if helpful for edge cases (expired key, missing key).
5. **Verify** — Run `pytest tests/unit/test_orchestrator_session.py` and `make test-unit`; manually smoke-test two consecutive reviews locally if time allows.

### Inputs & outputs

**Inputs:**
- `profile_id` (str) — identifies the user/profile whose session is cached
- `profile_data` (dict) — drives which tools run (`readme_content`, `resume_text`, `github_username`, etc.)

**Outputs / changes:**
- Redis session value at `session:{profile_id}` contains only tool results from the current review
- `Orchestrator.run()` return value `tool_results` matches the current plan with no ghost entries from prior runs
- Regression test passes

### Risks & unknowns

- **Concurrent reviews:** If the same user triggers two reviews simultaneously, deleting session at start could cause a race. Need to confirm whether the API allows parallel reviews per profile (`core/services/review_service.py`).
- **Intentional cross-review memoization:** Issue text implies caching is a bug, but verify no other code path depends on persisting tool output across reviews (grep for `session_store.get`).
- **In-process ContextManager cache:** `ContextManager` is per-orchestrator instance and memoizes within a single run only — should not block the fix, but worth noting in PR description.
- **Redis TTL:** Sessions expire after 3600s by default; bug still manifests within that window, which is the primary user scenario.

### Edge cases

- **First review for a profile** — No prior session exists; delete/get should be a no-op and results persist normally.
- **Second review with overlapping tools** — e.g. both runs include `market_analyzer`; new results should replace old ones, not merge with stale sibling keys from dropped tools.
- **Second review with empty plan** — Profile data yields zero tools; session should be empty (or deleted), not retain previous tool keys.
- **Missing session store** — When `session_store=None`, orchestrator behavior must remain unchanged (no delete calls).
- **Tool failure mid-run** — Partial `results` dict should still be what gets stored, without resurrecting keys from an earlier review.
