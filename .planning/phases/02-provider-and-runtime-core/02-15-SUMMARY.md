---
phase: 02-provider-and-runtime-core
plan: 15
subsystem: testing
tags: [dependency-audit, supply-chain, human-approval, fail-closed]

requires:
  - phase: 02-provider-and-runtime-core
    provides: Plan 02-14 current legitimacy and dependency-consumer evidence
provides:
  - row-scoped human review of all 20 package-change candidates
  - conditional approval of the 16 OK rows and explicit rejection of four SUS rows
  - machine-checked block on all current 02-16 and 02-17 manifest changes
affects: [02-16-python-dependencies, 02-17-node-dependencies]

tech-stack:
  added: []
  patterns: [row-scoped human authorization, conditional approval without manifest authority]

key-files:
  created:
    - .planning/phases/02-provider-and-runtime-core/02-15-SUMMARY.md
  modified:
    - .planning/evidence/phase-02/package-legitimacy.json
    - tests/test_dependency_audit.py

key-decisions:
  - "Ty conditionally approved only the 16 candidates whose evidence verdict is OK and explicitly rejected all four SUS candidates."
  - "No manifest or lock change is authorized until Plans 02-16 and 02-17 are revised and independently recheck the exact subset and evidence freshness."
  - "The FAISS disposition mismatch in Plan 02-16 must be resolved during revision; it cannot be interpreted as approval to move either rejected FAISS package."

patterns-established:
  - "Human review is distinct from manifest authorization: reviewed rows remain non-executable until a revised downstream plan passes an independent gate."
  - "SUS and UNASSESSED rows cannot be widened into an approved set through review metadata mutations."

requirements-completed: [TEST-05, OPS-02]

duration: about 30min active across checkpoint and resumed approval
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 15: Package Legitimacy Approval Summary

**Ty approved the 16 evidence-OK rows only, rejected four suspicious rows, and kept every current downstream manifest and lock change blocked pending plan revision and independent recheck**

## Performance

- **Duration:** About 30 minutes active across the initial checkpoint and resumed approval
- **Started:** 2026-08-20T08:57:49Z
- **Completed:** 2026-08-20T17:16:08Z
- **Tasks:** 1 / 1
- **Files created:** 1
- **Files modified:** 2

## Accomplishments

- Recorded Ty's exact decision: `Approve only the 16 OK rows; reject the four SUS rows; revise Plans 02-16 and 02-17 before any manifest or lock changes.`
- Preserved all row-level `manifest_change_authorized: false` values, document-level `manifest_changes_authorized: false`, and an empty `authorized_candidate_ids` list.
- Strengthened the canonical validator to reject set widening, omission of a rejected candidate, direct manifest authorization, or removal of either downstream-plan block.
- Revalidated all package, freshness, consumer, entrypoint, and human-review invariants with 23 passing deterministic tests.

## Exact Human Disposition

### Conditionally Approved Evidence Rows

- `pypi:ruff@0.12.7`
- `npm:pyright@1.1.413`
- `pypi:google-genai@1.75.0`
- `pypi:mcp@1.27.0`
- `pypi:fastmcp@3.2.4`
- `pypi:memvid-sdk@2.0.159`
- `pypi:beautifulsoup4@4.13.4`
- `pypi:ebooklib@0.19`
- `pypi:opencv-python@4.11.0.86`
- `pypi:pandas@2.2.3`
- `pypi:pillow@12.2.0`
- `pypi:pypdf@6.10.2`
- `pypi:qrcode@8.2`
- `pypi:anthropic@0.54.0`
- `pypi:websockets@15.0.1`
- `npm:@google/genai@1.51.0`

These rows are conditionally approved review inputs only. They do not authorize the current Plans 02-16 or 02-17 to edit a manifest or lock.

### Rejected Evidence Rows

- `pypi:pyzbar@0.1.9` — unresolved maintenance/deprecation evidence
- `pypi:faiss-cpu@1.11.0` — recorded source redirects to an archived community wheel repository
- `pypi:faiss-gpu-cu12@1.14.1.post1` — unofficial third-party GPU wheels
- `pypi:asyncio-mqtt@0.16.2` — deprecated old distribution and renamed-source redirect

All four remain `SUS`, explicitly rejected, and unauthorized.

## Task Commits

1. **Task 02-15-01: Approve exact package and dependency-lane dispositions** — `1c12ffc` (`test`)

## Files Created/Modified

- `.planning/evidence/phase-02/package-legitimacy.json` — Records Ty's exact row-scoped decision and keeps both downstream plans blocked.
- `tests/test_dependency_audit.py` — Validates the exact 16/4 split and fails closed on attempted authorization widening.
- `.planning/phases/02-provider-and-runtime-core/02-15-SUMMARY.md` — Canonical checkpoint decision and downstream handoff.

## Decisions Made

- `OK` was accepted only as a conditionally approved evidence row, not as immediate manifest authority.
- `SUS` remains a hard rejection even for packages proposed only for removal and even when the static scan found zero supported consumers.
- Plans 02-16 and 02-17 must both be revised before execution because the original checkpoint contract made any SUS row blocking.
- Plan 02-16's instruction to place FAISS into optional/GPU lanes conflicts with the audited `remove-direct` disposition and cannot survive revision unchanged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Auditability] Persisted the human decision in the evidence schema**

- **Found during:** Task 02-15-01 continuation
- **Issue:** A summary-only decision would not give downstream validators a machine-readable, fail-closed authorization boundary.
- **Fix:** Added row-scoped conditional approval, rejection, downstream-block, and recheck conditions to the evidence document; strengthened its validator accordingly.
- **Files modified:** `.planning/evidence/phase-02/package-legitimacy.json`, `tests/test_dependency_audit.py`
- **Verification:** `uv run --locked --no-sync python -m pytest -q tests/test_dependency_audit.py` passed 23 tests, including four adversarial human-review mutations.
- **Committed in:** `1c12ffc`

---

**Total deviations:** 1 auto-fixed Rule 2 issue
**Impact on plan:** The approval remains narrower than the original downstream plans and cannot cause a package, manifest, lock, environment, or data mutation.

## Issues Encountered

- The older GSD package-legitimacy helper remains unusable because its installed runtime is missing its expected `package.json`. Plan 02-14's checked-in evidence validator is the canonical gate and passed fresh during this plan.
- Plan 02-16 contains a FAISS lane instruction that conflicts with the audited `remove-direct` disposition. The explicit downstream block prevents that inconsistency from reaching a manifest.

## Verification

- `uv run --locked --no-sync python -m pytest -q tests/test_dependency_audit.py` — **23 passed**
- `python -m json.tool .planning/evidence/phase-02/package-legitimacy.json` — **passed**
- `git diff --check` — **passed**
- Forbidden manifests and locks retained their pre-checkpoint SHA-256 hashes.
- No package manager mutation, installed-environment change, runtime-data access, or Git-history rewrite occurred.

## Known Stubs

None.

## User Setup Required

None. No software was installed, removed, or moved.

## Next Phase Readiness

- Plan 02-15 is complete because Ty supplied an explicit exact decision for every candidate.
- Plans 02-16 and 02-17 are **not ready to execute**. Both must be revised to consume only the 16 conditionally approved rows, exclude all four rejected rows, resolve the FAISS mismatch, and independently recheck freshness and scope.
- No current manifest or lock edit is authorized by this summary or the evidence document.

## Self-Check: PASSED

- Summary exists at the canonical plan path.
- Task commit `1c12ffc` exists in Git history.
- The evidence records exactly 16 conditionally approved and four rejected rows, with both downstream plans blocked and no manifest authorization.
- All 23 deterministic evidence-contract tests pass.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
