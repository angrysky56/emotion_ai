---
phase: 03-memory-integrity-and-data-lifecycle
status: planned
nyquist_compliant: true
wave_0_complete: false
last_updated: 2026-08-31
---

# Phase 03 Validation Strategy

Every plan task has a named automated pytest command and an explicit artifact or human gate. Code-producing tasks use a RED tracer first, the smallest complete GREEN implementation, and refactoring only while green. Real historical stores are outside ordinary task execution: Plans 03-07, 03-08, and 03-09 are non-autonomous gates for fresh inventory, backup/restore, disposable-copy import, and the read switch.

The recorded pre-Phase-3 suite counts differ between current artifacts (`STATE.md` records 510 passed while `03-RESEARCH.md` records 512 passed). Execution must recapture the full non-live baseline; pass/fail and named contract coverage are gates, not a hard-coded pass count.

## Test command contract

All test commands use the locked existing environment:

`uv run --locked --no-sync python -m pytest ...`

No task may install or sync packages, change `pyproject.toml` or `uv.lock`, create another environment, or accept a resource-limited/truncated/vacuous result as passing.

## Existing and planned test surfaces

| Test surface | Role | Available after |
|---|---|---|
| Existing `tests/api`, `tests/runtime`, `tests/characterization`, `tests/memory` suites | Preserve seven-field/API/provider/loopback/prompt/Memvid/Phase-2 contracts | Before Wave 1 |
| `tests/storage/test_atomic_ledger.py` | Transactional turn/schema invariants | 03-01-01 |
| `tests/storage/test_idempotency.py` | Retry/restart/replay convergence | 03-01-02 |
| `tests/storage/test_provenance_supersession.py` | Append-only provenance/correction graph | 03-01-03 |
| `tests/storage/test_memory_benchmark.py` | Sanitized corpus, controls, gates, determinism | 03-02-01 |
| `tests/storage/test_projection_rebuild.py` | SQLite-to-cosine-Chroma rebuild/parity | 03-03-01 |
| `tests/storage/test_storage_owner.py` | Sole-truth and owner-marker invariants | 03-03-01 |
| `tests/storage/test_legacy_migration.py` | Disposable-copy immutable/idempotent import | 03-03-02 |
| `tests/storage/test_hybrid_retrieval.py` | Hard gates, RRF, traces, cursors, salience zero | 03-04-01 |
| `tests/storage/test_snapshot_restore.py` | Online backup and exact isolated restore | 03-05-01 |
| `tests/storage/test_export_delete.py` | Truthful JSON export and explicit deletion protocol | 03-05-02 |
| `tests/storage/test_git_hygiene.py` | Generated/private artifact exclusion | 03-05-03 |
| `tests/storage/test_phase3_evidence.py` | Adversarial real-operation evidence validator | 03-07-01 |

## Requirement coverage

| Requirement | Observable proof | Task coverage |
|---|---|---|
| PRES-04 | Public/private evidence split, ignore rules, Phase 1 evidence hashes unchanged | 03-05-03, 03-07-01, 03-07-03, 03-08-01, 03-08-03, 03-09-01, 03-09-02, 03-09-03 |
| TEST-03 | Atomicity, corruption, idempotency, authorization, human-bound publication, current-CI, privacy, forged-evidence, rollback failures | All 23 tasks; exact map below |
| DATA-01 | One owner controls persistence, indexing, recovery, export, retention, and deletion | 03-01-01, 03-01-02, 03-03-01, 03-03-02, 03-05-01, 03-05-02, 03-05-03, 03-06-01, 03-06-02, 03-09-01 |
| DATA-02 | Consistent snapshot and exact isolated restore | 03-05-01, 03-08-01, 03-09-01 |
| DATA-03 | Export returns actual data in advertised formats and rejects unsupported formats | 03-05-02, 03-06-02, 03-09-03 |
| DATA-04 | Deletion enumerates and verifies active stores, exports, caches, archives, and backups | 03-05-03, 03-06-02, 03-09-03 |
| DATA-05 | Retrieval pagination, relevance, latency, and duplicate behavior are bounded and measured | 03-02-01, 03-02-02, 03-04-01, 03-04-02, 03-06-02, 03-09-01 |
| DATA-06 | Immutable events are distinct from derived memory, with provenance and supersession | 03-01-01, 03-01-03, 03-03-02, 03-04-01, 03-06-01, 03-09-01 |
| DATA-09 | Affect-neutral eligibility, hard gates, neutral anchors, and traces precede salience | 03-02-01, 03-02-02, 03-04-01, 03-04-02, 03-06-02, 03-09-01 |

## Exact per-task validation map

| Task | Requirements | Threat focus | Automated command | Produced proof | Status |
|---|---|---|---|---|---|
| 03-01-01 | DATA-01, DATA-06, TEST-03 | Partial writes, schema drift, FK bypass | `uv run --locked --no-sync python -m pytest -q tests/storage/test_atomic_ledger.py` | SQLite schema/repository plus atomicity tests | pending |
| 03-01-02 | DATA-01, TEST-03 | Replay duplication, request collision | `uv run --locked --no-sync python -m pytest -q tests/storage/test_idempotency.py tests/storage/test_atomic_ledger.py` | Stable request/event identity tests | pending |
| 03-01-03 | DATA-01, DATA-06, TEST-03 | Provenance spoofing, history overwrite, cycles | `uv run --locked --no-sync python -m pytest -q tests/storage/test_provenance_supersession.py tests/storage/test_atomic_ledger.py tests/storage/test_idempotency.py` | Append-only provenance/supersession proof | pending |
| 03-02-01 | DATA-05, DATA-09, TEST-03 | Private fixture leakage, unfrozen corpus | `uv run --locked --no-sync python -m pytest -q tests/storage/test_memory_benchmark.py -k 'corpus or manifest or privacy'` | 10k-plus sanitized corpus and manifest contract | pending |
| 03-02-02 | DATA-05, DATA-09, TEST-03 | Vacuous benchmark, missing failure controls | `uv run --locked --no-sync python -m pytest -q tests/storage/test_memory_benchmark.py` | Deterministic controls-first gate engine | pending |
| 03-03-01 | DATA-01, TEST-03 | Projection divergence, non-cosine space, false ownership | `uv run --locked --no-sync python -m pytest -q tests/storage/test_projection_rebuild.py tests/storage/test_storage_owner.py` | Clear rebuild/parity and sole-owner proof | pending |
| 03-03-02 | DATA-01, DATA-06, TEST-03 | Source mutation, duplicate import, root conflation | `uv run --locked --no-sync python -m pytest -q tests/storage/test_legacy_migration.py tests/storage/test_storage_owner.py` | Copy-only two-root migration engine tests | pending |
| 03-04-01 | DATA-05, DATA-06, DATA-09, TEST-03 | Cross-scope leak, stale/superseded hit, unstable fusion | `uv run --locked --no-sync python -m pytest -q tests/storage/test_hybrid_retrieval.py -k 'gate or scope or rrf or duplicate or order'` | Pre-fusion hard gates and normalized RRF | pending |
| 03-04-02 | DATA-05, DATA-09, TEST-03 | Unstable cursor/trace, hidden salience, benchmark regression | `uv run --locked --no-sync python -m pytest -q tests/storage/test_hybrid_retrieval.py tests/storage/test_memory_benchmark.py tests/memory/test_prompt_memory_boundary.py` | Stable continuation/trace and zero-salience benchmark proof | pending |
| 03-05-01 | DATA-01, DATA-02, TEST-03 | Torn backup, in-place restore, incomplete recovery | `uv run --locked --no-sync python -m pytest -q tests/storage/test_snapshot_restore.py` | SQLite backup plus exact isolated-restore tests | pending |
| 03-05-02 | DATA-01, DATA-03, TEST-03 | False format label, scope leak, partial export success | `uv run --locked --no-sync python -m pytest -q tests/storage/test_export_delete.py tests/api/test_filesystem_contract.py` | Actual JSON-only scoped export proof | pending |
| 03-05-03 | PRES-04, DATA-01, DATA-04, TEST-03 | Ambiguous deletion, residual-copy concealment, Git leakage | `uv run --locked --no-sync python -m pytest -q tests/storage/test_export_delete.py tests/storage/test_git_hygiene.py tests/memory/test_memvid_archival_safety.py` | Plan/confirm/execute/verify deletion and residual report | pending |
| 03-06-01 | DATA-01, DATA-06, TEST-03 | Public response drift, provider-error drift, dual durable write | `uv run --locked --no-sync python -m pytest -q tests/api/test_api_compatibility.py tests/api/test_provider_compatibility.py tests/characterization/test_companion_contract.py tests/characterization/test_persistence_contract.py tests/runtime/test_base_install_startup.py` | SQLite-first turn wiring with seven-field/HTTP-200 preservation | pending |
| 03-06-02 | PRES-04, DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-09, TEST-03 | Owner ambiguity, local-boundary drift, lifecycle bypass | `uv run --locked --no-sync python -m pytest -q tests/api/test_api_compatibility.py tests/storage/test_storage_owner.py tests/storage/test_hybrid_retrieval.py tests/storage/test_export_delete.py tests/storage/test_snapshot_restore.py tests/memory/test_prompt_memory_boundary.py tests/api/test_filesystem_contract.py tests/api/test_local_boundary.py tests/runtime` | Unified storage/API/CLI boundary and explicit legacy default | pending |
| 03-07-01 | PRES-04, DATA-01, DATA-02, TEST-03 | Pre-approval real-root observation, widened proposal, synthetic tool failure | `uv run --locked --no-sync python -m pytest -q tests/storage/test_phase3_evidence.py -k 'proposal or synthetic_readiness or phase1'` | Observation-free exact proposal and synthetic readiness proof | pending |
| 03-07-02 | PRES-04, DATA-01, DATA-02, TEST-03 | Unauthorized metadata inventory/preflight | `uv run --locked --no-sync python -m pytest -q tests/storage/test_phase3_evidence.py -k 'proposal or synthetic_readiness or phase1'` | Human approval restricted to exact metadata inventory/preflight | pending |
| 03-07-03 | PRES-04, DATA-01, DATA-02, TEST-03 | Stale inventory, open writer, content leakage, premature backup | `uv run --locked --no-sync python -m pytest -q tests/storage/test_phase3_evidence.py -k 'inventory or quiescence or phase1'` | Approved fresh inventory/ticket and separate human backup approval | pending |
| 03-08-01 | PRES-04, DATA-01, DATA-02, TEST-03 | Bad copy, source drift, durable-path open, forged restore | `uv run --locked --no-sync python -m pytest -q tests/storage/test_phase3_evidence.py -k 'backup or restore or migration_plan or phase1'` | Fresh backup, isolated restore, content-free migration plan | pending |
| 03-08-02 | PRES-04, DATA-01, DATA-02, TEST-03 | Unlicensed historical read/import/switch | `uv run --locked --no-sync python -m pytest -q tests/storage/test_phase3_evidence.py -k 'backup or restore or migration_plan or phase1'` | Human authorization restricted to disposable copies and gated switch | pending |
| 03-08-03 | PRES-04, DATA-01, DATA-02, TEST-03 | Missing/stale/tampered/widened/replayed/wrong-result authority | `uv run --locked --no-sync python -m pytest -q tests/storage/test_phase3_evidence.py -k 'authorization_receipt or authorization_summary'` | Exclusive-create private summary and public-safe exact-scope receipt | pending |
| 03-09-01 | PRES-04, DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-09, TEST-03 | Receipt replay, import/projection drift, private leakage, premature switch, rollback failure, publication/CI parser substitution | `uv run --locked --no-sync python -m pytest -q tests/storage/test_phase3_evidence.py -k 'authorization_receipt or authorization_summary or import or projection or benchmark or snapshot or restore or rollback or switch or privacy or ci_publication or ci_parser'` | Receipt consumption plus migration summaries and publication/CI adversarial parsers | pending |
| 03-09-02 | PRES-04, TEST-03 | Dirty/different SHA, force/main/tag/release scope, stale/wrong remote run, auto-push | `uv run --locked --no-sync python -m pytest -q tests/storage/test_phase3_evidence.py -k 'ci_publication or ci_parser'` | Human-only exact-SHA safe-branch publication proposal and read-only verification receipt | pending |
| 03-09-03 | PRES-04, DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-09, TEST-03 | Old/missing/`not_run`/non-green CI, compatibility regression, false acceptance | `uv run --locked --no-sync python -m pytest -q tests -m 'not live'` | Full runtime suite, outside-Git exact-current CI proof, and human local acceptance | pending |

## Wave gates

| After wave | Gate command | Required result |
|---|---|---|
| 1 | `uv run --locked --no-sync python -m pytest -q tests/storage/test_atomic_ledger.py tests/storage/test_idempotency.py tests/storage/test_provenance_supersession.py` | Ledger atomicity/idempotency/provenance all pass |
| 2 | `uv run --locked --no-sync python -m pytest -q tests/storage/test_memory_benchmark.py tests/storage/test_projection_rebuild.py tests/storage/test_storage_owner.py tests/storage/test_legacy_migration.py` | Frozen instrument and projection/migration contracts pass |
| 3 | `uv run --locked --no-sync python -m pytest -q tests/storage/test_hybrid_retrieval.py tests/storage/test_snapshot_restore.py tests/storage/test_export_delete.py tests/storage/test_git_hygiene.py tests/memory/test_prompt_memory_boundary.py tests/memory/test_memvid_archival_safety.py` | Retrieval and lifecycle contracts pass |
| 4 | `uv run --locked --no-sync python -m pytest -q tests -m 'not live'` | Complete existing plus Phase 3 non-live suite passes before real operations |
| 5 | `uv run --locked --no-sync python -m pytest -q tests/storage/test_phase3_evidence.py -k 'proposal or synthetic_readiness or inventory or quiescence or phase1'` | Synthetic proposal passes before metadata approval; approved inventory then passes before separate backup approval |
| 6 | `uv run --locked --no-sync python -m pytest -q tests/storage/test_phase3_evidence.py -k 'backup or restore or migration_plan or authorization_receipt or authorization_summary or phase1'` | Backup/restore/plan and immutable exact-scope receipt pass after human data-read/import/switch approval |
| 7 | `uv run --locked --no-sync python -m pytest -q tests -m 'not live'` | Import/evidence/runtime pass, Ty publishes only the exact SHA to the named safe ref, and its five deterministic jobs are green before final acceptance |

## Human checkpoints

| Checkpoint | Happens after automation | Exact authorization |
|---|---|---|
| 03-07-02 | Exact observation-free proposal and synthetic tool/failure/privacy tests pass | Run metadata-only inventory/preflight against only the listed real paths; no backup or content read |
| 03-07-03 | Approved fresh inventory, writer/handle quiescence, capacity, and Phase 1 hash checks pass | Copy only the listed exact roots to the listed new outside-Git backup target |
| 03-08-02 | Fresh backup parity and isolated restore proof pass | Read/import only new disposable children of the durable backup and switch reads only after all declared gates |
| 03-09-02 | Implementation/evidence commit and synthetic publication parser pass on a clean exact SHA | Ty alone non-force-pushes that SHA to `phase-03-memory-integrity-ci` or dispatches its already exact ref; tasks only verify read-only |
| 03-09-03 | Publication receipt, migration evidence, full suite, and exact current-commit five-job CI are green | Accept Phase 3 after content-free CI/evidence and local loopback behavior checks |

Authentication failures are dynamic execution gates, not planned setup. No checkpoint authorizes source deletion, old-root repair, archive mutation, retention purge, tracked-data cleanup, Git-history rewrite, graph/RLM, affect salience, frontend redesign, authentication, or an at-rest-encryption claim.

## Nyquist execution rule

For every behavior-adding task:

1. Add the named failing tracer and run its exact command to demonstrate RED.
2. Implement the smallest complete behavior that satisfies the task contract and run the same command to GREEN.
3. Refactor only while that command remains green.
4. Run the wave gate before a dependent wave starts.
5. Preserve exact outputs in the plan summary; a skipped, truncated, resource-limited, empty, or structurally incomplete result is non-pass.

For Plans 03-07 through 03-09, public evidence contains only allowlisted paths/aliases, counts, sizes, timestamps, statuses, HMACed opaque fixture values, and digests. Conversation content, document text, embeddings, raw metadata, and secrets stay in mode-restricted outside-Git attempt artifacts.

## Validation approval

- [x] Every plan task has an automated command.
- [x] Every Phase 3 requirement appears in frontmatter and concrete task coverage.
- [x] Same-wave plans have disjoint `files_modified` sets.
- [x] The sanitized benchmark/instrument is planned before optimization or real-data migration.
- [x] Real data, backup/restore, and read switching are separated by blocking human checkpoints.
- [x] Full Phase 2 behavior is a pre-migration and post-switch gate.
- [x] Final acceptance requires exact current-commit deterministic CI; historical/live/model lanes cannot substitute.
- [x] Only the blocking human-action checkpoint may publish/dispatch the exact SHA; no task auto-pushes or mutates a remote ref.
- [ ] Wave 0/new tracer files exist; they are created RED-first during execution.
- [ ] Human checkpoints complete during execution.

**Approval state:** planned and Nyquist-mapped; execution evidence pending.
