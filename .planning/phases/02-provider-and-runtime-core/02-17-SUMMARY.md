---
phase: 02-provider-and-runtime-core
plan: 17
subsystem: dependencies
tags: [npm, pyright, typescript, supply-chain, testing]

requires:
  - phase: 02-provider-and-runtime-core
    provides: exact 16 OK / 4 SUS human package disposition and revised-plan gate
provides:
  - exact locked Pyright 1.1.413 development dependency
  - removal of the unused frontend Google SDK declaration and lock closure
  - named local Python typing, frontend typing, and frontend build scripts
  - fail-closed Node dependency authority contract
affects: [02-18-ci-truth-lanes, frontend-verification, dependency-authority]

tech-stack:
  added: [pyright@1.1.413]
  patterns: [digest-bound pre-edit authorization, package-lock-only reconciliation]

key-files:
  created:
    - tests/test_node_dependency_contract.py
    - .planning/phases/02-provider-and-runtime-core/02-17-SUMMARY.md
  modified:
    - package.json
    - package-lock.json

key-decisions:
  - "Node dependency authority was limited to exact pyright@1.1.413 addition and direct @google/genai removal."
  - "Pyright execution remains unclaimed until Plan 02-18 performs an isolated clean lock-faithful install."
  - "All four rejected SUS Python declarations and records remain unchanged."

patterns-established:
  - "Dependency edits require a passing digest-bound evidence gate before either manifest is changed."
  - "npm lock reconciliation uses package-lock-only plus ignore-scripts and receives a semantic diff review."

requirements-completed: [TEST-03, TEST-05, OPS-01, OPS-02]

duration: 11 min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 17: Node Dependency and Typing Authority Summary

**Aura now has an exact, evidence-gated Node dependency authority with locked Pyright, local typing/build commands, and no unused frontend Google SDK.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-20T21:14:06Z
- **Completed:** 2026-08-20T21:24:46Z
- **Tasks:** 2 / 2
- **Files modified:** 4

## Accomplishments

- Passed the independent pre-edit gate against the evidence SHA, both live manifest SHAs, exact human decision text, exact 16 OK / 4 SUS partition, and exact two-action Node subset.
- Added exact `pyright@1.1.413` as a development dependency and removed only the unused direct frontend `@google/genai` dependency.
- Added `typecheck:python`, `typecheck:frontend`, and retained `build` as explicit local npm-script lanes.
- Reconciled only `package-lock.json` with lifecycle scripts suppressed; every surviving package version remained unchanged.
- Preserved all Python manifests, locks, rejected rows, evidence, runtime data, and the active installed Node environment.

## Task Commits

Each task was committed atomically:

1. **Task 02-17-01: Specify the Node authority and verification-script contract** — `e1d8edc` (`test`)
2. **Task 02-17-02: Apply approved Node changes and reconcile the lock** — `57ca161` (`chore`)

## Files Created/Modified

- `tests/test_node_dependency_contract.py` — Fail-closed evidence, action-set, exact-version, script, import, and lock authority checks.
- `package.json` — Exact Pyright development declaration, unused SDK removal, and named typing commands.
- `package-lock.json` — Lock-faithful consequences of the two approved dependency actions.
- `.planning/phases/02-provider-and-runtime-core/02-17-SUMMARY.md` — Execution and verification record.

## Decisions Made

- npm scripts rely on npm's project-local `node_modules/.bin` PATH, so they remain cross-platform and do not invoke `npx`, a global executable, or an installer.
- The lock-only operation removed the Google SDK's unreachable dependency closure, added the one Pyright package record, and changed only mechanical development flags on surviving shared packages.
- Actual Pyright execution is deliberately deferred: `node_modules/.bin/pyright` is absent because this plan was forbidden from mutating Ty's active installed environment.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `npm install --package-lock-only --ignore-scripts` reported three high-severity audit findings in the resulting dependency graph. No audit fix or version upgrade was attempted because this plan explicitly forbids broad dependency changes; this remains visible for later security/dependency work.
- The installed GSD helper still fails with `Cannot find module '../../../package.json'`, so no helper-driven state mutation was attempted. The orchestrator retains ownership of `.planning/STATE.md`.

## Verification

- Pre-edit authorization: `AURA_DEPENDENCY_PRECHANGE_GATE=1 ...::test_prechange_node_authority_gate` — **1 passed before manifest edits**.
- TDD RED: Node contract — **3 expected failures**, limited to the missing approved Pyright/scripts and still-present Google SDK.
- Post-change Node contract — **10 passed, 1 expected pre-edit-gate skip**.
- Full offline deterministic suite — **440 passed, 2 skipped**.
- `npm run typecheck:frontend` — **passed** using the existing installed TypeScript tree.
- `npm run build` — **passed** with Vite 8.0.10.
- `npm ls --package-lock-only --depth=0 --ignore-scripts` — **passed**, showing exact Pyright 1.1.413.
- Semantic lock review — **no surviving package version changed**; only the approved addition/removal closure and mechanical development flags changed.
- `git diff --check` — **passed**.
- `npm run typecheck:python` — **not run and not claimed**; Plan 02-18 owns the isolated clean-install proof.

## Known Stubs

None.

## Threat Flags

None. The package identity, lock tampering, lifecycle-script, and verification-claim surfaces were all already registered in the plan threat model and received their specified mitigations.

## User Setup Required

None. The active `node_modules` environment was not installed, removed, or synchronized.

## Next Phase Readiness

- Plan 02-18 can now perform the first authoritative Pyright execution after an isolated `npm ci` from this exact lock.
- The four rejected SUS packages remain unchanged and outside this plan.
- The npm audit findings should be assessed separately without widening this approved dependency change.

## Self-Check: PASSED

- Both task commits exist in Git history.
- All declared files exist and the package/lock direct dependencies agree exactly.
- Evidence, Python manifests/locks, rejected declarations, and installed Pyright absence were rechecked after execution.
- All required offline tests, frontend typing, and frontend build gates pass.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
