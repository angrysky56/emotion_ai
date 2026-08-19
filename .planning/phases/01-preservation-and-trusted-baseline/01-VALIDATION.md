---
phase: 1
slug: preservation-and-trusted-baseline
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-19
revised: 2026-08-19
---

# Phase 1 — Validation Strategy

> Deterministic feedback and the real preservation drill are separate evidence
> lanes. A skipped, blocked, partial, resource-limited, or environment-dependent
> check is never reported as a pass.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 with pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` |
| **Canonical deterministic command** | `uv run python -m pytest -q` |
| **Collection command** | `uv run python -m pytest --collect-only -q` |
| **Independent non-Python checks** | `npx tsc --noEmit`; `npm run build`; `git diff --check` |
| **Real-operation CLI** | `uv run python -m aura_backend.preservation.cli <subcommand>` using the normative Plan 01-02 contract |
| **Current baseline** | 13 deterministic tests pass; preservation/characterization files below are created in their owning waves |

## Sampling Rate

- **After every deterministic code task:** run its focused one-shot command below,
  then `uv run python -m pytest -q`.
- **After every plan wave:** run collection, the full deterministic Python suite,
  TypeScript type-check, Vite build, and `git diff --check` as separately named
  results.
- **During Plans 01-08 through 01-10:** run only the explicit real-operation command
  in the owning task, then its non-mutating validator. Never put inventory, preflight,
  backup, or restore execution in the default pytest command.
- **Before phase sign-off:** re-run deterministic checks and the non-mutating
  `validate-summary`, `validate-quiescence`, and `validate-restore-summary` commands
  against the already-created artifacts. Do not repeat the real backup merely to
  obtain another green test line.
- **Target deterministic feedback latency:** under 10 seconds for Python; the real
  inventory/copy/restore duration is recorded separately and has no passing timeout
  shortcut.

## Per-Task Verification Map — Deterministic Lane (15 tasks)

| Task ID | Exact Plan | Wave | Requirements | One-shot automated command | Primary file status |
|---|---|---:|---|---|---|
| 01-01-01 | 01-01 | 1 | PRES-01 | `uv run python -m pytest -q tests/preservation/test_inventory.py` | `tests/preservation/test_inventory.py` — planned W1 |
| 01-01-02 | 01-01 | 1 | PRES-01, PRES-04 | `uv run python -m pytest -q tests/preservation/test_inventory.py tests/preservation/test_manifest_privacy.py` | `tests/preservation/test_manifest_privacy.py` — planned W1 |
| 01-02-01 | 01-02 | 2 | PRES-02 | `uv run python -m pytest -q tests/preservation/test_backup_restore.py -k 'copy or path or mutation or quiescence'` | `aura_backend/preservation/backup.py` and focused tests — planned W2 |
| 01-02-02 | 01-02 | 2 | PRES-02 | `uv run python -m pytest -q tests/preservation/test_backup_restore.py` | `aura_backend/preservation/restore.py` and CLI contract tests — planned W2 |
| 01-03-01 | 01-03 | 1 | PRES-04, TEST-01 | `uv run python -m pytest -q tests/test_repository_hygiene.py` | `pyproject.toml`/`.gitignore` exist; hygiene test planned W1 |
| 01-03-02 | 01-03 | 1 | TEST-02 | `uv run python -m pytest -q tests/test_legacy_classification.py` | classification manifest and test — planned W1 |
| 01-04-01 | 01-04 | 2 | PRES-03, TEST-02 | `uv run python -m pytest -q tests/characterization/test_mcp_parameters.py` | focused characterization — planned W2 |
| 01-04-02 | 01-04 | 2 | PRES-03, TEST-02 | `uv run python -m pytest -q tests/characterization/test_mcp_result_formatting.py` | focused characterization — planned W2 |
| 01-04-03 | 01-04 | 2 | PRES-03, TEST-02 | `uv run python -m pytest -q tests/characterization/test_numpy_serialization.py` | focused characterization — planned W2 |
| 01-05-01 | 01-05 | 1 | PRES-03 | `uv run python -m pytest -q tests/api/test_local_boundary.py -k 'probe'` | subprocess probe and tests — planned W1 |
| 01-05-02 | 01-05 | 1 | PRES-03, LOCAL-01, LOCAL-02, LOCAL-04 | `uv run python -m pytest -q tests/api/test_local_boundary.py` | request boundary tests — planned W1 |
| 01-06-01 | 01-06 | 2 | PRES-03, LOCAL-03 | `uv run python -m pytest -q tests/api/test_filesystem_contract.py -k 'component or containment or symlink or format'` | helper and focused tests — planned W2 |
| 01-06-02 | 01-06 | 2 | PRES-03, LOCAL-03 | `uv run python -m pytest -q tests/api/test_filesystem_contract.py` | endpoint/filesystem contract — planned W2 |
| 01-07-01 | 01-07 | 2 | PRES-03 | `uv run python -m pytest -q tests/characterization/test_persistence_contract.py` | persistence characterization — planned W2 |
| 01-07-02 | 01-07 | 2 | PRES-03 | `uv run python -m pytest -q tests/characterization/test_companion_contract.py` | companion characterization — planned W2 |

## Per-Task Verification Map — Real Evidence and Drill Lane (6 tasks)

The action for each row contains the exact state-changing or real-data command. The
command below is the one-shot automated proof run after that action; validators do
not repeat the copy or open original Chroma roots.

| Task ID | Exact Plan | Wave | Requirements | One-shot automated command | Primary file / gate status |
|---|---|---:|---|---|---|
| 01-08-01 | 01-08 | 3 | PRES-01 | `uv run python -m aura_backend.preservation.cli validate-summary --summary .planning/evidence/phase-01/inventory-summary.json --require-role active --require-role backup --require-role test --require-role archive` | real inventory summary — created W3; private manifest outside Git |
| 01-08-02 | 01-08 | 3 | PRES-01, PRES-04 | `uv run python -m pytest -q tests/preservation/test_inventory.py tests/preservation/test_manifest_privacy.py tests/test_repository_hygiene.py` | reconciled inventory summary — updated W3 |
| 01-09-01 | 01-09 | 4 | PRES-02 | `uv run python -m aura_backend.preservation.cli validate-quiescence --summary .planning/evidence/phase-01/quiescence-summary.json --inventory .planning/evidence/phase-01/inventory-summary.json` | private/public preflight ticket — created W4; no copy |
| 01-09-02 | 01-09 | 4 | PRES-01, PRES-02 | `uv run python -m aura_backend.preservation.cli validate-quiescence --summary .planning/evidence/phase-01/quiescence-summary.json --inventory .planning/evidence/phase-01/inventory-summary.json --require-pass` | blocking manual quiescence checkpoint; Ty must reply `approved` |
| 01-10-01 | 01-10 | 5 | PRES-01, PRES-02 | `uv run python -m aura_backend.preservation.cli validate-restore-summary --summary .planning/evidence/phase-01/restore-drill-summary.json --inventory .planning/evidence/phase-01/inventory-summary.json --quiescence .planning/evidence/phase-01/quiescence-summary.json --require-pass --require-source-unchanged --require-fk-parity --require-retrieval-parity` | immutable backup/private evidence outside Git; public restore summary created W5 |
| 01-10-02 | 01-10 | 5 | PRES-04 | `uv run python -m pytest -q && npx tsc --noEmit && npm run build && git diff --check` | final summary cross-check and independent build gates — W5 |

## Manual Quiescence Checkpoint

This is the only human gate in Phase 1.

1. Plan 01-09 Task 1 runs the exact `preflight` command and produces a ticket bound
   to the inventory digest, source-set digest, destination, and 900-second expiry.
2. The automated `validate-quiescence ... --require-pass` command must succeed.
3. Ty confirms Aura is unused, Aura/FastAPI/Chroma writers are stopped, both likely
   active roots remain included, and `/backup` is the destination.
4. Ty replies `approved`. A stale or blocked ticket requires a fresh preflight and
   a new approval; the executor must not force-kill a process or omit a root.

Canonical root ownership and the meaning/repair of the eight-row FK anomaly are not
manual Phase 1 choices. Both roots are preserved, exact FK parity is required, and
those ownership/repair decisions are deferred to Phase 3. Retrieval evidence uses
the resolved opaque HMAC fixture and exposes no raw content or identifiers.

## Wave 0 Requirements

Existing infrastructure covers Python/Node installation and deterministic discovery.
Each planned behavior test is created test-first in its owning task. No speculative
test stub is required before Wave 1, and no new package installation is planned.

## Validation Sign-Off

- [x] All 21 submitted tasks have an exact plan ID, wave, requirement mapping,
  one-shot automated command, and file/gate status.
- [x] The sole manual quiescence checkpoint is mapped to Plan 01-09 Task 2.
- [x] Deterministic tests are separate from the real inventory/backup/restore lane.
- [x] Every real operation is followed by a non-mutating validator.
- [x] Commands contain no watch mode and no optional live Ollama/model dependency.
- [x] Missing, blocked, partial, resource-limited, or stale evidence cannot satisfy
  a passing gate.

**Approval:** pending successful execution of all deterministic checks, the ticketed
human checkpoint, and the real restore-drill validator.
