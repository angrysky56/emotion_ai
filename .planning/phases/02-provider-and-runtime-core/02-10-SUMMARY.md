---
phase: 02-provider-and-runtime-core
plan: 10
subsystem: runtime-health
tags: [fastapi, health, readiness, providers, redaction, tdd]

requires:
  - phase: 02-07
    provides: Lifespan-owned application and provider runtime snapshots
  - phase: 02-08
    provides: Import-safe FastAPI application factory
  - phase: 02-09
    provides: Provider-neutral conversation route integration
provides:
  - Frozen fail-closed application, resource, and provider health snapshots
  - Cached `/live`, `/ready`, `/health/providers`, and compatibility `/health` routes
  - Adversarial redaction and no-side-effect polling evidence
affects: [02-11-preflight, 02-12-startup, 02-13-startup-docs, 02-18-ci]

tech-stack:
  added: []
  patterns:
    - Bounded provider metadata observation once during lifespan startup
    - Public health serialization from validated allowlists only
    - Server-generated content-free health correlation identifiers

key-files:
  created:
    - aura_backend/runtime/health.py
    - tests/runtime/test_health.py
  modified:
    - aura_backend/main.py

key-decisions:
  - "Readiness is recomputed from required runtime resources and exact selected provider/model evidence; cached booleans alone cannot pass."
  - "Health requests never probe providers or storage; the selected provider metadata check runs once under the configured preflight timeout during lifespan startup."
  - "Health correlation IDs are generated server-side so arbitrary request headers cannot be reflected into public diagnostics."

patterns-established:
  - "Cached health: lifespan records one frozen observation and every route serializes that same evidence without work."
  - "Fail-closed states: blocked, unknown, partial, unavailable, model-not-found, and not-run remain distinct from ready."

requirements-completed: [TEST-03, OPS-01]

duration: 15min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 10: Truthful Layered Health Summary

**Frozen, privacy-safe health snapshots now distinguish process liveness, application readiness, and selected/optional provider availability without turning polling into runtime work.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-20T19:53:10Z
- **Completed:** 2026-08-20T20:08:18Z
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

- Derived readiness fail-closed from all required resources plus exact selected provider/model metadata; vacuous and contradictory snapshots cannot pass.
- Kept unselected Gemini and OpenRouter states visible as `not_configured` without making a healthy local Ollama runtime fail.
- Added `/live` (always process-local 200), `/ready` (200/503), `/health/providers` (diagnostic 200), and a compatibility `/health` composite backed by one cached snapshot.
- Proved repeated health polling performs no provider generation, model download, runtime construction, database open, or source write.
- Prevented raw exceptions, credentials, URLs, prompts, responses, tool content, tracebacks, and arbitrary request identifiers from entering health JSON or default logs.

## Task Commits

Each TDD gate and correction was committed atomically:

1. **Task 1 RED: typed health truth and redaction contract** — `1897cf5`
2. **Task 1 GREEN: cached health snapshots and safe serializer** — `75abb61`
3. **Task 2 RED: layered route and no-side-effect contract** — `1369270`
4. **Task 2 GREEN: lifespan cache and four health routes** — `f0ade84`
5. **Security RED: live correlation redaction coverage** — `c084f6f`
6. **Security GREEN: server-generated correlation IDs** — `31a1c04`

## Files Created/Modified

- `aura_backend/runtime/health.py` — Frozen health DTOs, state mapping, fail-closed aggregation, and allowlisted serialization.
- `aura_backend/main.py` — One bounded lifespan health capture and four side-effect-free public routes.
- `tests/runtime/test_health.py` — Truth tables, adversarial inconsistencies, HTTP status contracts, polling tripwires, import purity, and recursive redaction checks.

## Decisions Made

- Provider/model availability is observed once during startup through the existing metadata-only health boundary; ordinary health requests only read the cached result.
- An absent selected-provider check is `not_run`, a failed check is `unavailable`, and a mismatched provider/model identity is `blocked`; none can be reported ready.
- Compatibility `/health` remains HTTP 200 for existing local consumers while its payload truthfully reports `operational` or `unhealthy`; `/ready` owns the conventional 200/503 signal.
- No authentication, dependency, manifest, lock, persistence, session, or storage behavior changed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Information disclosure] Prevented request-ID reflection on `/live`**
- **Found during:** Final Task 2 threat review
- **Issue:** The initial liveness route returned an arbitrary caller-supplied `X-Request-ID`, which could reflect credential-like content even though the other health serializers sanitized it.
- **Fix:** Health routes now generate content-free server correlation IDs and never echo the request header.
- **Files modified:** `aura_backend/main.py`, `tests/runtime/test_health.py`
- **Verification:** The adversarial sentinel test failed before the fix and passes afterward; the full offline suite remains green.
- **Committed in:** `c084f6f`, `31a1c04`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug/security correction).
**Impact on plan:** Strengthened the specified disclosure boundary without changing route purpose or local/no-auth behavior.

## Issues Encountered

- The local GSD helper remains unavailable because its installed runtime cannot resolve `../../../package.json`. Execution used the plan's direct commands and atomic Git commits; shared `STATE.md` was intentionally left to the orchestrator.

## Verification

- `uv run --locked --no-sync python -m pytest -q tests/runtime/test_health.py` — 14 passed.
- Focused health/lifecycle/import/local/companion/persistence regression — 75 passed.
- `uv run --locked --no-sync python -m pytest -q tests -m 'not live'` — 358 passed.
- `npx tsc --noEmit` — passed.
- `npm run build` — passed with Vite 8.0.10.
- `git diff --check` — passed.
- No live model or external service was used.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02-11 can consume the typed cached readiness/provider payloads for non-mutating preflight checks.
- No blockers remain for the next wave.

## Self-Check: PASSED

- All three declared implementation/test files exist.
- All six listed commits exist in Git history.
- Task-specific, focused regression, complete offline Python, TypeScript type-check, and production build gates passed.
- Shared `STATE.md`, dependency manifests/locks, data/storage roots, and `.trunk/` were not modified by this plan.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
