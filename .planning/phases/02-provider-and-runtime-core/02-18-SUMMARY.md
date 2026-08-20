---
phase: 02-provider-and-runtime-core
plan: 18
subsystem: verification-infrastructure
tags: [github-actions, ollama, pytest, ruff, pyright, evidence]

requires:
  - phase: 02-provider-and-runtime-core
    provides: Complete provider/runtime path and exact Python/Node dependency authorities
provides:
  - Bounded opt-in Ornith streaming and local-cancellation evidence lane
  - Schema-checked cold/warm runtime baseline with explicit non-success states
  - Seven pinned independent GitHub Actions truth lanes
  - Static rejection of floated actions, swallowed failures, reordered Pyright, and hidden blocked evidence
affects: [phase-02-verification, phase-03-memory-integrity, ci, release-evidence]

tech-stack:
  added: []
  patterns:
    - Required offline proof remains independent of optional live/provider evidence
    - Clean CI npm install is the only authoritative Pyright execution path
    - Classified legacy archives remain blocked evidence rather than active lint targets

key-files:
  created:
    - tests/live/test_ollama_ornith.py
    - tests/runtime/test_baseline_evidence.py
    - .planning/evidence/phase-02/runtime-baseline.json
    - tests/test_ci_contract.py
    - .github/workflows/ci.yml
  modified: []

key-decisions:
  - "Pyright remains not_run pending a genuinely completed green clean-CI typing-python job; local absence is not reinterpreted as proof."
  - "The optional Ornith lane was not run during the required offline gate and its provider baseline remains explicitly not_run."
  - "Ruff covers active backend code and deterministic tests while Phase 1-classified archive, scratch, and legacy-test roots remain in the separate blocked-evidence lane."
  - "The exact 16 approved and four rejected dependency dispositions remain unchanged; Plan 02-18 mutates no manifest or lock."

patterns-established:
  - "CI truth lane: each claim has its own job, lock-faithful setup, immutable action references, and native failing exit status."
  - "Optional live truth: environment absence may be classified before prerequisites, but every post-preflight non-success is non-green."

requirements-completed: [TEST-03, TEST-05, AI-01, AI-02, AI-03, OPS-01, OPS-02]

duration: 11min
completed: 2026-08-20
status: complete
verification-status: pending-clean-ci
---

# Phase 2 Plan 18: Optional Live Evidence and CI Truth Lanes Summary

**Aura now has deterministic offline closure, bounded optional Ornith evidence, and seven pinned CI truth lanes without claiming an unrun Pyright or live-model result.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-20T21:32:13Z
- **Completed:** 2026-08-20T21:42:51Z
- **Tasks:** 3/3
- **Files modified:** 5

## Accomplishments

- Added an opt-in, loopback-only `ornith:latest` probe with exact disabled/unavailable/model-missing classifications, a 90-second whole-operation bound, first-delta-before-completion proof, local cancellation cleanup, safe failure metadata, and an explicit `upstream_compute_cancellation: unknown` boundary.
- Recorded three cold imports (471.638, 438.241, and 431.288 ms) and three warm cached imports (0.004, 0.001, and 0.001 ms) without presenting them as an optimization result. The optional provider measurement remains `not_run`.
- Added seven independent CI jobs: deterministic backend, optional Ollama live, active-code lint, Python typing, frontend typing, frontend build, and environment-blocked classification.
- Pinned every external action to the four reviewed full commit SHAs and required `uv sync --locked`/`uv run --locked --no-sync` or clean `npm ci` setup as appropriate.
- Enforced `npm ci` before `npm run typecheck:python` in the same clean hosted job; the current local tree still has no Pyright executable, so no local Pyright pass is claimed.
- Preserved the exact dependency decision boundary: all four rejected SUS declarations remain untouched and no manifest, lock, installed environment, data root, or `.trunk/` content changed.

## Task Commits

1. **Task 02-18-01 RED: Runtime evidence contracts** — `0c5877b` (`test`)
2. **Task 02-18-01 GREEN: Honest runtime baseline evidence** — `11d0779` (`feat`)
3. **Task 02-18-02 RED: Independent CI truth contract** — `aeb2e56` (`test`)
4. **Task 02-18-03 GREEN: Pinned CI truth lanes** — `71cd043` (`feat`)

## Files Created/Modified

- `tests/live/test_ollama_ornith.py` — Offline-tested opt-in gate plus the marked bounded live streaming/cancellation probe.
- `tests/runtime/test_baseline_evidence.py` — Complete schema, privacy, sample, and anti-optimization-claim checks.
- `.planning/evidence/phase-02/runtime-baseline.json` — Content-free import measurements and explicit provider/comparison non-run states.
- `tests/test_ci_contract.py` — Structured YAML, lock, ordering, pin, false-success, and adversarial mutation checks.
- `.github/workflows/ci.yml` — Seven independent immutable-action CI lanes.

## Decisions Made

- A Plan 02-18 completion means the repository contract and locally available gates are complete; it does not mean Phase 2 has a green Python-typing result. That result remains pending until GitHub runs the clean `typing-python` job successfully.
- The live Ornith check stays optional and separate. It was not needed for the deterministic gate, was not executed in this plan, and cannot contribute a success claim while its evidence says `not_run`.
- Legacy archive/scratch scripts are not silently repaired or deleted. They remain covered by Phase 1's exact 38-entry classification and are uploaded by the manual `environment-blocked` lane, which exits non-green after publication.
- No audit fix was attempted. The current lock still reports exactly three high-severity npm findings: direct Vite and transitive Nano ID and PostCSS findings.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used module-mode pytest for a self-contained import path**

- **Found during:** Task 02-18-01 RED verification.
- **Issue:** The plan's direct `uv run ... pytest` task command uses the environment's console-script directory as `sys.path[0]`, so even existing tests could not import the repository-local `aura_backend` package.
- **Fix:** Used `uv run --locked --no-sync python -m pytest` in local verification and CI, matching the project's established deterministic command without changing packaging or manifests.
- **Files modified:** `.github/workflows/ci.yml`.
- **Verification:** The complete non-live suite passed with 456 tests, two expected dependency-gate skips, and one live deselection.
- **Committed in:** `71cd043`.

**2. [Rule 1 - Truth boundary] Kept classified legacy scripts out of the active Ruff lane**

- **Found during:** Task 02-18-03 complete offline gate.
- **Issue:** The broad planned Ruff command traversed immutable archive, scratch, and legacy-test roots already classified as untrusted/environment-blocked. It reported 56 pre-existing errors there, including intentionally preserved invalid historical scripts, while active code was clean.
- **Fix:** Kept the required `aura_backend tests` scope but explicitly excluded `aura_backend/archive_unused`, `aura_backend/scratch`, and `aura_backend/tests`; the separate environment-blocked job verifies and uploads their exact classification.
- **Files modified:** `.github/workflows/ci.yml`, `tests/test_ci_contract.py`.
- **Verification:** Active-code Ruff passed; the CI contract requires all three exclusions and the blocked-evidence upload/non-green status.
- **Committed in:** `71cd043`.

---

**Total deviations:** 2 auto-fixed (one Rule 3 execution-path blocker, one Rule 1 false-boundary correction).
**Impact on plan:** Both corrections make the advertised lanes match what actually runs. No product behavior, dependency authority, archived source, data, or environment was changed.

## Issues Encountered

- The installed GSD helper remains broken with `Cannot find module '../../../package.json'`; direct plan commands and atomic Git commits were used, and the orchestrator-owned `.planning/STATE.md` was preserved.
- No GitHub Actions run exists for these local commits because the branch is 155 commits ahead of `origin/main` and this plan was explicitly forbidden to push or mutate remote state.
- `node_modules/.bin/pyright` is absent. `npm run typecheck:python` was not executed and is not claimed.
- `npm audit --json --package-lock-only` currently reports three high-severity findings. They remain unresolved because an audit fix or dependency upgrade would exceed the exact approved package scope.

## Verification

- Baseline and CI schema/contract — **13 passed**.
- Complete deterministic offline suite — **456 passed, 2 skipped, 1 live deselected** in 25.88 seconds.
- Active backend/test Ruff lane — **passed**.
- Frontend TypeScript (`npm run typecheck:frontend`) — **passed**.
- Vite production build (`npm run build`) — **passed** with Vite 8.0.10.
- `uv lock --check` — **passed**, resolving the existing 180-package authority without mutation.
- `git diff --check` — **passed**.
- Python typing — **not_run/pending**; no local executable and no completed clean-CI job.
- Optional `ornith:latest` lane — **not_run**; deterministic proof does not depend on it.
- GitHub CI — **not_run/pending**; no push or remote mutation was performed.

## TDD Gate Compliance

- Runtime/baseline RED `0c5877b` failed on the absent baseline evidence; GREEN `11d0779` supplied the schema-valid, content-free artifact.
- CI RED `aeb2e56` failed because `.github/workflows/ci.yml` did not exist; GREEN `71cd043` implemented the reviewed pinned lanes and all eight contract tests passed.
- RED commits precede both corresponding GREEN commits.

## Known Stubs

None. Empty provider samples and the null optimization claim in the evidence artifact are intentional `not_run` truth states, not unwired product behavior.

## Threat Flags

None. Workflow supply-chain execution, self-hosted Ollama access, provider-log disclosure, denial-of-service bounds, and false-success labeling were all registered in the plan threat model and received the specified controls.

## User Setup Required

No local setup is required for the completed offline gates. A future authoritative Python-typing result requires the committed workflow to run in GitHub; the optional live lane additionally requires an explicitly labeled self-hosted runner with Ollama and `ornith:latest` already available.

## Next Phase Readiness

- Plan 02-18 repository work is complete and all locally available required gates pass.
- **Phase 2 is not yet fully verified:** Python typing and GitHub CI remain visibly `not_run`/pending until a clean green `typing-python` job exists.
- The optional live lane remains separate and non-authoritative; provider latency is not measured and no optimization claim is licensed.
- The four rejected SUS dependencies and three high npm audit findings remain explicit follow-up risks, not hidden successes.

## Self-Check: PASSED

- All five declared artifacts exist.
- All four task commits exist in Git history in RED/GREEN order.
- Frontmatter records `status: complete` for the plan and `verification-status: pending-clean-ci` for the phase truth boundary.
- Local deterministic, active lint, frontend typing/build, lock, privacy, pinning, and whitespace checks pass.
- Pyright, GitHub CI, and optional Ornith are all explicitly non-run and not counted as success.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
