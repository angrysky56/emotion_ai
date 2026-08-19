# Phase 1: Preservation and Trusted Baseline - Research

**Researched:** 2026-08-19
**Domain:** Local data preservation, restore verification, deterministic Python testing, and loopback-only FastAPI boundaries
**Confidence:** MEDIUM — repository findings were directly verified; framework guidance came from current official documentation reached through WebSearch because the configured Context7 client was unavailable. [VERIFIED: codebase and local command inspection] [CITED: https://docs.pytest.org/en/stable/]

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### D-01 Local trust model
- Aura is run privately by one user and must not gain a sign-in flow.
- Default to loopback and explicit browser origins; LAN access is opt-in.

### D-02 Preservation
- Do not delete or migrate any database or backup until an isolated restore is
  verified against counts, integrity checks, and representative retrieval fixtures.
- Inventory metadata and checksums without copying personal content into reports.

### D-03 Test truthfulness
- Deterministic tests, live services, optional models, GPU checks, and diagnostic
  scripts must be separate result classes.
- A printed success message, returned boolean, partial collection, or unavailable
  external service is not a passing test.

### D-04 Models
- Ollama is available locally; `ornith:latest` may be used for bounded optional live
  tests when model behavior is genuinely under evaluation.
- Core tests must remain fast and deterministic without Ollama.

### D-05 Refactoring restraint
- Characterize user-visible and persistence behavior before moving implementations.
- Preserve ordinary existing user identifiers while rejecting filesystem traversal.

### Codex's Discretion
- Inventory report schema and checksum algorithm.
- Which legacy scripts contain assertions worth migrating first.
- Exact temporary-directory structure for restore drills.

### Deferred Ideas (OUT OF SCOPE)
- Provider consolidation and Ornith quality evaluation: Phase 2.
- Storage migration and tracked-data removal: Phase 3 after the restore gate.
- Frontend redesign: Phase 5.
- Remote Git-history rewrite: Phase 6 with explicit approval.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRES-01 | Inventory every active, backup, test, and archived data root without exposing conversation content. | Use a no-follow metadata walker, SHA-256 file digests, typed root roles, read-only SQLite checks, and redacted Chroma summaries. [CITED: https://docs.python.org/3.12/library/pathlib.html] |
| PRES-02 | Create an offline backup outside Git and prove restoration into an isolated temporary location before deletion or migration. | Stop Aura/Chroma, copy complete persistence roots to the separate `/backup` mount, verify manifests, then restore into `tmp_path`/`TemporaryDirectory` and open only the copy. [CITED: https://cookbook.chromadb.dev/strategies/backup/] |
| PRES-03 | Capture representative API, persistence, and companion behavior before changing it. | Use fake collaborators and a quarantined subprocess probe for `aura_backend.main`; keep pure boundary tests import-light. [VERIFIED: aura_backend/main.py import and lifespan structure] |
| PRES-04 | Keep generated databases, backups, exports, profiles, logs, and secrets out of new commits. | Extend/check ignore coverage and add a tracked-artifact regression check that grandfathers existing tracked artifacts without deleting them. [VERIFIED: .gitignore and git ls-files inspection] |
| TEST-01 | One root command runs deterministic tests with unambiguous semantics. | Canonical command is `uv run python -m pytest -q`; it currently collects and passes 13 tests while `uv run pytest -q` fails to import `aura_backend`. [VERIFIED: commands run 2026-08-19] |
| TEST-02 | Classify legacy diagnostics as tests, live checks, migration tools, or archives; print/boolean scripts are not tests. | Use a checked-in classification manifest and migrate only production-invoking, assertion-worthy cases. [VERIFIED: aura_backend/tests and archive_unused inspection] |
| LOCAL-01 | Bind loopback by default; LAN is explicit configuration. | Preserve `server_host(None) == "127.0.0.1"` and test launcher configuration. [VERIFIED: aura_backend/runtime_security.py and tests/test_runtime_security.py] |
| LOCAL-02 | Use explicit browser origins, reject wildcard CORS, and keep strict JSON content handling. | Test real CORS preflight/denial and missing or non-JSON Content-Type behavior. [CITED: https://fastapi.tiangolo.com/advanced/strict-content-type/] |
| LOCAL-03 | Caller identifiers/formats cannot escape data roots or claim unwritten exports. | Keep allowlisted formats and validate the final resolved path remains below the resolved storage root. [CITED: https://cwe.mitre.org/data/definitions/22] |
| LOCAL-04 | No account or sign-in for normal local use. | Characterize primary local API access without auth and do not introduce identity infrastructure. [VERIFIED: CONTEXT.md D-01 and current route inspection] |
</phase_requirements>

## Summary

Phase 1 should build two explicit gates: a **preservation gate** and a **test-truth gate**. The preservation gate inventories every known root without serializing documents/messages, creates a quiesced full-directory Chroma backup on the separate `/backup` filesystem, verifies every copied regular file by SHA-256, and proves that a second copy opened from a temporary directory has the same structural counts and retrieval fingerprints. It must never call the current automatic backup cleanup, open originals through a new Chroma client, or restore over an existing path. [VERIFIED: aura_backend/database_protection.py currently copies a live directory and deletes backups beyond ten] [CITED: https://cookbook.chromadb.dev/strategies/backup/]

The test-truth gate should retain `tests/` as the only deterministic discovery root, make `uv run python -m pytest -q` the canonical command, register strict categories, and classify every legacy script before selectively porting value. The current root suite is real but narrower than `.planning/STATE.md` implies: `uv run python -m pytest -q` passes 13 tests, whereas the bare `uv run pytest -q` aborts collection because the console entry point does not add the repository root to `sys.path`. [VERIFIED: local pytest runs 2026-08-19] [CITED: https://docs.pytest.org/en/stable/how-to/usage.html]

The loopback boundary is partially implemented in `runtime_security.py` and `main.py`, but existing tests exercise helpers only. Phase 1 should add request-level tests for allowed and disallowed CORS origins, strict JSON Content-Type rejection, traversal payloads, implemented export formats, and no-auth local operation. CORS and strict JSON handling matter together: FastAPI documents the missing-Content-Type attack specifically for unauthenticated localhost applications. [VERIFIED: aura_backend/main.py CORS configuration] [CITED: https://fastapi.tiangolo.com/advanced/strict-content-type/]

**Primary recommendation:** implement a read-only preservation CLI plus a separate restore verifier, execute the real drill against `/backup/aura-preservation/<UTC timestamp>/`, and block all storage cleanup/refactoring until its manifest, integrity, count, and retrieval-fingerprint comparisons pass. [VERIFIED: `/backup` is a writable separate filesystem with about 253 GB free]

## Current Repository Evidence

This section is descriptive evidence, not a recommendation.

| Finding | Evidence | Planning consequence |
|---------|----------|----------------------|
| Known data/archive roots total about 990,118,794 bytes, including about 333 MB under `aura_backend/auto_backups`, 468 MB under `aura_backend/chromadb_backups`, 143 MB under `archive_unused`, and two likely active Chroma roots. | Read-only `du`/`find` on 2026-08-19. [VERIFIED: local filesystem metadata inspection] | Inventory all roots; do not assume the 33 MB planning estimate is current. |
| There are 77 SQLite-like files outside `.git`, `.venv`, and `node_modules`; Git currently tracks 47 database/vector-like artifacts totaling about 153 MB. | `find`, `git ls-files`, and `stat`. [VERIFIED: local command inspection] | PRES-04 must prevent new artifacts while preserving already tracked history until Phase 3. |
| `aura_chroma_db/chroma.sqlite3` and `aura_backend/aura_chroma_db/chroma.sqlite3` each report `PRAGMA integrity_check = ok`, four collections, and eight `foreign_key_check` result rows. | Opened with `sqlite3 -readonly`; no row content was printed. [VERIFIED: read-only SQLite inspection 2026-08-19] | Gate on exact source/restore parity and separately record the baseline FK anomaly; do not equate `integrity_check=ok` with zero FK violations. |
| `aura_backend/database_protection.py` uses `shutil.copytree()` while the service may be live, then removes old backup directories beyond ten. | `_create_safety_backup()` and `_cleanup_old_backups()`. [VERIFIED: aura_backend/database_protection.py] | Do not reuse this service for the preservation artifact; Phase 1 forbids deletion and requires quiescence. |
| `pyproject.toml` limits discovery to `tests/` with strict config/markers; the one root file contains 13 assertion-based tests. | Configuration and test source. [VERIFIED: pyproject.toml and tests/test_runtime_security.py] | Keep the boundary; do not point pytest at `aura_backend/tests`. |
| Bare `uv run pytest -q` fails with `ModuleNotFoundError: aura_backend`; `uv run python -m pytest -q` passes 13/13 in 0.02 seconds. | Both commands run from repository root. [VERIFIED: local pytest runs 2026-08-19] | Document one exact root command or add explicit packaging/pythonpath configuration; do not claim both commands work. |
| Active legacy `aura_backend/tests/test_*.py` files use `return True/False`, prints, top-level path manipulation, real models/services, and `sys.exit`; no active file contains native `assert` statements. | Ripgrep and targeted source inspection. [VERIFIED: aura_backend/tests] | Treat them as unclassified scripts, not a test suite. |
| `main.py` imports model, Chroma, MCP, autonomic, and embedding modules at module import; the embedding model itself is lazy, but the heavyweight libraries are still imported before lifespan. | Module imports plus `shared_embedding_service.py`. [VERIFIED: aura_backend/main.py and shared_embedding_service.py] | Keep ordinary unit collection away from `main`; isolate the few full-route characterizations. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Metadata-only inventory | Backend/CLI | Database/Storage | A local CLI owns traversal/report policy; storage is read-only input. [VERIFIED: phase boundary] |
| Offline backup and restore drill | Backend/CLI | External backup filesystem | The CLI coordinates quiescence, copy, verification, and isolated restore; `/backup` owns the durable copy. [VERIFIED: environment audit] |
| SQLite/Chroma integrity inspection | Database/Storage | Backend/CLI | Native database checks and Chroma APIs provide evidence; the CLI redacts and compares it. [CITED: https://sqlite.org/pragma.html] |
| Deterministic test discovery | Test harness | Backend modules | Pytest owns collection/result semantics; production modules expose narrow test seams. [CITED: https://docs.pytest.org/en/stable/example/pythoncollection.html] |
| Legacy script classification | Test harness | Operations | Classification decides which lane owns each script before migration. [VERIFIED: legacy script inspection] |
| Local browser boundary | API/Backend | Browser/Client | Uvicorn bind, CORS, Content-Type, and path validation are server controls; browser preflight is secondary. [CITED: https://www.uvicorn.org/settings/] |
| No-sign-in local flow | API/Backend | Browser/Client | The API remains usable without account state while network/origin boundaries contain access. [VERIFIED: CONTEXT.md D-01] |

## Recommended Architecture

### Preservation flow

```text
Known roots + explicit role map
          |
          v
No-follow metadata walker ---- symlink/special file? ----> record + fail-safe review
          |
          v
SHA-256 + size + SQLite read-only checks
          |
          v
Sanitized source manifest (no documents/messages)
          |
          v
Aura/Chroma stopped? -- no --> STOP (no backup claim)
          |
         yes
          v
Copy complete roots to /backup/.../.partial
          |
          v
Destination hashes equal source? -- no --> FAIL, retain evidence, originals untouched
          |
         yes
          v
Finalize backup directory
          |
          v
Copy backup into TemporaryDirectory (never open backup in place)
          |
          v
SQLite integrity + FK parity + Chroma counts + opaque retrieval fingerprints
          |
          +---- mismatch/error ----> FAIL gate; no delete/migrate/refactor
          |
         pass
          v
Commit sanitized summary; keep detailed private manifest beside backup
```

The copy must include `chroma.sqlite3`, WAL-related state, and UUID-named vector-index directories as one persistence unit; SQLite-only backup is not a complete Chroma backup. The Chroma storage documentation describes the SQLite metadata/WAL plus per-collection HNSW directories, and its backup guide requires stopping the instance for a filesystem backup. [CITED: https://cookbook.chromadb.dev/core/storage-layout/] [CITED: https://cookbook.chromadb.dev/strategies/backup/]

### Test-truth flow

```text
legacy *.py
    |
    v
classification manifest
    |
    +--> deterministic candidate --> rewrite against production code + assert --> tests/
    +--> live service/model ------> optional registered marker; never default
    +--> diagnostic/benchmark ----> scripts/diagnostics; exit code + evidence
    +--> migration/recovery ------> scripts/migrations; manual approval only
    +--> obsolete/vacuous --------> archive classification; never collected

tests/ --> uv run python -m pytest -q --> one unambiguous exit status
```

### Recommended project structure

```text
aura_backend/
├── preservation/
│   ├── __init__.py
│   ├── inventory.py        # no-follow metadata/checksum/read-only SQLite scan
│   ├── backup.py           # quiesced copy to new outside-Git destination
│   ├── restore.py          # copy backup to temp, inspect only temp copy
│   ├── manifest.py         # versioned schemas + redaction rules
│   └── cli.py              # explicit inventory/backup/verify subcommands
tests/
├── preservation/
│   ├── test_inventory.py
│   ├── test_backup_restore.py
│   └── test_manifest_privacy.py
├── characterization/
│   ├── test_api_contract.py
│   ├── test_persistence_contract.py
│   └── test_companion_contract.py
├── test_runtime_security.py
└── conftest.py
.planning/evidence/phase-01/
├── inventory-summary.json       # safe-to-commit aggregate only
├── restore-drill-summary.json   # safe-to-commit pass/fail and opaque hashes
└── legacy-test-classification.json
```

This structure keeps preservation code independent of `main.py`, so inventory and restore tooling cannot accidentally start the API, model providers, Chroma writers, or automatic backup cleanup. [VERIFIED: current import/lifespan coupling in aura_backend/main.py]

## Standard Stack

### Core

| Component | Current resolved version | Purpose | Phase decision |
|-----------|--------------------------|---------|----------------|
| Python | 3.12.9 | CLI, filesystem, hashing, SQLite API, tests | Keep current runtime; use stdlib first. [VERIFIED: `python3 --version`] |
| SQLite runtime via Python | 3.47.1 | Read-only checks and online backup for standalone SQLite snapshots | Use the Python runtime for automated evidence so results match Aura's interpreter. [VERIFIED: `sqlite3.sqlite_version`] |
| pytest | 9.0.3 (PyPI latest observed 9.1.1, published 2026-06-19) | Deterministic runner | Keep locked/resolved version; do not upgrade during baseline capture. [VERIFIED: local import and PyPI registry query] |
| pytest-asyncio | 1.3.0 (PyPI latest observed 1.4.0, published 2026-05-26) | Explicit async tests | Keep current; declare strict async behavior and marks. [VERIFIED: local import and PyPI registry query] |
| ChromaDB | 1.5.9 (PyPI latest observed 1.5.9, published 2026-05-05) | Open only restored copies for collection counts/retrieval checks | Never point a validation client at originals. [VERIFIED: local import and PyPI registry query] |
| FastAPI | 0.136.1 (PyPI latest observed 0.141.1, published 2026-07-29) | Request/response characterization and strict JSON behavior | Keep current baseline. [VERIFIED: local import and PyPI registry query] |
| HTTPX | 0.28.1 (latest observed 0.28.1, published 2024-12-06) | ASGI/API test transport via TestClient | Already declared; no new package. [VERIFIED: local import and PyPI registry query] |

### Supporting

| Component | Current resolved version | Purpose | When to use |
|-----------|--------------------------|---------|-------------|
| Starlette | 1.0.0 | CORS middleware and TestClient foundation | Request-level origin tests through FastAPI. [VERIFIED: local import] |
| Uvicorn | 0.46.0 | Local socket binding | Runtime host behavior only; tests target `server_host`. [VERIFIED: local import] |
| `hashlib.file_digest` | Python 3.12 stdlib | Streaming SHA-256 | Every regular file in a manifest. [CITED: https://docs.python.org/3.12/library/hashlib.html] |
| `pathlib.Path.lstat` | Python 3.12 stdlib | Metadata without following symlinks | Inventory traversal and containment. [CITED: https://docs.python.org/3.12/library/pathlib.html] |
| `tempfile.TemporaryDirectory` / pytest `tmp_path` | stdlib / pytest | Isolated restore target | Every automated restore and fixture. [CITED: https://docs.python.org/3/library/tempfile.html] |
| `/backup` mount | about 253 GB free, writable | Offline/outside-Git preservation destination | Real preservation artifact, not test fixtures. [VERIFIED: findmnt, test -w, and df] |

### Alternatives considered

| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| SHA-256 | BLAKE2 | Both are stdlib; SHA-256 is the more interoperable manifest format and performance is adequate for about 1 GB. No new package is justified. [CITED: https://docs.python.org/3.12/library/hashlib.html] |
| Quiesced full Chroma directory copy | SQLite `Connection.backup()` alone | Online backup is correct for the SQLite file but omits Chroma's persisted vector-index directories; it cannot satisfy full Chroma restoration. [CITED: https://sqlite.org/backup.html] [CITED: https://cookbook.chromadb.dev/core/storage-layout/] |
| `uv run python -m pytest` | bare `uv run pytest` | Module invocation adds the current directory to `sys.path`; the bare command currently fails in this flat layout. [CITED: https://docs.pytest.org/en/stable/explanation/pythonpath.html] |
| Production-module import in every test | One quarantined subprocess characterization probe | The child can run from a temp cwd with fake services and terminate heavyweight imports after capture; ordinary unit tests stay fast. [VERIFIED: current main.py imports] |

**Installation:** none. This phase should add no dependencies and should not re-lock or upgrade the environment while establishing the baseline. [VERIFIED: all recommended capabilities are present in stdlib or current lock]

## Package Legitimacy Audit

No external package installation is required. An informational legitimacy-seam check was run for the already-present packages; it returned `SUS` for all because download telemetry was unavailable, and additionally called some recent releases “too new.” That result is not evidence that the installed packages are malicious; their package identities are independently anchored by the current repository and official documentation. If a plan unexpectedly adds or upgrades any package, it must insert a human verification checkpoint before installation. [VERIFIED: `gsd-tools query package-legitimacy check` output 2026-08-19]

| Package | Registry | Source repository | Seam verdict | Disposition |
|---------|----------|-------------------|--------------|-------------|
| pytest | PyPI | github.com/pytest-dev/pytest | SUS: unknown downloads | Keep current lock; no install. [CITED: https://docs.pytest.org/en/stable/] |
| pytest-asyncio | PyPI | github.com/pytest-dev/pytest-asyncio | SUS: unknown downloads | Keep current lock; no install. [CITED: https://pytest-asyncio.readthedocs.io/] |
| FastAPI | PyPI | github.com/fastapi/fastapi | SUS: recent + unknown downloads | Keep current lock; no install. [CITED: https://fastapi.tiangolo.com/] |
| HTTPX | PyPI | github.com/encode/httpx | SUS: unknown downloads | Keep current lock; no install. [CITED: https://www.python-httpx.org/] |
| ChromaDB | PyPI | github.com/chroma-core/chroma | SUS: unknown downloads | Keep current lock; no install. [CITED: https://docs.trychroma.com/] |
| Starlette | PyPI | github.com/Kludex/starlette | SUS: recent + unknown downloads | Transitive/current only; no install. [CITED: https://www.starlette.io/] |
| Uvicorn | PyPI | github.com/Kludex/uvicorn | SUS: recent + unknown downloads | Keep current lock; no install. [CITED: https://www.uvicorn.org/] |

**Packages removed due to SLOP verdict:** none. [VERIFIED: legitimacy seam]

**Packages flagged as suspicious for any future install:** all rows above solely because of seam telemetry/release-age signals; no Phase 1 install is planned. [VERIFIED: legitimacy seam]

## Architecture Patterns

### Pattern 1: Manifest as an evidence contract

Use a versioned JSON manifest with two layers. The private manifest beside the backup contains per-file relative path, root role, type, byte size, modification time, SHA-256, and SQLite/Chroma opaque fingerprints. The safe-to-commit summary contains root aliases/relative paths, roles, totals, integrity result counts, and aggregate hashes but no documents, messages, raw metadata values, user IDs, collection names, or retrieval text. [VERIFIED: CONTEXT.md allows paths/roles/sizes/hashes/count summaries]

The manifest should include `schema_version`, tool version/Git commit, UTC timestamp, source root resolved hash, backup destination, quiescence evidence, per-check status, and an overall status that is `pass` only when every required check ran and passed. A skipped check is `blocked` or `not_run`, never `pass`. [VERIFIED: D-03 test truthfulness]

### Pattern 2: Immutable-source, disposable-restore

Resolve source, backup, and restore paths before work. Require all three to be disjoint, require backup/restore destinations not to exist, never use `dirs_exist_ok=True`, never call reset/delete/migrate APIs, and open Chroma only from the disposable restore copy. Use `lstat()` and do not follow symlinks during inventory or copy; unexpected links/special files require explicit review. [CITED: https://docs.python.org/3.12/library/pathlib.html] [CITED: https://docs.python.org/3.12/library/shutil.html]

For the real backup, stop Aura and verify no open handles with `lsof` before copy. Chroma's backup guidance says a filesystem backup requires a stopped instance; the current live-copy daemon is not sufficient evidence. [CITED: https://cookbook.chromadb.dev/strategies/backup/] [VERIFIED: `lsof` is available]

### Pattern 3: Baseline parity, not idealized cleanliness

Run full `PRAGMA integrity_check` and `PRAGMA foreign_key_check` independently. `integrity_check` does not check foreign keys; `quick_check` also skips UNIQUE and index-content consistency, so it is suitable only for a fast per-task smoke check, not the phase gate. [CITED: https://sqlite.org/pragma.html]

The phase gate should require: source manifest hash equals backup manifest hash; backup copy equals temporary restore copy; restored SQLite structural result equals `ok`; restored FK violation count/fingerprint equals source baseline; restored Chroma collection and record counts equal baseline; and opaque retrieval result fingerprints equal fixtures. Existing FK anomalies remain open findings and must not be silently normalized. [VERIFIED: current source has eight FK-check rows per likely active DB]

### Pattern 4: Quarantined characterization harness

Do not import `aura_backend.main` at test-module top level. Keep DTO/security/inventory tests against import-light modules. For the few core API/companion characterizations, spawn a child Python process with `cwd=tmp_path`, a sanitized deterministic environment, no production lifespan, fake provider/persistence/filesystem/MCP collaborators, a hard timeout, and JSON-only result capture. The child may import `main`, patch module globals, call the real ASGI route/handler, serialize sanitized responses, then exit. [VERIFIED: main.py's production lifespan would otherwise start protection, Chroma, MCP, provider, archival, and autonomic services]

Do not snapshot timestamps, generated UUIDs, hidden reasoning, or exact model prose. Normalize volatile fields and assert stable schema, status, persistence call shape, uncertainty-facing fields, and error behavior. Deterministic companion tests use fake provider responses; `ornith:latest` belongs only in a separately marked live evaluation when model behavior is the subject. [VERIFIED: D-04 and ConversationResponse shape]

### Pattern 5: Classification before migration

Create a manifest with one entry per legacy script: `path`, `category`, `reason`, `external_dependencies`, `writes`, `production_symbol`, `disposition`, and `replacement_test`. Require classification completeness against `rg --files` so new `test_*.py` files outside `tests/` cannot disappear silently. [VERIFIED: current mixed locations]

Priority migration order:

1. `test_aura_parameter_fix.py`: port schema/JSON-string/direct/wrapped formatting cases to package imports and native assertions; it exercises production parameter handling without needing services. [VERIFIED: source inspection]
2. `test_mcp_bridge_fix.py`: port JSON serialization, fake-client construction, large-result bounds, and heartbeat result assertions; exclude live MCP. [VERIFIED: source inspection]
3. Pure portion of `test_numpy_serialization.py`: parameterize NumPy scalar/array/nested conversion against the actual production helper; exclude SentenceTransformer loading. [VERIFIED: source inspection]
4. Convert current filesystem/CORS/export helper tests into request-level characterization where possible. [VERIFIED: tests/test_runtime_security.py]

Archive/diagnostic dispositions:

| Legacy group | Classification | Required disposition |
|--------------|----------------|----------------------|
| `test_aura_conversation.py`, `test_mcp_client.py`, `test_mcp_integration.py`, `test_mcp_tools.py`, archived `test_mcp_fix.py` | Live service/MCP checks | Optional `live` lane only; explicit server precondition, assertions, timeout, and nonzero failure exit. [VERIFIED: source inspection] |
| `quick_test.py`, `test_vector_db.py`, `test_shared_embedding.py` | Mixed dependency/model/GPU diagnostics | Split environment diagnostics from bounded performance/live-model checks; never default. [VERIFIED: source inspection] |
| `test_memvid_integration.py` and Memvid archived variants | Optional live SDK/storage check | Keep outside deterministic lane; force temp paths and assert outcomes if retained. [VERIFIED: source inspection] |
| `test_interprocess_locking.py` | Destructive/concurrency diagnostic | Do not run until rewritten to accept only temp database paths; current default construction can write relative runtime state. [VERIFIED: source inspection] |
| `test_comprehensive_fixes.py`, `test_ui_improvements.py`, `test_tool_improvements.py` | Source-text/demo diagnostics | Do not migrate source-string or reimplemented-logic checks; replace with behavior tests. [VERIFIED: source inspection] |
| `test_setup.py` | Vacuous diagnostic | Archive classification; it prints component success without constructing or checking components. [VERIFIED: source inspection] |
| recovery/fix/migrate scripts in `archive_unused` | Migration/recovery tools | Never collect; manual-only and out of Phase 1 execution scope. [VERIFIED: filenames and source inspection] |

### Anti-patterns to avoid

- **Opening an original with `PersistentClient` for “inspection”:** client startup may load/migrate persistent state; open only a disposable copy. [CITED: https://docs.trychroma.com/docs/run-chroma/cloud-client?lang=typescript]
- **Hashing only `chroma.sqlite3`:** this omits HNSW/vector sidecars and cannot prove a full Chroma restore. [CITED: https://cookbook.chromadb.dev/core/storage-layout/]
- **Treating `integrity_check=ok` as total integrity:** foreign keys require a separate pragma. [CITED: https://sqlite.org/pragma.html]
- **Using current automatic backup cleanup:** it deletes old backup directories, contradicting this phase's no-deletion boundary. [VERIFIED: aura_backend/database_protection.py]
- **Broadening `testpaths`:** it would collect scripts with unresolved fixtures, import exits, live services, and boolean returns. [VERIFIED: legacy source inspection]
- **Mocking the code under test with reimplemented logic:** tests must invoke production symbols, not duplicate expected algorithms inside the test. [VERIFIED: test_tool_improvements.py and test_comprehensive_fixes.py]
- **CORS-only localhost defense:** strict JSON Content-Type behavior must also be tested because simple browser requests can bypass preflight in the documented local unauthenticated scenario. [CITED: https://fastapi.tiangolo.com/advanced/strict-content-type/]
- **Adding sign-in:** it contradicts the locked single-user local trust model and is not a Phase 1 mitigation. [VERIFIED: CONTEXT.md D-01]

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---------|-------------|-------------|-----|
| File digests | Whole-file reads or custom chunk/hash code | `hashlib.file_digest(..., "sha256")` | Stdlib streams from a binary file object efficiently. [CITED: https://docs.python.org/3.12/library/hashlib.html] |
| SQLite structural checks | Custom page/table validators | `integrity_check`, `foreign_key_check`, and `Connection.backup` where applicable | SQLite owns its consistency and snapshot semantics. [CITED: https://sqlite.org/pragma.html] |
| Temporary restore cleanup | Ad-hoc `/tmp` names and manual recursive deletion | pytest `tmp_path` / `TemporaryDirectory` | Unique, isolated lifecycle with reliable cleanup. [CITED: https://docs.pytest.org/en/9.0.x/reference/reference.html] |
| FastAPI request testing | Socket servers or hand-built request objects | `TestClient`/HTTPX ASGI transport with fake dependencies | Exercises parsing, middleware, validation, and serialization without a network listener. [CITED: https://fastapi.tiangolo.com/tutorial/testing/] |
| Async test runner | `asyncio.run()` inside collected tests | `pytest-asyncio` with explicit registered marks/mode | Preserves runner-owned failures and teardown. [VERIFIED: dependency already installed] |
| Path security | Replacing `../` substrings | allowlist component validation plus resolved-root containment | Denylists miss alternate separators/encodings; CWE recommends known-good validation and canonicalization. [CITED: https://cwe.mitre.org/data/definitions/22] |
| Test category semantics | Filename folklore and printed banners | registered pytest markers plus separate commands/manifests | Unknown markers fail and result classes remain explicit. [CITED: https://docs.pytest.org/en/stable/how-to/mark.html] |

## Common Pitfalls

### Pitfall 1: The backup “passes” while Aura was writing

**What goes wrong:** SQLite and vector-index files can represent different moments. **Warning sign:** open handles or a running protection/backend process during copy. **Avoidance:** stop Aura/Chroma, verify quiescence, then copy the entire persistence directory. [CITED: https://cookbook.chromadb.dev/strategies/backup/]

### Pitfall 2: The verifier mutates the evidence

**What goes wrong:** opening the only backup with a normal persistent client can change it, destroying the original evidence. **Warning sign:** validation path equals source or backup path. **Avoidance:** hash/finalize backup, copy it to a fresh temp directory, and open only that disposable copy. [VERIFIED: preservation design constraint]

### Pitfall 3: Personal content leaks into a committable report

**What goes wrong:** Chroma `peek()`, `get()` defaults, collection names, metadata values, or exception strings can contain sensitive material. **Warning sign:** report keys named `documents`, `messages`, `metadata`, `query`, or raw `ids`. **Avoidance:** request `include=[]` where supported, hash opaque identifiers with a backup-private salt, and enforce a manifest allowlist plus privacy test. [CITED: https://docs.trychroma.com/docs/querying-collections/query-and-get]

### Pitfall 4: A copied database is structurally valid but incomplete

**What goes wrong:** hashes prove copied bytes, not usability; `integrity_check` ignores foreign keys and SQLite checks do not exercise the HNSW index. **Warning sign:** no Chroma count/retrieval step. **Avoidance:** combine hashes, both SQLite pragmas, Chroma collection/record counts, and retrieval fingerprints. [CITED: https://sqlite.org/pragma.html]

### Pitfall 5: Pre-existing anomalies block truthful parity reporting

**What goes wrong:** demanding a pristine `foreign_key_check` would fail the current baseline, while ignoring it hides risk. **Warning sign:** only a boolean overall integrity field. **Avoidance:** record source anomaly count/fingerprint, require exact restored parity, and keep a separate unresolved finding for later storage work. [VERIFIED: eight FK-check rows observed in each likely active DB]

### Pitfall 6: Pytest reports green on boolean-return scripts

**What goes wrong:** returning `False` does not create a pytest assertion failure; scripts may also catch exceptions and print success. **Warning sign:** `return True/False`, `sys.exit`, or “tests completed” banners inside collected functions. **Avoidance:** migrate to native assertions and allow unexpected exceptions to fail the test. [VERIFIED: legacy scripts]

### Pitfall 7: Import-time application setup touches real state

**What goes wrong:** importing `main` pulls in heavy subsystems, loads `.env`, and creates global service objects; entering lifespan starts database protection and other services. **Warning sign:** `from aura_backend.main import app` at test-module scope or `with TestClient(app)` without fakes. **Avoidance:** import-light unit modules plus a temp-cwd child probe that never enters production lifespan. [VERIFIED: aura_backend/main.py]

### Pitfall 8: Helper tests are mistaken for boundary tests

**What goes wrong:** testing `allowed_browser_origins()` alone does not prove middleware responses or strict Content-Type enforcement. **Warning sign:** no OPTIONS/POST request assertions. **Avoidance:** add request-level allowed-origin, rejected-origin, missing Content-Type, `text/plain`, and `application/json` tests. [CITED: https://www.starlette.io/middleware/] [CITED: https://fastapi.tiangolo.com/advanced/strict-content-type/]

## Code Examples

### Metadata and SHA-256 without reporting content

```python
# Source: Python 3.12 pathlib/hashlib official documentation
from hashlib import file_digest
from pathlib import Path


def regular_file_evidence(path: Path) -> dict[str, object]:
    stat = path.lstat()  # Do not follow links during inventory.
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Unsupported inventory entry type: {path}")
    with path.open("rb") as stream:
        digest = file_digest(stream, "sha256").hexdigest()
    return {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest}
```

This reads bytes only to compute a digest and returns no content. Report paths should be relative to an explicitly mapped root; exception messages included in committable summaries should be sanitized. [CITED: https://docs.python.org/3.12/library/hashlib.html]

### Read-only SQLite checks

```python
# Source: Python sqlite3 and SQLite PRAGMA official documentation
import sqlite3
from pathlib import Path


def sqlite_checks(database: Path) -> tuple[list[str], int]:
    uri = f"{database.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
        foreign_key_violation_count = sum(
            1 for _ in connection.execute("PRAGMA foreign_key_check")
        )
    return integrity, foreign_key_violation_count
```

Do not emit full foreign-key rows in the committable report; count and privately fingerprint them. [CITED: https://docs.python.org/3.12/library/sqlite3.html] [CITED: https://sqlite.org/pragma.html]

### Canonical deterministic test configuration

```toml
# Source: pytest official configuration/marker documentation
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--strict-config", "--strict-markers"]
asyncio_mode = "strict"
markers = [
  "live: requires a separately started external service",
  "ollama: evaluates a local Ollama model and is never deterministic",
  "gpu: requires GPU hardware/runtime",
]
```

```bash
uv run python -m pytest -q
```

The root command needs no negative marker expression if all live/model/GPU files remain outside `tests/`; if any are retained inside, add `-m "not live and not ollama and not gpu"` to the deterministic command. [CITED: https://docs.pytest.org/en/stable/how-to/mark.html]

### Request-level CORS and strict JSON characterization

```python
# Source: FastAPI and Starlette official testing/middleware documentation
def test_untrusted_origin_cannot_drive_local_json_endpoint(client):
    preflight = client.options(
        "/conversation",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers

    response = client.post("/conversation", content=b'{}', headers={"Origin": "https://untrusted.example"})
    assert response.status_code in {415, 422}
```

Pin the exact observed status/body in the characterization fixture after running it against the current FastAPI version; do not guess the final golden response. [CITED: https://fastapi.tiangolo.com/advanced/strict-content-type/]

## State of the Art

| Old/current fragile approach | Recommended current approach | Impact |
|-----------------------------|------------------------------|--------|
| Live `copytree` of Chroma | Stop instance, copy whole persistence directory, hash, then restore-test a second copy | Aligns with Chroma backup guidance and preserves sidecar indexes. [CITED: https://cookbook.chromadb.dev/strategies/backup/] |
| `quick_check` or `integrity_check` alone | Full integrity check plus separate FK check and Chroma API verification | Avoids false completeness. [CITED: https://sqlite.org/pragma.html] |
| Bare `pytest` in an uninstalled flat layout | `python -m pytest` or an explicit installed-package configuration | Produces a reproducible import path. [CITED: https://docs.pytest.org/en/stable/explanation/pythonpath.html] |
| CORS wildcard/local-network trust | Explicit origins, credentials off, strict JSON Content-Type, loopback default | Matches unauthenticated localhost threat model. [CITED: https://fastapi.tiangolo.com/advanced/strict-content-type/] |
| Test-like scripts returning booleans | Assertion-based tests plus separate live/diagnostic/migration lanes | Makes exit status meaningful. [VERIFIED: D-03] |

**Deprecated/outdated for this phase:** treating the existing automatic backup service as proof of recoverability; running `aura_backend/tests` under pytest; source-text checks as behavior tests; and any `ornith:latest` invocation in the deterministic suite. [VERIFIED: current repository evidence and locked decisions]

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | A quiesced full-directory copy is sufficient for Aura's embedded Chroma 1.5.9 layout when the restored copy passes API-level counts and retrieval checks. [ASSUMED] | Recommended Architecture | Chroma may require additional version-specific snapshot steps; the real restore drill is the gate that tests this assumption. |
| A2 | The `/backup` mount is operationally acceptable as the “offline backup outside Git” destination. [ASSUMED] | Standard Stack | If Ty requires removable/offsite media, the plan needs a different target; do not silently substitute the repository filesystem. |
| A3 | Opaque hashed retrieval identifiers are sufficient evidence without exposing raw IDs or content. [ASSUMED] | Manifest pattern | If identifiers are low entropy, plain SHA-256 could be guessable; use a private random salt/HMAC key beside the backup. |
| A4 | The preservation CLI/module does not yet exist; Plan 01-02 resolves its executable contract into separate `inventory`, `preflight`, `backup-from-ticket`, `verify`, and non-mutating validator commands. [RESOLVED] | Validation Architecture | Executors must use the plan's exact argument, output-schema, exit-code, and ticket-binding contract rather than inventing an equivalent command. |
| A5 | Repository-pattern guidance remains useful for 30 days if no relevant code changes land. [ASSUMED] | Metadata | Fast-moving dependencies or concurrent Phase 1 edits may require earlier revalidation. |

## Open Questions (RESOLVED)

1. **Authoritative Chroma root — resolved for Phase 1:** preserve and restore-test both `aura_chroma_db` and `aura_backend/aura_chroma_db` as independent active candidates. Phase 1 must not choose, merge, rename, or migrate either root. Canonical storage ownership is a Phase 3 decision informed by runtime tracing and the preservation evidence. [VERIFIED: D-02/D-05 and phase boundary]

2. **Eight foreign-key-check rows — resolved for Phase 1:** treat the rows as a known unresolved baseline anomaly, not as proof of either corruption or valid Chroma internals. Record only their count and a salted private fingerprint, require exact source/backup/restore parity, and defer Chroma-specific interpretation or repair semantics to Phase 3. A passing Phase 1 restore licenses preservation only; it does not certify zero relational anomalies. [VERIFIED: read-only inspection] [CITED: https://sqlite.org/pragma.html]

3. **Privacy-safe retrieval fixture — resolved:** create fixtures only after copying each durable backup into a disposable restore directory. For each non-empty collection, choose a deterministically ordered internal record on that disposable copy, reuse its stored embedding as the query vector, request IDs/distances only with documents and metadata excluded, and compare the ordered top-result count plus HMAC-SHA-256 fingerprints of `(collection ordinal, result ordinal, opaque ID, normalized distance)` using a random key stored only in the private backup evidence. Public output contains only fixture count, pass/fail status, and an aggregate fingerprint; it contains no raw collection name, record ID, embedding, distance list, document, query text, or metadata. Empty collections are explicit `not_applicable`; unavailable embeddings or an unexecuted query are `blocked`, never pass. [CITED: https://docs.trychroma.com/docs/querying-collections/query-and-get] [VERIFIED: D-02/D-03]

4. **SQLite-suffix files in archives that are not databases — resolved:** retain, hash, and count the file. When and only when SQLite returns `SQLITE_NOTADB` under an explicitly declared archive root, record integrity and foreign-key checks as `not_applicable` with the fixed non-content reason `preserved_non_sqlite_archive`, include it in the anomaly count, and allow the root to pass because preservation succeeded without claiming database integrity. The same condition in active, backup, or test roots remains a failure. Disposable restore must reproduce the same role-bound facts; `not_applicable` cannot substitute for an active check or an unrun check. [VERIFIED: D-02/D-03 and Plan 01-08 execution decision]

## Environment Availability

| Dependency | Required By | Available | Version/capacity | Fallback |
|------------|-------------|-----------|------------------|----------|
| Python | Preservation/test code | ✓ | 3.12.9 | None needed. [VERIFIED: local command] |
| uv | Canonical root execution | ✓ | 0.11.21 | None needed. [VERIFIED: local command] |
| Python SQLite | Automated DB checks | ✓ | 3.47.1 | None needed. [VERIFIED: local import] |
| sqlite3 CLI | Manual secondary inspection | ✓ | 3.51.2 | Prefer Python API to avoid runtime-version drift. [VERIFIED: local command] |
| Git | Tracked-artifact/ignore checks | ✓ | 2.55.0 | None needed. [VERIFIED: local command] |
| lsof | Quiescence preflight | ✓ | system command present | If unavailable later, require verified process shutdown plus exclusive-open probe. [VERIFIED: `command -v lsof`] |
| `/backup` filesystem | Real outside-Git backup | ✓ | writable, ~253 GB available, separate `/dev/sda2` mount | `/data` is also writable with ~327 GB, but do not switch silently. [VERIFIED: findmnt/df/test -w] |
| Ollama/Ornith | Not required by Phase 1 deterministic work | Not probed for execution | `ollama` executable exists; planning state says Ornith is installed | No model call; optional live evaluation is out of scope. [VERIFIED: command presence and CONTEXT.md] |

**Missing dependencies with no fallback:** none. [VERIFIED: environment audit]

**Capacity warning:** `/home` is about 94% used with about 61 GB free, while the identified preservation roots total about 1 GB. Use the separate `/backup` mount for the real backup and temp directories with explicit free-space checks. [VERIFIED: df and du]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 with pytest-asyncio 1.3.0. [VERIFIED: local imports] |
| Config file | `pyproject.toml`. [VERIFIED: codebase] |
| Quick run command | `uv run python -m pytest -q`. [VERIFIED: 13 passed] |
| Collection gate | `uv run python -m pytest --collect-only -q`. [VERIFIED: 13 collected] |
| Full Phase 1 deterministic suite | `uv run python -m pytest -q`. Live/model/diagnostic checks are separate. [VERIFIED: D-03/D-04] |
| Real preservation drill | The exact Plan 01-08 `inventory` command, Plan 01-09 `preflight` plus manual approval, and Plan 01-10 `backup-from-ticket` then disposable `verify` commands under the normative Plan 01-02 contract. [RESOLVED] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test type | Automated command | File exists? |
|--------|----------|-----------|-------------------|--------------|
| PRES-01 | Inventory includes every declared root/file metadata and never report content | unit + real evidence | `uv run python -m pytest -q tests/preservation/test_inventory.py` | ❌ Wave 0 |
| PRES-02 | Backup/restore paths are disjoint; copy hashes, SQLite checks, Chroma counts and retrieval fingerprints match | unit/integration + manual real drill | `uv run python -m pytest -q tests/preservation/test_backup_restore.py` | ❌ Wave 0 |
| PRES-03 | API schemas/statuses, fake-provider companion response, and persistence call shape remain stable | characterization | `uv run python -m pytest -q tests/characterization` | ❌ Wave 0 |
| PRES-04 | Generated path patterns are ignored and no new runtime artifacts become tracked | unit/git smoke | `uv run python -m pytest -q tests/test_repository_hygiene.py` | ❌ Wave 0 |
| TEST-01 | Root collection/run has one clear exit status | meta smoke | `uv run python -m pytest --collect-only -q && uv run python -m pytest -q` | Partial: config + 13 tests exist. [VERIFIED: current run] |
| TEST-02 | Every legacy test-like script has exactly one classification; migrated tests assert | unit/manifest | `uv run python -m pytest -q tests/test_legacy_classification.py` | ❌ Wave 0 |
| LOCAL-01 | Loopback default, explicit LAN override | unit | `uv run python -m pytest -q tests/test_runtime_security.py` | ✅ helper coverage |
| LOCAL-02 | Explicit origins; wildcard/disallowed origin denied; JSON Content-Type required | unit + ASGI integration | `uv run python -m pytest -q tests/test_runtime_security.py tests/characterization/test_api_contract.py` | ⚠️ helper only |
| LOCAL-03 | Existing safe IDs preserved; traversal/special formats rejected; resolved path contained | unit | `uv run python -m pytest -q tests/test_runtime_security.py` | ⚠️ component/format coverage; add final containment |
| LOCAL-04 | Primary local flow does not require sign-in | ASGI characterization | `uv run python -m pytest -q tests/characterization/test_api_contract.py` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run python -m pytest -q` plus the task's focused file. [VERIFIED: suite currently 0.02 seconds]
- **Per preservation code task:** add synthetic temp-root backup/restore tests; never run the real backup implicitly. [VERIFIED: D-02]
- **Per wave merge:** collection gate, full deterministic suite, `git status --short`, and safe inventory-summary schema validation. [VERIFIED: PRES-04/TEST-01]
- **Phase gate:** deterministic suite green **and** one explicitly executed real `/backup` restore drill with no required check skipped. [VERIFIED: PRES-02/D-03]

### Wave 0 Gaps

- [ ] `tests/conftest.py` — temp root factories, no-op lifespan, fake provider/persistence/filesystem collaborators.
- [ ] `tests/preservation/test_inventory.py` — metadata-only/redaction/symlink/special-file coverage.
- [ ] `tests/preservation/test_backup_restore.py` — synthetic SQLite + Chroma fixture, disjoint paths, hash/count parity, source unchanged.
- [ ] `tests/preservation/test_manifest_privacy.py` — reject document/message/raw metadata/raw ID fields from committable evidence.
- [ ] `tests/characterization/test_api_contract.py` — CORS, strict Content-Type, validation, health/root/error contracts without production lifespan.
- [ ] `tests/characterization/test_persistence_contract.py` — fake persistence call and failure behavior.
- [ ] `tests/characterization/test_companion_contract.py` — fake-provider stable schema/useful visible response; no model.
- [ ] `tests/test_repository_hygiene.py` — expected ignore patterns and no newly tracked runtime artifacts.
- [ ] `tests/test_legacy_classification.py` — manifest completeness and category schema.
- [ ] Register `live`, `ollama`, and `gpu` markers and explicit async mode in `pyproject.toml`.

No new framework install is needed. [VERIFIED: current dependencies]

## Security Domain

Security enforcement is enabled because `.planning/config.json` does not explicitly set `security_enforcement: false`. ASVS 5.0.0 renamed/reorganized chapters, so this phase should cite actual v5 categories rather than mechanically copy older V2-authentication/V5-validation labels. [CITED: https://owasp.org/www-project-application-security-verification-standard/]

### Applicable ASVS 5.0.0 categories

| ASVS category/control | Applies | Standard control |
|-----------------------|---------|------------------|
| V2.2 Input Validation | yes | Positive validation of identifiers/formats at the trusted backend boundary. [CITED: https://github.com/OWASP/ASVS/blob/master/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json] |
| V3.5 Browser Origin Separation | yes | Explicit CORS origins plus strict JSON Content-Type so sensitive POSTs require preflight. [CITED: same ASVS 5.0.0 JSON] |
| V4 API and Web Service | yes | Request/response Content-Type and schema validation through FastAPI/Pydantic. [CITED: same ASVS 5.0.0 JSON] |
| V5.3 File Storage | yes | Trusted/internal path construction, strict identifier validation, resolved-root containment. [CITED: same ASVS 5.0.0 JSON] |
| Authentication/session controls | no for Phase 1 normal local flow | Locked decision forbids adding sign-in; network/origin/input boundaries are the chosen local controls. [VERIFIED: CONTEXT.md D-01] |
| Stored cryptography | limited | SHA-256 is evidence integrity, not encryption or authentication; do not claim confidentiality from hashes. [CITED: https://docs.python.org/3.12/library/hashlib.html] |

### Known Threat Patterns

| Pattern | STRIDE | Standard mitigation |
|---------|--------|---------------------|
| Path traversal through `user_id`, session ID, or format | Tampering / information disclosure | Allowlist + canonical resolved containment + fixed extension/root. [CITED: https://cwe.mitre.org/data/definitions/22] |
| Malicious website driving localhost API | Spoofing / tampering | Loopback bind, explicit origin preflight, strict JSON Content-Type, credentials off. [CITED: https://fastapi.tiangolo.com/advanced/strict-content-type/] |
| Backup written while DB/index changes | Tampering / denial of service | Stop/quiesce service, copy full persistence unit, hash and restore-test. [CITED: https://cookbook.chromadb.dev/strategies/backup/] |
| Evidence report leaks personal content | Information disclosure | Output-schema allowlist, no raw Chroma docs/metadata/IDs, privacy regression test. [VERIFIED: PRES-01/D-02] |
| Restore verifier overwrites original | Tampering / denial of service | Disjoint resolved paths, non-existing destinations, open only temp copy, no destructive APIs. [VERIFIED: preservation design] |
| False-green legacy script | Repudiation | Native assertions, strict collection/markers, separate result classes, no swallowed exceptions. [VERIFIED: D-03 and legacy evidence] |

## Project Constraints (from supplied AGENTS instructions)

- Explain plans/results in concise, practical language suitable for a non-coder; report failures plainly. [VERIFIED: supplied AGENTS instructions]
- Research current official information before code/package decisions and avoid reinventing maintained solutions. [VERIFIED: supplied AGENTS instructions]
- Prefer `uv` for Python work, type hints/docstrings/comments, and self-contained project code. [VERIFIED: supplied AGENTS instructions]
- Do not install large packages or require sudo without Ty's action; this phase needs no installation. [VERIFIED: supplied AGENTS instructions and environment audit]
- Do not couple code to other projects by filesystem path. `/backup` is data output, not a code dependency. [VERIFIED: supplied AGENTS instructions]

No project-defined `.claude/skills/` or `.agents/skills/` directory was present. [VERIFIED: filesystem inspection]

## Sources

### Primary repository/runtime evidence (HIGH confidence)

- `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, and phase `CONTEXT.md` — goals, locked decisions, scope, and requirements. [VERIFIED: codebase]
- `.planning/codebase/CONCERNS.md`, `TESTING.md`, `ARCHITECTURE.md` — upstream risk/test/architecture map, cross-checked against current files. [VERIFIED: codebase]
- `aura_backend/database_protection.py`, `main.py`, `runtime_security.py`, `shared_embedding_service.py`, `pyproject.toml`, `.gitignore`, and legacy scripts — current implementation evidence. [VERIFIED: codebase]
- Local read-only filesystem, Git, SQLite, package-version, pytest, mount, and capacity commands run 2026-08-19. [VERIFIED: local commands]

### Official documentation reached through WebSearch (MEDIUM confidence per confidence seam)

- https://docs.python.org/3.12/library/hashlib.html — `file_digest`.
- https://docs.python.org/3.12/library/pathlib.html — `stat`, `lstat`, resolution/relative paths.
- https://docs.python.org/3.12/library/sqlite3.html — backup and read-only URI connections.
- https://sqlite.org/pragma.html — integrity, quick, and foreign-key checks.
- https://sqlite.org/backup.html — online backup semantics.
- https://docs.trychroma.com/reference/python/client — persistent/list/count APIs.
- https://docs.trychroma.com/docs/querying-collections/query-and-get — query/get inclusion behavior.
- https://cookbook.chromadb.dev/core/storage-layout/ — Chroma persisted SQLite/WAL/index layout.
- https://cookbook.chromadb.dev/strategies/backup/ — quiesced filesystem backup guidance.
- https://docs.pytest.org/en/stable/explanation/goodpractices.html — discovery/layout/module invocation.
- https://docs.pytest.org/en/stable/how-to/usage.html — `python -m pytest` behavior.
- https://docs.pytest.org/en/9.0.x/reference/reference.html — strict markers and `tmp_path`.
- https://fastapi.tiangolo.com/tutorial/testing/ — TestClient/HTTPX assertions.
- https://fastapi.tiangolo.com/advanced/testing-events/ — lifespan in TestClient context.
- https://fastapi.tiangolo.com/advanced/testing-dependencies/ — dependency overrides.
- https://fastapi.tiangolo.com/advanced/strict-content-type/ — localhost CSRF and JSON Content-Type.
- https://www.starlette.io/middleware/ — explicit CORS controls.
- https://www.uvicorn.org/settings/ — loopback default and LAN bind.
- https://cwe.mitre.org/data/definitions/22 and https://owasp.org/www-community/attacks/Path_Traversal — path traversal controls.
- https://owasp.org/www-project-application-security-verification-standard/ and ASVS 5.0.0 JSON — current security categories/controls.

### Tertiary (LOW confidence)

- None used as authoritative implementation guidance. [VERIFIED: research log]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH for installed versions and availability; MEDIUM for current external documentation due provider classification. [VERIFIED: local environment] [CITED: official docs above]
- Architecture: HIGH for repository/current-state findings; MEDIUM for the proposed Chroma backup pattern until the real restore drill proves it on Aura's data. [VERIFIED: codebase] [ASSUMED]
- Pitfalls: HIGH where reproduced/current-source based; MEDIUM where based on official framework/database documentation. [VERIFIED: local commands] [CITED: official docs above]

**Research date:** 2026-08-19
**Valid until:** 2026-09-18 for repository patterns; re-check installed versions and FastAPI/Chroma docs before dependency changes. [ASSUMED]
