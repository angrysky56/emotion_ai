---
phase: 01-preservation-and-trusted-baseline
verified: 2026-08-19T17:16:49Z
status: passed
score: 30/30 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 29/30
  gaps_closed:
    - "The restore-summary validator now requires the exact seven ordered checks, derives status/gates from them, validates inventory/ticket/backup/private bindings, and rejects incomplete or forged evidence."
  gaps_remaining: []
  regressions: []
---

# Phase 1: Preservation and Trusted Baseline Verification Report

**Phase Goal:** Make Aura safe to change without losing data or mistaking scripts for tests.
**Verified:** 2026-08-19T17:16:49Z
**Status:** passed
**Re-verification:** Yes — after gap closure in `bdf3f4b`, `a725749`, `6f1011f`, and `968bc9c`

## Verdict

Phase 1 now achieves its goal. It has a real content-safe inventory, an outside-Git byte-identical backup, an isolated restore proof, a deterministic 131-test suite, working local-runtime boundaries, and a final validator that fails closed against incomplete or forged evidence.

The prior empty-check exploit is closed. Independent adversarial re-execution rejected empty, missing, duplicate, reordered, unknown, blocked-with-pass, broken digest binding, and missing binding-field cases while continuing to accept the real canonical summary.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---:|---|---|---|
| 1 | Every declared active, backup, test, and archive root can be inventoried without committable conversation content. | ✓ VERIFIED | Real public inventory has 14 roots across all four roles; allowlist/privacy tests pass. |
| 2 | Inventory never follows symlinks or reads special files as ordinary data. | ✓ VERIFIED | `inventory.py` uses no-follow traversal; FIFO, socket, symlink, and symlink-parent behavioral tests pass. |
| 3 | Missing or unrun required inventory work cannot become pass. | ✓ VERIFIED | Required-missing-root and changed-while-hashing tests pass; status aggregation is fail-closed. |
| 4 | A complete synthetic persistence root can be copied/restored without source mutation. | ✓ VERIFIED | Backup/restore behavioral suite passes source-before/source-after/destination parity. |
| 5 | Chroma is opened only on a disposable restore copy. | ✓ VERIFIED | `restore.py` imports Chroma after copying into `TemporaryDirectory`; path-spy test proves source and durable backup are never supplied to `PersistentClient`. |
| 6 | Required restore checks cannot be omitted while a pass is produced. | ✓ VERIFIED | Canonical artifact returned 0; 12 adversarial variants returned 4, including the former `checks: []` exploit. |
| 7 | One root command runs deterministic assertion-based tests with a truthful exit status. | ✓ VERIFIED | `uv run python -m pytest -q` completed: 131 passed in 30.76s. |
| 8 | Every legacy test-shaped script is classified exactly once without broadening discovery. | ✓ VERIFIED | Exact-set test passes; manifest classifies 38 scripts into explicit non-default lanes. |
| 9 | New generated/runtime/secret artifacts are blocked while grandfathered tracked artifacts remain intact. | ✓ VERIFIED | Repository-hygiene tests match the exact 59-artifact Git baseline and exercise a synthetic new candidate. |
| 10 | Valuable pure legacy cases execute as assertions against production symbols. | ✓ VERIFIED | MCP parameter, MCP formatting, and NumPy characterization modules import and exercise production code. |
| 11 | Migrated cases require no server, live model, GPU, network, or persistent database. | ✓ VERIFIED | Tests use in-memory values/fakes; the canonical suite passed without live services. |
| 12 | Corresponding legacy scripts remain preserved outside default pytest discovery. | ✓ VERIFIED | Legacy paths still exist; `testpaths = ["tests"]`; 131-test collection excludes legacy roots. |
| 13 | Aura defaults to loopback, uses explicit origins, and rejects wildcard origins. | ✓ VERIFIED | `server_host(None)` returns `127.0.0.1`; CORS uses explicit configured origins and `allow_credentials=False`; request tests pass. |
| 14 | An untrusted browser cannot drive a simple non-JSON request while an allowed local browser can use JSON. | ✓ VERIFIED | Real-ASGI subprocess tests produce 400/422 for untrusted/non-JSON attempts and 200 for configured-origin JSON. |
| 15 | Normal local use has no account, credential, or sign-in requirement. | ✓ VERIFIED | The conversation probe succeeds with no cookie/token/auth header; production route has no auth dependency. |
| 16 | Request characterization starts no production lifespan service and calls no Ollama/network service. | ✓ VERIFIED | Child probe forbids network connects, suppresses lifespan, and asserts no production initializer calls. |
| 17 | Ordinary local identifiers retain their filename behavior. | ✓ VERIFIED | Production path helper and direct filesystem tests preserve ordinary and Unicode identifiers. |
| 18 | Traversal, symlinked parents/final files, and unsupported formats cannot escape the data root. | ✓ VERIFIED | Pure helper and production filesystem subprocess tests pass with no outside writes. |
| 19 | Export success names an actually written JSON file without claiming complete Phase 3 history. | ✓ VERIFIED | Endpoint checks file existence/JSON; unwritten paths return 500; empty arrays are explicitly characterized as Phase 1 baseline. |
| 20 | A fake-provider conversation captures the current visible response schema without Ollama. | ✓ VERIFIED | Production `/conversation` route returns the asserted typed shape in a network-forbidden child. |
| 21 | Persistence exchange/session shape and failure behavior are explicit. | ✓ VERIFIED | Immediate persistence and degraded-storage/background fallback cases are assertion-tested. |
| 22 | Volatile IDs/timestamps, model prose, and hidden reasoning are normalized or excluded. | ✓ VERIFIED | Probe normalization and response assertions avoid unstable prose and require hidden reasoning absence. |
| 23 | The real inventory covers every declared role and stays content-safe. | ✓ VERIFIED | Validator exits 0; 662 files, 992,522,715 bytes, 77 databases, and 14 roots are represented only by safe aggregates/digests. |
| 24 | Both likely-active Chroma roots remain preserved and neither is declared canonical. | ✓ VERIFIED | `aura_chroma_db` and `aura_backend/aura_chroma_db` both exist in source and backup as `active-01`/`active-02`; no phase-range deletion exists. |
| 25 | Private per-file evidence remains outside Git and public evidence passes its privacy schema. | ✓ VERIFIED | Private manifest exists under `/backup` mode 0600 and its SHA-256 matches the public pointer; privacy/schema tests pass. |
| 26 | The real backup was gated by no writers/open handles and explicit quiescence. | ✓ VERIFIED | Ticket is digest-bound and records passing path, source, open-handle, process, and space checks; backup result binds to that ticket. |
| 27 | The approved source set includes both active roots and all inventory roles. | ✓ VERIFIED | Inventory/ticket/backup/restore share source-set digest `350091…4c78`; durable backup contains all 14 aliases. |
| 28 | A complete immutable backup exists outside Git and sources remained byte-identical. | ✓ VERIFIED | `/backup/.../backup` exists; private result records 662 files and equal source-before/source-after/destination digest `f5259d…5cef`. |
| 29 | A disposable restore proves hash, SQLite, FK, Chroma-count, and opaque-retrieval parity. | ✓ VERIFIED | Actual restore artifact contains all seven passing checks, 10 collections, 1,204 records, and 2 retrieval fixtures; private/public and backup digests match. |
| 30 | The two active eight-row FK anomalies match restore exactly and remain explicitly open, not “clean.” | ✓ VERIFIED | Public inventory reports 8 and identical `f39db0…d834` fingerprints for each active root; restore code compares count/fingerprint facts; `STATE.md` explicitly defers them to Phase 3 before migration/deletion. |

**Score:** 30/30 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `aura_backend/preservation/manifest.py` | Typed private/public evidence contract | ✓ VERIFIED | Substantive serializers, fixed statuses, aggregate anomaly reporting. |
| `aura_backend/preservation/inventory.py` | No-follow, content-safe inventory | ✓ VERIFIED | Metadata/hash collection and read-only SQLite checks; extensive behavioral tests. |
| `aura_backend/preservation/backup.py` | Quiescence-bound immutable copy | ✓ VERIFIED | Disjoint paths, fresh tickets, exclusive destination, pre/post/destination parity. |
| `aura_backend/preservation/restore.py` | Disposable structural/retrieval verification | ✓ VERIFIED | Copies durable backup before lazy Chroma open; closes clients and removes disposable child. |
| `aura_backend/preservation/cli.py` | Truthful end-to-end evidence gate | ✓ VERIFIED | Enforces the exact seven-check sequence, derived status/gates, complete schemas, and inventory/ticket/backup/private bindings. |
| `tests/preservation/` | Preservation/privacy/false-success regression suite | ✓ VERIFIED | Includes incomplete/unbound evidence regressions; full suite passes. Independent re-verification additionally exercised reordered and blocked-with-pass cases. |
| `tests/api/` and `tests/characterization/` | Local, filesystem, companion, persistence contracts | ✓ VERIFIED | Real production app/symbols exercised with bounded fakes and temporary storage. |
| `aura_backend/runtime_security.py` | Loopback, CORS, and containment helpers | ✓ VERIFIED | Imported by `main.py` and exercised directly and at request level. |
| `.planning/evidence/phase-01/inventory-summary.json` | Sanitized real inventory | ✓ VERIFIED | Valid schema; all roles and anomalies present without content fields. |
| `.planning/evidence/phase-01/quiescence-summary.json` | Bound quiescence ticket pointer | ✓ VERIFIED | Private ticket exists and digest matches; historical ticket expiration is expected after copy. |
| `.planning/evidence/phase-01/restore-drill-summary.json` | Sanitized final restore evidence | ✓ VERIFIED | Actual artifact has seven passing checks and all referenced private digests match. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `preservation/cli.py` | `inventory.py` / `manifest.py` | Inventory and schema validation | ✓ WIRED | Real summary validator exits 0 for all four required roles. |
| `backup.py` | inventory + quiescence evidence | Digest and source-set binding | ✓ WIRED | Private hashes independently recomputed and matched. |
| `restore.py` | `chromadb.PersistentClient` | Lazy open after disposable copy | ✓ WIRED | Source/durable-path spy test passes. |
| `main.py` | `runtime_security.py` | CORS, host, profile/export paths | ✓ WIRED | Production app and filesystem subprocess tests pass. |
| characterization tests | production route/symbols | Direct imports and isolated ASGI calls | ✓ WIRED | No mock-only surrogate implementation. |
| public restore summary | inventory → ticket → backup → restore chain | `validate-restore-summary` | ✓ WIRED | Canonical summary and every referenced private artifact validate as one chain; adversarial substitutions fail. |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Produces Real Data | Status |
|---|---|---|---|---|
| Inventory evidence | File/database metadata and opaque hashes | All 14 declared repository roots | Yes — 662 real files, no content fields | ✓ FLOWING |
| Backup evidence | Source/destination manifests | Real inventoried source set → `/backup` | Yes — 662-file exact parity | ✓ FLOWING |
| Restore evidence | Structural and retrieval facts | Durable backup → disposable copy | Yes — 10 collections/1,204 records/2 fixtures | ✓ FLOWING |
| `/conversation` characterization | Request → provider result → persistence exchange → response | Production route with deterministic fakes | Yes — stable typed response and captured exchange | ✓ FLOWING |
| `/export/{user_id}` characterization | Identifier → contained path → JSON file → response | Production `AuraFileSystem` in temp root | Yes for the explicitly empty Phase 1 baseline | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Canonical deterministic suite | `uv run python -m pytest -q` | 131 passed in 30.76s | ✓ PASS |
| Exact inventory validator | `validate-summary ... --require-role active --require-role backup --require-role test --require-role archive` | exit 0 | ✓ PASS |
| Historical quiescence-chain validation | `validate-quiescence ...` without freshness requirement | exit 0 | ✓ PASS |
| Exact final restore validator on real artifact | `validate-restore-summary ... --require-pass --require-source-unchanged --require-fk-parity --require-retrieval-parity` | exit 0 | ✓ PASS |
| Prior empty-check exploit | Validator against a temp digest-bound `status: pass`, `checks: []` summary | exit 4 | ✓ PASS |
| Missing/duplicate/reordered/unknown checks | Four independently forged temp summaries | each exit 4 | ✓ PASS |
| Contradictory check status | `retrieval_parity: blocked` with top-level `status: pass` | exit 4 | ✓ PASS |
| Broken evidence bindings | Forged private, backup, source-set, inventory, and quiescence SHA-256 fields | each exit 4 | ✓ PASS |
| Missing required binding field | Summary without `backup_result_sha256` | exit 4 | ✓ PASS |
| TypeScript static check | `npx tsc --noEmit` | exit 0 | ✓ PASS |
| Frontend production build | `npm run build` | Vite 8.0.10 build succeeded | ✓ PASS |
| Patch hygiene | `git diff --check` | exit 0 | ✓ PASS |

### Probe Execution

No shell probe was declared and no `scripts/**/tests/probe-*.sh` exists. The phase's Python subprocess probe is part of the deterministic suite and passed; it forbids network access and production lifespan initialization.

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
|---|---|---|---|
| PRES-01 | 01-01, 01-08, 01-10 | ✓ SATISFIED | Real content-safe inventory covers every declared role and both active candidates. |
| PRES-02 | 01-02, 01-09, 01-10 | ✓ SATISFIED | Outside-Git backup and isolated restore exist with independently matched digests. |
| PRES-03 | 01-04–01-07 | ✓ SATISFIED | API, persistence, companion, MCP, NumPy, and failure contracts are assertion-tested. |
| PRES-04 | 01-01, 01-03, 01-08, 01-10 | ✓ SATISFIED | Exact tracked-artifact baseline passes; phase diff deletes no files. |
| TEST-01 | 01-03 | ✓ SATISFIED | One root pytest command collected and passed 131 deterministic tests. |
| TEST-02 | 01-03, 01-04 | ✓ SATISFIED | All 38 legacy scripts are uniquely classified; boolean/print outcomes are explicitly untrusted. |
| LOCAL-01 | 01-05 | ✓ SATISFIED | Loopback default and explicit host override are tested. |
| LOCAL-02 | 01-05 | ✓ SATISFIED | Explicit CORS, wildcard rejection, no credentials, and strict JSON behavior are request-tested. |
| LOCAL-03 | 01-06 | ✓ SATISFIED | Traversal/symlink/format containment and actual-file export behavior are tested. |
| LOCAL-04 | 01-05 | ✓ SATISFIED | Normal local conversation succeeds without account or credentials. |

No Phase 1 requirement is orphaned from its plans.

### Locked Decision Coverage

| Decision | Status | Evidence |
|---|---|---|
| D-01 — private local app, no mandatory sign-in; loopback default and LAN opt-in | ✓ VERIFIED | Runtime configuration and request-level tests. |
| D-02 — preserve before delete/migrate; isolated restore; content-safe evidence | ✓ VERIFIED | Real backup/restore chain; both active roots remain; no deletion in phase diff. |
| D-03 — separate truthful result classes; no false pass from partial/unavailable evidence | ✓ VERIFIED | Typed statuses, derived restore status/gates, exact check-set enforcement, and adversarial binding tests now fail closed. |
| D-04 — Ollama is optional and absent from deterministic tests | ✓ VERIFIED | Network-forbidden fakes and pytest markers; full suite passed without live model calls. |
| D-05 — characterize before refactor and preserve safe identifiers | ✓ VERIFIED | Characterization tests target production behavior; containment retains ordinary IDs. |

### Anti-Patterns and Disconfirmation

| File | Line | Pattern | Severity | Impact |
|---|---:|---|---|---|
| `tests/preservation/test_backup_restore.py` | 830–902 | Adversarial evidence completeness/binding test | ℹ️ INFO | Committed regression covers empty, missing, duplicate, unknown, and five broken bindings; independent spot-check also covered reordered and contradictory-status cases. |
| `.planning/STATE.md` | 11–15 | Verification headline synchronized | ℹ️ INFO | Now correctly records 131 tests and the exact 59-path, 153,612,467-byte baseline. |
| `aura_backend/main.py` | 354–356 | Empty export arrays | ℹ️ INFO | Explicitly documented/tested Phase 1 baseline, not a completeness claim; full export is Phase 3. |

No unreferenced `TBD`, `FIXME`, or `XXX` marker was found in phase-modified implementation/test files. The phase commit range `fd75ef5^..HEAD` contains no deleted paths. Both active roots still exist. No original or durable Chroma root was opened during this verification.

### Human Verification Required

None. Phase 1's sole human checkpoint was the already-completed quiescence approval preceding the immutable copy. No visual, external-service, or untested transition claim is needed for this verdict.

### Deferred Items

Complete export/deletion semantics, storage ownership, FK diagnosis/repair, and tracked-data cleanup are explicitly assigned to Phase 3 and were not treated as Phase 1 gaps. The Phase 1 restore-validator defect was fixed and re-verified rather than deferred.

### Gaps Summary

None. The prior false-success gap is closed, all 30 truths pass, and no regression or new human-verification item was found. Phase 3 cleanup/migration remains explicitly unauthorized until its own gates; that planned boundary is not a Phase 1 gap.

---

_Verified: 2026-08-19T17:16:49Z_
_Verifier: Codex (gsd-verifier)_
