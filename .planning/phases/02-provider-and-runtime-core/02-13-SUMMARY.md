---
phase: 02-provider-and-runtime-core
plan: 13
subsystem: startup-documentation
tags: [uv, ollama, runtime-cli, loopback, documentation-tests]

requires:
  - phase: 02-12
    provides: Canonical preflight-gated runtime CLI and thin cross-platform delegates
provides:
  - Exact locked setup, preflight, and serve instructions
  - Local-first non-secret Ollama example configuration
  - Static drift gates for commands, trust boundaries, and configuration parsing
affects: [02-18-ci, operations, release-documentation]

tech-stack:
  added: []
  patterns:
    - Marker-extracted documentation commands compared with the executable runtime contract
    - Example environment parsed through production RuntimeSettings without dotenv or ambient state

key-files:
  created:
    - tests/runtime/test_startup_docs.py
  modified:
    - README.md
    - aura_backend/STARTUP_GUIDE.md
    - .env.example

key-decisions:
  - "Supported startup uses explicit uv sync --locked and npm ci setup, followed by locked/no-sync preflight and serve commands."
  - "The checked-in configuration selects Ollama on loopback; Gemini, OpenRouter, and autonomic cloud behavior remain explicit opt-ins."
  - "Documentation states no sign-in and no remote compute or billing cancellation guarantee."

patterns-established:
  - "Truth-bound docs: drift tests extract marked commands and reject legacy mutating startup behavior."
  - "Local-first examples: production settings parsing proves the checked-in example needs no cloud credential."

requirements-completed: [TEST-03, OPS-01]

duration: 12min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 13: Truthful Local Startup Documentation Summary

**Aura now has one tested, locked/no-sync startup path and a non-secret Ollama-on-loopback example that states provider, readiness, LAN, and cancellation limits honestly.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-20T21:00:33Z
- **Completed:** 2026-08-20T21:12:11Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- Replaced unsafe install-on-start, process-killing, implicit Gemini, and nonexistent-launcher guidance with exact executable setup, preflight, serve, and delegate commands.
- Documented all six preflight states and exit codes, selected-model/live-provider behavior, loopback/no-sign-in trust boundary, explicit LAN warning, and local-only cancellation guarantee.
- Rebuilt `.env.example` around Ollama and `127.0.0.1`, with optional cloud providers and autonomic behavior commented and credential-free.
- Added 9 static/configuration tests that reject command drift, duplicate keys, active cloud credentials, secret-like values, and contradictory legacy runtime claims.

## Task Commits

1. **Task 02-13-01: Document canonical preflight, serve, and truth boundaries** — `81eb6fb`
2. **Task 02-13-02: Make the example runtime configuration local-first and non-secret** — `d14bfcd`
3. **Rule 1 correction: Remove contradictory legacy runtime guidance** — `7fbc52a`

## Files Created/Modified

- `tests/runtime/test_startup_docs.py` — Extracted-command, safety-language, provider/configuration, duplicate-key, and secret-sentinel drift gates.
- `README.md` — Canonical local startup path plus corrected provider, troubleshooting, cloud-transmission, and no-auth statements.
- `aura_backend/STARTUP_GUIDE.md` — Concise operator guide for explicit setup, report-only preflight, owned serve lifecycle, delegates, and safe remediation.
- `.env.example` — One local-first runtime example with explicit optional cloud sections and no live secret.

## Decisions Made

- Setup is the only environment-mutating step and remains explicit; normal preflight/serve and wrappers always use `uv run --locked --no-sync`.
- Preflight provider rows are labeled live evidence, while the deterministic suite remains offline.
- `ornith:latest` is not the normal example model; it remains reserved for the separate bounded opt-in live lane.
- Optional cloud credentials are documented only as commented non-secret sentinels.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Documentation correctness] Removed contradictory legacy provider, auth, and destructive troubleshooting claims**
- **Found during:** Plan-level truth-boundary scan after Task 2
- **Issue:** README sections outside the new startup marker still said Gemini was unconditional, claimed API-key authentication, and advised killing ports or deleting the vector database.
- **Fix:** Changed the data flow to the explicitly selected provider, stated the actual no-auth/cloud boundary, and replaced destructive troubleshooting with safe remediation guidance.
- **Files modified:** `README.md`, `tests/runtime/test_startup_docs.py`
- **Verification:** The drift test now scans the whole README for these contradictions; 30 focused startup tests and the complete offline suite pass.
- **Committed in:** `7fbc52a`

---

**Total deviations:** 1 auto-fixed (Rule 1 documentation correctness).
**Impact on plan:** The correction closed contradictions that would otherwise undermine the documented local/private startup contract; no runtime, dependency, storage, or deployment scope was added.

## Issues Encountered

- Two initial drift assertions were overly literal about wording and line wrapping. They were corrected before the first task commit; the resulting assertions test semantic boundaries without banning truthful warnings.

## Verification

- `uv run --locked --no-sync python -m pytest -q tests/runtime/test_startup_docs.py tests/runtime/test_startup_entrypoints.py` — 30 passed.
- `uv run --locked --no-sync python -m pytest -q tests -m 'not live'` — 430 passed, 1 skipped.
- `uv run --locked --no-sync ruff check tests/runtime/test_startup_docs.py` — passed.
- `npx tsc --noEmit` — passed.
- `npm run build` — passed with Vite 8.0.10.
- `git diff --check` — passed.
- No service, provider, model, installer, sync, manifest/lock, data/storage, `.trunk/`, or shared-state operation was performed.

## Known Stubs

None. Commented credential sentinels in `.env.example` are intentional operator placeholders and are inactive by contract.

## Threat Controls

- **T-02-ST / T-02-SC:** Exact command extraction and mutation bans prevent unsafe startup/setup drift.
- **T-02-PC:** Production settings parsing proves the active example selects Ollama without a cloud key.
- **T-02-PL:** Secret-pattern and sentinel checks keep credentials inactive and obviously non-secret.

## User Setup Required

None for this plan. Running Aura still requires the explicit locked dependency setup and an already-installed selected Ollama model described in the guide.

## Next Phase Readiness

- Plan 02-18 can consume the exact offline startup/documentation gate in CI.
- No blocker remains from Plan 02-13.

## Self-Check: PASSED

- The summary and all four declared production/test files exist.
- All three Plan 02-13 task/correction commits exist in Git history.
- Focused startup, complete offline Python, Ruff, TypeScript, frontend build, and whitespace gates pass.
- Shared `STATE.md`, manifests/locks, data/storage roots, and `.trunk/` were preserved.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
