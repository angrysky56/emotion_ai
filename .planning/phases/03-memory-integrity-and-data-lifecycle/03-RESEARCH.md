# Phase 3: Memory Integrity and Data Lifecycle - Research

**Researched:** 2026-08-31  
**Domain:** SQLite event ledger, rebuildable vector projection, neutral hybrid retrieval, and local data lifecycle  
**Confidence:** HIGH for repository findings and SQLite design; MEDIUM-HIGH for the Chroma projection contract because official documentation was available but Context7 was unavailable

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Durable truth
- SQLite is the sole source of truth for immutable conversation events and typed
  derived memories.
- Conversation turns are committed atomically; retries are idempotent and cannot
  create half-turns or duplicate events.
- Corrections append new evidence and explicitly supersede derived claims. Source
  events are never rewritten to make a newer interpretation appear original.
- Every derived fact, preference, episode, goal, and relationship claim cites its
  source events and carries uncertainty/status.

### Retrieval
- SQLite full-text and the existing Chroma store supply affect-neutral candidates.
- Chroma and any future graph are disposable projections rebuildable from SQLite.
- Relevance, user isolation, provenance, freshness/supersession, and bounded
  pagination are hard gates before any future affective salience adjustment.
- Retrieval emits a deterministic trace explaining selected and rejected items.
- Retrieved text is untrusted historical data, never system authority or new
  evidence merely because it was recalled.

### Lifecycle and safety
- Existing databases, Chroma roots, Memvid archives, and backups remain immutable
  until inventory and restore parity prove a migration or deletion safe.
- Memvid v2 is optional copy-only cold archival. Archive creation never deletes
  active data.
- Backup uses a SQLite-consistent mechanism and restore is proven in an isolated
  location with counts, hashes, foreign-key checks, and retrieval fixtures.
- Export returns real stored data; unsupported formats fail clearly.
- Deletion enumerates active stores, projections, exports, caches, archives, and
  backup policy. No destructive operation is inferred from vague requests.
- Normal local use requires no account or sign-in and stays loopback-only.

### Evaluation
- Build a sanitized, versioned corpus before optimizing retrieval.
- Measure direct and paraphrased recall, corrections, temporal questions,
  distractors, abstention, duplicates, provenance, latency, and cross-user leaks.
- Preserve a neutral retrieval arm and a constant-salience seam for Phase 4.
- Apply the pre-registered kill criteria; do not add graph/RLM/Memvid core
  dependencies without an Aura-specific measured win.

### Codex's Discretion
- Exact SQLite schema, repository/module names, migration staging, FTS tokenizer,
  deterministic score normalization, and plan decomposition, provided all locked
  contracts above are observable and tested.

### Deferred Ideas (OUT OF SCOPE)
- Dynamic affective state, neurochemical/brainwave controls, relationship update,
  and post-response feedback belong to Phase 4.
- Graph-RLM reading, temporal graph projection, and Memvid performance adoption
  remain experimental candidates after the neutral baseline is valid.
- Frontend memory-management redesign belongs to Phase 5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research support |
|---|---|---|
| PRES-04 | Keep generated databases, backups, exports, profiles, logs, and secrets out of new Git commits. | Use a single configured runtime root, existing containment helpers, mode-restricted files, and Git-hygiene tests. |
| TEST-03 | Backend API contracts, filesystem containment, persistence, provider translation, and failure behavior require automated tests. | The validation map specifies atomicity, failure injection, containment, lifecycle, compatibility, and provider-path tests. |
| DATA-01 | One documented storage owner controls persistence, indexing, backup, restore, export, retention, and deletion. | A single SQLite repository/lifecycle boundary owns durable state; Chroma is an adapter-owned projection. |
| DATA-02 | Backups use a consistent snapshot/export mechanism and are restore-tested with counts and retrieval fixtures. | Use `sqlite3.Connection.backup()` and isolated verification with hashes, integrity, foreign keys, counts, FTS rebuild, and fixtures. |
| DATA-03 | Export returns actual stored data in every advertised format; unsupported formats are rejected clearly. | Ship versioned JSON first; query the ledger under a consistent read transaction and reject any other format. |
| DATA-04 | Deletion enumerates and verifies all affected active stores, exports, caches, archives, and backups. | Use plan/confirm/execute/verify semantics with explicit residual-copy reporting and no inferred destructive scope. |
| DATA-05 | Retrieval has bounded pagination and measured relevance, latency, and duplicate behavior. | Fixed candidate caps, maximum page sizes, stable keyset/run cursors, and a pre-registered sanitized benchmark satisfy this. |
| DATA-06 | Immutable source events are distinct from lossy derived memories; derived memory retains provenance and supersession state. | Separate append-only event, derived-memory, source-edge, and supersession tables provide observable contracts. |
| DATA-09 | Affect-neutral retrieval creates the eligible set and enforces relevance, provenance, supersession, isolation, neutral anchors, and traceability. | Hard eligibility gates precede normalized reciprocal-rank fusion; the Phase 4 salience seam is fixed at zero. |
</phase_requirements>

## Summary

Aura's current persistence path is neither atomic nor idempotent: one conversation turn is written as two independent Chroma records with random IDs, so a mid-write failure can leave a half-turn and a retry can duplicate both records. Chroma is also serving as durable truth while its default squared-L2 distance is converted to `1 - distance`, filters can overwrite the user scope, history is unbounded in API terms, export emits empty arrays, deletion touches only one collection, and the live backup service copies an active Chroma directory with `shutil.copytree`. These are confirmed implementation defects, not hypothetical risks. [VERIFIED: codebase inspection of `aura_backend/main.py`, `robust_vector_db.py`, `conversation_persistence_service.py`, `database_protection.py`, and `aura_internal_tools.py`]

The safe replacement is a new, explicitly located SQLite database behind one storage repository. A successful turn inserts the request identity, user event, Aura event, typed derivations, provenance edges, and any ledger-side audit records in one `BEGIN IMMEDIATE` transaction. Chroma is updated after commit with stable origin IDs and can always be discarded and rebuilt. Existing roots are imported only from disposable restored copies, never mutated or silently merged. SQLite's online backup API supplies the consistent snapshot; isolated restore proof gates any read switch, retention change, or deletion. [CITED: https://docs.python.org/3.13/library/sqlite3.html] [CITED: https://www.sqlite.org/backup.html]

Neutral retrieval should use bounded FTS5 and cosine-vector candidate lists, apply hard isolation/provenance/supersession/integrity gates, then combine ranks with normalized reciprocal-rank fusion. Raw BM25 and vector distances remain trace fields, not directly added numbers with incompatible scales. A versioned synthetic corpus and the already accepted kill criteria decide whether the baseline is competent and whether any later graph, RLM, or Memvid adoption is justified. [CITED: https://www.sqlite.org/fts5.html] [CITED: https://docs.trychroma.com/docs/collections/configure]

**Primary recommendation:** Build SQLite truth, projection reconciliation, lifecycle proof, and the neutral benchmark as one vertical storage boundary; switch reads only after shadow parity and restore/retrieval gates pass.

## Project Constraints (from AGENTS.md)

- Keep reports concise, factual, practical, and accessible to a non-coder; state failures plainly.
- Research current official information instead of relying on stale package or API knowledge.
- Do not reinvent mature facilities. Prefer TypeScript, then Python managed with `uv`; this phase is an existing Python subsystem, so retain Python and `uv`.
- New Python code needs docstrings, type hints, useful comments, and the existing virtual environment.
- Keep the project self-contained; never wire another repository into runtime paths.
- Deliver coherent, tested behavior rather than diagnostics that merely print booleans.
- Avoid large or privileged installs without Ty's involvement. This design adds no dependency and requires no `sudo`.
- Preserve privacy, fairness, empathy, and non-harm: recalled or model-generated text cannot silently become authoritative evidence.
- Target environment is Pop!_OS with 64 GB RAM and an RTX 3060 12 GB; CPU-only correctness must remain the baseline.

## Architectural Responsibility Map

| Capability | Primary tier | Secondary tier | Rationale |
|---|---|---|---|
| Immutable events, typed derivations, provenance, supersession | Database / Storage | API / Backend | SQLite enforces identity and relationships; the repository enforces domain transitions. |
| Atomic turn persistence and retry identity | API / Backend | Database / Storage | The service supplies an idempotency key; one database transaction makes the turn indivisible. |
| Lexical retrieval | Database / Storage | API / Backend | FTS5 is a database projection; the retrieval service applies domain gates and ranking. |
| Vector retrieval | Database / Storage | API / Backend | Chroma is a rebuildable storage projection controlled by a backend adapter. |
| Pagination and deterministic traces | API / Backend | Database / Storage | The service defines stable cursors and trace semantics; trace rows are stored for audit. |
| Snapshot, restore, export, retention, deletion | Database / Storage | API / Backend | One lifecycle service operates on all state and exposes explicit, validated operations. |
| Sanitized benchmark and kill gates | API / Backend | Database / Storage | The harness drives public storage/retrieval contracts against fixed fixtures. |
| User-facing memory management | Frontend | API / Backend | Deferred to Phase 5; Phase 3 exposes only stable contracts. |

## Current Architecture and File Map

| File / root | Current role | Phase 3 disposition | Provenance |
|---|---|---|---|
| `aura_backend/main.py` | Starts `RobustAuraVectorDB`, `AuraFileSystem`, and `ConversationPersistenceService`; retrieves three Chroma memories into the prompt; persists after the provider response. | Keep route compatibility; route through the new storage service. | [VERIFIED: codebase] |
| `aura_backend/conversation_persistence_service.py` | Writes user and Aura records sequentially, performs analyses, and reports degraded persistence. | Replace internals with one idempotent turn command; retain observable degraded-response behavior. | [VERIFIED: codebase] |
| `aura_backend/robust_vector_db.py` | Owns four Chroma collections, random record IDs, embeddings, retrieval, profile data, repair, and direct backup operations. | Narrow to a projection adapter and legacy reader; remove durable ownership. | [VERIFIED: codebase] |
| `aura_backend/shared_embedding_service.py` | Singleton SentenceTransformer service using `all-MiniLM-L6-v2`. | Retain model for compatibility; record model/config in projection generation and benchmark manifests. | [VERIFIED: codebase] |
| `aura_backend/database_protection.py` | Periodically `copytree`s the live Chroma root, mutates Chroma's internal SQLite, and prunes backups after ten. | Retire after the SQLite snapshot path is proven; never mutate old roots in migration. | [VERIFIED: codebase] |
| `aura_backend/aura_internal_tools.py` | Exposes high-limit history/search, single-collection deletion, and a JSON export wrapper. | Route through bounded retrieval/history and complete lifecycle contracts. | [VERIFIED: codebase] |
| `aura_backend/runtime_security.py` | Supplies path containment, no-follow, strict JSON/origin and loopback controls. | Reuse for database, snapshot, export, and restore paths. | [VERIFIED: codebase and Phase 2 verification] |
| `aura_backend/preservation/{inventory,backup,restore,manifest,cli}.py` | Proven preservation inventory and exact restore-evidence patterns. | Reuse the evidence discipline and manifest style; do not reuse raw-directory copy as the new live backup primitive. | [VERIFIED: Phase 1 verification] |
| `aura_backend/aura_real_memvid.py`, `memvid_archival_service.py` | Optional Memvid v2 copy-only archival adapter. | Keep optional; inventory archives and never place it on the primary read/write path. | [VERIFIED: codebase] |
| `aura_chroma_db/`, `aura_backend/aura_chroma_db/` | Both are preserved active Chroma roots caused by cwd-relative defaults. | Preserve both, fingerprint them, and import only from restored copies. Do not choose a winner by size or mtime. | [VERIFIED: Phase 1 inventory] |
| `aura_data/`, `aura_backend/aura_data/`, Memvid and backup roots | Profiles, sessions, exports, archives, and historical copies. | Include every root in lifecycle plans and residual-copy reports. | [VERIFIED: Phase 1 inventory and codebase] |

### Confirmed Defects and Planning Consequences

| # | Confirmed defect | Consequence / required test | Provenance |
|---|---|---|---|
| D1 | User and Aura messages are separate Chroma `add` calls with a sleep between them. | Failure injection must prove zero half-turns after every SQL step. | [VERIFIED: `ConversationPersistenceService._store_conversation_pair*`] |
| D2 | IDs combine timestamps with fresh UUIDs and there is no idempotency key. The route can schedule a retry after returning the response. | Same key and request hash must return the existing turn; same key with a different hash must conflict. | [VERIFIED: codebase] |
| D3 | Chroma currently owns conversations, emotional patterns, cognitive patterns, and knowledge substrate. | DATA-01 requires a single SQLite owner and projection reconciliation. | [VERIFIED: `RobustAuraVectorDB`] |
| D4 | Collections do not declare a distance metric. Chroma's documented HNSW default is squared L2, but code reports `1 - distance` as similarity; embeddings are not normalized. | Rebuild projection with explicit cosine; clamp cosine similarity only for thresholding and preserve raw distance. | [VERIFIED: codebase] [CITED: https://docs.trychroma.com/docs/collections/configure] |
| D5 | `base_filter.update(where_filter)` lets caller filters overwrite scope metadata. | Scope must be an unavoidable repository argument and a hard conjunct; add adversarial two-scope tests. | [VERIFIED: codebase] |
| D6 | Search/history defaults reach 5,000 rows, have no maximum page size, cursor, or `has_more`, and grouping happens after a row limit. | Add fixed candidate caps and stable keyset/run cursors; benchmark latency and duplicates. | [VERIFIED: API models and internal tools] |
| D7 | `get_fresh_chat_history` passes `ids` in Chroma's `include`; official results always include IDs and do not list `ids` as an include option. | Replace the path; characterize compatibility rather than preserving an invalid call. | [VERIFIED: codebase] [CITED: https://docs.trychroma.com/docs/querying-collections/query-and-get] |
| D8 | Export creates a real JSON file whose conversation/profile arrays are empty. | JSON export must contain ledger rows and counts; other formats fail explicitly. | [VERIFIED: `AuraFileSystem.export_conversation_history`] |
| D9 | Deletion removes conversation collection IDs and a volatile provider session only. It does not enumerate profiles, derived collections, exports, caches, archives, or backups. | Use explicit plan/confirm/verify semantics and report residual historical copies. | [VERIFIED: API deletion routes and internal tools] |
| D10 | Live backup is a recursive copy of an active Chroma directory and old copies are auto-pruned after ten without restore parity. | Use SQLite online backup; no retention deletion until an isolated restore proof passes. | [VERIFIED: `DatabaseProtectionService`] |
| D11 | `RobustAuraVectorDB` is a singleton whose initialized instance ignores a later `persist_directory`. | New adapters must be ordinary injected objects; test both root selections and test isolation. | [VERIFIED: codebase] |
| D12 | Current recovery executes PRAGMAs, checkpoints, and `REINDEX` directly against Chroma's internal database. | Never treat third-party internals as the owned ledger or migration surface. | [VERIFIED: codebase] |
| D13 | Phase 1 inventoried fourteen declared roots, 662 files, about 992.5 MB, and 77 SQLite files; both active roots share eight Chroma foreign-key violations. The current tree also contains `aura_backend/memvid_videos` with twelve `.mv2` files, outside the old declared-root table. | Refresh inventory before migration; preserve anomalies as evidence and never repair old roots in place. | [VERIFIED: Phase 1 manifest/verification and filesystem metadata inspection] |
| D14 | The legacy vector diagnostic under `aura_backend/tests` is outside configured pytest paths and returns/prints booleans. | Add deterministic pytest coverage under `tests/storage`; do not count the diagnostic as verification. | [VERIFIED: `pyproject.toml` and test tree] |

The existing untrusted-memory prompt delimiters and copy-only Memvid behavior are positive compatibility contracts, not defects. Preserve both. [VERIFIED: `tests/memory/test_prompt_memory_boundary.py` and `test_memvid_archival_safety.py`]

## Standard Stack

No external package should be added in this phase. The package-legitimacy gate is therefore not applicable; the planner must not create an install task. [VERIFIED: existing lock and recommended design]

### Core

| Library | Resolved version | Purpose | Why standard |
|---|---:|---|---|
| Python `sqlite3` | Python 3.12.9 / SQLite 3.47.1 in `.venv` | Durable ledger, transactions, FTS5, online backup | Standard library; this environment reports FTS5 enabled and serialized thread support. [VERIFIED: local runtime probe] |
| SQLite FTS5 | SQLite 3.47.1 | Neutral lexical candidates | Built into the locked runtime; supports BM25, external-content indexes, triggers, and rebuild. [CITED: https://www.sqlite.org/fts5.html] |
| `chromadb` | 1.5.9 | Rebuildable local vector projection | Already locked and used; official PersistentClient is a local-disk client. [VERIFIED: `uv.lock` and PyPI JSON] [CITED: https://docs.trychroma.com/reference/python/client] |
| `sentence-transformers` | 4.1.0 | Existing `all-MiniLM-L6-v2` embeddings | Already locked and cached; avoids a migration-time model change. [VERIFIED: `uv.lock`, code, local model cache] |
| `pytest` | 9.0.3 | Unit, integration, corruption, and benchmark-contract tests | Existing root test runner with deterministic conventions. [VERIFIED: `uv.lock` and `pyproject.toml`] |

### Supporting Standard-Library Facilities

| Facility | Use |
|---|---|
| `hashlib.sha256` | Request, content, table-digest, manifest, and backup integrity identifiers; never as encryption. |
| `json` with canonical separators and sorted keys | Request hashes, manifests, deterministic exports, trace/config fingerprints. |
| `uuid.uuid4` | Preallocated opaque event/memory/turn IDs; caller idempotency remains a separate key. |
| `pathlib`, `tempfile`, `os.open`, `os.replace`, `fsync` | Contained staging, mode-restricted output, and atomic publish. |
| Existing Pydantic/FastAPI models | Request bounds, strict lifecycle intent, and explicit unsupported-format errors. |

### Version and Environment Verification

- `chromadb` 1.5.9 is the currently returned PyPI release; its PyPI JSON records an upload on 2026-05-05. [VERIFIED: https://pypi.org/pypi/chromadb/json]
- The project requires Python 3.12+, locks Chroma 1.5.9, Sentence Transformers 4.1.0, and pytest 9.0.3. [VERIFIED: `pyproject.toml`, `uv.lock`]
- The `.venv` runtime is Python 3.12.9 with SQLite 3.47.1, FTS5 enabled, and `sqlite3.threadsafety == 3`. [VERIFIED: local runtime probe]
- Context7 was selected by the research seam but was not available in this environment. All external API claims below were therefore checked against primary official Python, SQLite, Chroma, PyPI, and OWASP pages. [VERIFIED: research-tool availability probe]

### Alternatives Considered

| Recommended | Instead of | Reason |
|---|---|---|
| Standard-library SQLite + FTS5 | A broad memory framework or a second primary database | The locked decision requires one local, inspectable truth owner; existing facilities cover transactions, search, and snapshots. |
| Chroma as a disposable cosine projection | Chroma as durable truth or a new vector database | Preserves compatibility without a package migration or dual authority. |
| Normalized rank fusion | Page-local min-max or raw weighted-score addition | Rank fusion is deterministic across channels whose raw scores have different semantics. |
| Versioned JSON export | Placeholder CSV/Markdown/PDF exporters | One truthful format is safer than several advertised but incomplete formats. |

## Architecture Patterns

### System Data Flow

```text
Loopback API request
  -> validate scope + caller idempotency key + canonical request hash
  -> provider produces Aura response
  -> BEGIN IMMEDIATE on the one SQLite writer
       -> turn + user event + Aura event
       -> typed derivations + provenance + supersession edges
     COMMIT (or complete rollback)
  -> projection queue/reconciler
       -> stable-ID Chroma upsert (disposable)
       -> FTS5 is transactionally maintained with SQLite
  -> retrieval request
       -> bounded FTS candidates ----\
       -> bounded Chroma candidates --+-> hard gates -> neutral RRF -> trace -> page
                                            |
                                            +-> Phase 4 seam returns constant 0

Lifecycle command
  -> explicit plan/inventory
  -> snapshot | isolated restore | JSON export | confirmed deletion
  -> exact verification evidence and residual-copy report
```

### Recommended Project Structure

```text
aura_backend/storage/
├── models.py          # typed IDs, events, memories, traces, lifecycle contracts
├── connection.py      # explicit path, PRAGMAs, writer transaction boundary
├── schema.py          # versioned forward migrations and FTS triggers
├── repository.py      # sole durable read/write owner
├── retrieval.py       # gates, normalized RRF, pagination, trace construction
├── projection.py      # Chroma upsert/reconcile/rebuild adapter
├── migration.py       # read-only legacy inventory/import/parity
├── lifecycle.py       # snapshot, restore, export, retention, deletion
└── benchmark.py       # sanitized corpus runner and kill gates

tests/storage/
├── test_atomic_ledger.py
├── test_idempotency.py
├── test_provenance_supersession.py
├── test_legacy_migration.py
├── test_projection_rebuild.py
├── test_hybrid_retrieval.py
├── test_snapshot_restore.py
├── test_export_delete.py
└── test_memory_benchmark.py
```

The new storage objects must be injected at application startup. They must not be module singletons and must not initialize a model or database at import time. [VERIFIED: requirement ARCH-01 and current singleton defect]

## Recommended SQLite Contract

### Schema

Use a monotonically versioned schema (`PRAGMA user_version`) and explicit SQL migrations committed in the repository. Recommended logical tables:

| Table | Required columns and constraints | Contract |
|---|---|---|
| `memory_scopes` | `scope_id TEXT PRIMARY KEY`, `created_at TEXT NOT NULL` | Local logical isolation without accounts or sign-in. |
| `sessions` | `session_id TEXT PRIMARY KEY`, `scope_id` FK, `created_at`, `closed_at`; index `(scope_id, created_at)` | Session grouping is not an authorization boundary. |
| `turns` | `turn_id TEXT PRIMARY KEY`, `scope_id` FK, `session_id` FK, `idempotency_key`, `request_hash`, `response_hash`, `occurred_at`; `UNIQUE(scope_id,idempotency_key)` | One durable retry identity per scope. Request and response identities remain distinguishable. |
| `events` | integer `event_pk` PK for FTS rowid; unique opaque `event_id`; `scope_id` FK; `turn_id` FK; `ordinal`; `event_type`; `actor`; `observed_at`; `content`; canonical `payload_json`; `content_sha256`; `source_kind`; `UNIQUE(turn_id,ordinal)` | Immutable source observations with directly enforceable scope. Normal completed turns use ordinals 0=user and 1=Aura. Historical fragments are explicitly typed, not fabricated into pairs. |
| `derived_memories` | integer PK; unique `memory_id`; `scope_id`; `memory_kind` constrained to fact/preference/episode/goal/relationship; `canonical_text`; bounded `confidence`; `epistemic_status`; `primary_source_event_id NOT NULL`; `created_at`; `content_sha256` | Lossy interpretations are visibly distinct from events and always uncertain/status-bearing. |
| `memory_sources` | `memory_id` FK, `event_id` FK, relation constrained to support/contradict/context; composite PK | Complete many-to-many provenance. |
| `memory_supersessions` | `old_memory_id`, `new_memory_id`, `basis_event_id`, `reason`, `created_at`; unique edge and `old != new` check | Corrections append evidence and an edge; old rows remain unchanged. |
| `memory_retractions` | `memory_id`, `basis_event_id`, `reason`, `created_at` | Explicit withdrawal without pretending a replacement is known. |
| `legacy_sources` | `root_fingerprint`, `collection_name`, `legacy_id`, `imported_origin_id`, canonical raw metadata JSON; unique source triple | Repeatable, auditable import without destructive deduplication. |
| `projection_generations` | generation ID, embedding model/config hash, metric, SQLite watermark, build state/timestamps | Makes staleness and rebuild provenance testable. |
| `retrieval_runs` | run ID, scope, query-event reference or query hash, config version, projection generation, created time | Binds traces to one deterministic configuration without copying sensitive query text to logs. |
| `retrieval_candidates` | run ID, origin ID, lexical/vector raw values and ranks, every gate result/reason, neutral score, selected rank | Explains selected and rejected candidates. Apply a bounded retention policy to traces. |

Create external-content FTS5 tables for event text and derived-memory text, keyed by their integer rowids, with insert/update/delete triggers and an explicit rebuild migration. This avoids duplicating authoritative text while keeping FTS transactionally aligned. SQLite warns that external-content tables are inconsistent unless triggers and the initial rebuild are handled; tests must cover both. [CITED: https://www.sqlite.org/fts5.html#external_content_tables]

Use `unicode61 remove_diacritics 2` with no stemming and no prefix indexes initially. It is deterministic, language-tolerant for the current corpus, and minimizes unbenchmarked behavior. This is a design decision to be frozen in the benchmark manifest, not a claim that it is universally optimal.

Do not add a database trigger that makes authorized deletion impossible. Append-only behavior should be available only through the repository interface and proved with tests; the lifecycle service is the sole audited exception for explicit deletion.

### Connection and Transaction Rules

1. Resolve one explicit `AURA_DATA_DIRECTORY` once at startup and pass absolute paths into storage objects. No persistence path may depend on process cwd.
2. Every connection enables `PRAGMA foreign_keys = ON`; SQLite does not guarantee this default. Configure WAL mode and a finite busy timeout. [CITED: https://www.sqlite.org/pragma.html#pragma_foreign_keys]
3. Serialize writes through one application writer boundary. Begin a turn with `BEGIN IMMEDIATE`, which acquires write intent early; SQLite permits only one simultaneous writer. [CITED: https://www.sqlite.org/lang_transaction.html]
4. Preallocate opaque IDs. Insert the turn, both source events, derivations, provenance, and supersession edges, then commit. Any exception rolls the entire unit back.
5. Use placeholders for all values. Python explicitly warns against string-built SQL and documents qmark/named bindings. [CITED: https://docs.python.org/3.13/library/sqlite3.html#how-to-use-placeholders-to-bind-values-in-sql-queries]
6. A repeated `(scope_id, idempotency_key)` with the same canonical `request_hash` returns the existing turn and event IDs. The same key with a different hash returns a typed conflict; it never overwrites or appends.
7. Compute `request_hash` from a versioned canonical client request containing scope, session, user input, and contract version. Store a separate `response_hash` for exact persistence-retry diagnostics. A committed replay of the same request key returns the original event IDs/response; it does not call the provider again or accept a newly generated answer. Do not put raw content in routine logs.
8. Commit SQLite before touching Chroma. A projection failure marks reconciliation pending but does not invalidate the durable turn or duplicate it on retry.

Python's connection context manager commits an open transaction on normal exit and rolls it back on exception, but does not close the connection. The implementation should still make transaction start and connection ownership explicit. [CITED: https://docs.python.org/3.13/library/sqlite3.html#how-to-use-the-connection-context-manager]

### Provenance and Supersession Rules

- Source events are immutable observations. Aura's own statement is stored as an Aura event, not promoted automatically to a fact about Ty.
- Every derived row has at least one source edge and a non-null primary source. A repository query must reject orphaned derivations even if the database was externally damaged.
- Corrections insert a new source event and, if warranted, a new derivation plus a supersession edge. The prior text, confidence, and timestamp are unchanged.
- “Current” is a view/query over rows with no valid outgoing supersession or retraction; it is not a mutable `is_current` flag that can drift from the edge history.
- Supersession must remain scope-local and acyclic. Reject self-edges and detect cycles in repository validation/tests.
- Imported ambiguity remains explicit: unmatched historical rows use `source_kind='legacy_fragment'` and carry the root/collection/legacy ID. Do not invent a conversational pair or provenance.

## Chroma as a Rebuildable Projection

Use one adapter whose public operations are `upsert_committed`, `delete_origins`, `query_candidates`, `reconcile`, and `rebuild`. Stable projection IDs should be `event:{event_id}` and `memory:{memory_id}`. Chroma's collection API documents `upsert`, `get`, `query`, and `delete`; use those public APIs rather than its internal SQLite schema. [CITED: https://docs.trychroma.com/reference/python/collection]

Projection metadata must include `scope_id`, origin kind/ID, content hash, SQLite schema version, projection generation, embedding model/config hash, and active status. The collection must explicitly use cosine distance. Chroma documents cosine distance as `1 - cosine similarity`, whereas its default HNSW space is squared L2. [CITED: https://docs.trychroma.com/docs/collections/configure]

Index committed source events for direct conversational recall and active derived memories for semantic abstraction. Never index a derivation without provenance. Rebuild algorithm:

1. Create a fresh generation/directory; do not mutate the current generation in place.
2. Page deterministically through SQLite truth.
3. Embed and `upsert` using stable IDs.
4. Compare expected IDs, counts, content hashes, model/config, and deterministic retrieval fixtures.
5. Atomically switch the configured generation only after parity.
6. Keep the failed/old projection as a disposable diagnostic until the verification record is stored; deletion remains a separate lifecycle decision.

## Staged Compatibility and Migration Strategy

### Stage 0 — Refresh Preservation Inventory

- Re-run metadata-only inventory across both active roots, both data roots, every backup root, test roots, profiles, exports, caches, Memvid data, and `memvid_videos` archives.
- Record absolute path, declared role, file count/bytes, SQLite inventory, collection/count metadata, archive readability, and a content-free fingerprint.
- Detect active writers/open handles. A Chroma process from another repository is running on port 8001, but no Aura process or user systemd unit was found; the migration must identify stores by absolute path rather than process-name substring. [VERIFIED: local process and user-unit probe]
- Refresh the outside-Git backup and isolated restore evidence before reading historical data for import.

### Stage 1 — Create New Truth Without Switching Reads

- Create a new, ignored, explicitly configured runtime root and SQLite database. Recommended migration default: repository-resolved `aura_data_v2/aura.sqlite3`, overridden by an absolute `AURA_DATA_DIRECTORY`; never reuse either historical active directory during import.
- Apply schema migration and FTS rebuild; prove an empty snapshot/restore cycle first.
- Keep every old root read-only and unchanged.

### Stage 2 — Import From Disposable Restored Copies

- Restore each historical root to a temporary isolated directory and read it through the public Chroma API.
- Import in bounded pages. The unique `(root_fingerprint, collection_name, legacy_id)` key makes reruns safe.
- Preserve raw metadata canonically and map only evidence-backed fields. Missing pairs or timestamps remain typed legacy fragments.
- Preserve identical content from different origins as separate ledger evidence. Deduplicate only at retrieval time by content hash; never delete or silently merge history.
- Record the known foreign-key anomalies as source evidence. Do not run repair, checkpoint, `REINDEX`, or schema mutations on original Chroma databases.

### Stage 3 — Shadow and Reconcile

- Make SQLite the first write in the stable persistence interface; derive stable projection updates only after commit.
- Run existing routes against compatibility adapters and compare old/new counts, turn grouping, content hashes, profile responses, failure behavior, and sanitized retrieval fixtures.
- Exercise crashes before commit, after commit/before projection, mid-projection, and before retry. Every case must converge to one complete turn and one projection record per origin.

### Stage 4 — Gated Read Switch

Switch history and retrieval to the new service only after all of these are simultaneously true:

- fresh inventory and outside-Git restore evidence pass;
- import counts and semantic table digests match the declared mapping;
- zero orphan provenance, cross-scope edges, or supersession cycles;
- rebuilt projection parity and deterministic retrieval fixtures pass;
- neutral benchmark meets every competence/containment gate;
- rollback to the preserved legacy read adapter is rehearsed.

### Stage 5 — Retire Legacy Writers, Preserve History

Disable legacy Chroma writes and the `copytree` backup service only after the switch gate. Keep both active Chroma roots, all historical stores, backups, and Memvid archives immutable. Phase 3 should not delete them merely because migration succeeded; any later disposal uses the explicit deletion contract and a fresh restore proof.

Dual durable writes are prohibited: they create split-brain authority and cannot be atomic across SQLite and Chroma. Shadow comparison means one SQLite truth plus repairable projections, not two sources of truth.

## Neutral Hybrid Retrieval Contract

### Candidate Admission and Hard Gates

For a request scoped to one local user:

1. Query at most 50 FTS candidates and 50 Chroma candidates. Candidate caps are configuration-versioned constants, not client inputs.
2. Chroma receives an exact `scope_id` metadata filter. Every result is revalidated against SQLite; a filter alone is not trusted.
3. Reject candidates whose SQLite origin is missing, scope differs, provenance is absent, derivation is superseded/retracted, content hash or projection generation is stale, or neutral relevance admission fails.
4. A recalled record is untrusted historical text. It remains inside the existing memory delimiters and cannot supply system instructions, tool authority, or new evidence.
5. Deduplicate the eligible set by canonical origin/content hash while retaining every contributing lexical/vector source in the trace.

### Score Normalization

FTS5's BM25 function returns better matches as lower numbers, and its magnitude is query/corpus dependent. Chroma distance scale depends on collection metric. Do not min-max normalize a single result page and do not add raw BM25 to `1 - distance`. [CITED: https://www.sqlite.org/fts5.html#the_bm25_function] [CITED: https://docs.trychroma.com/docs/collections/configure]

Use normalized reciprocal-rank fusion with fixed `k=60`:

```text
lex_rrf = ((1 / (k + lexical_rank)) / (1 / (k + 1))) if present else 0
vec_rrf = ((1 / (k + vector_rank))  / (1 / (k + 1))) if present else 0
neutral_score = (lex_rrf + vec_rrf) / 2
```

This produces a bounded, deterministic neutral score in `[0,1]` without pretending the raw channels share units. Preserve raw BM25, cosine distance, and `clamp(1 - cosine_distance, 0, 1)` in the trace. Use cosine similarity only for a corpus-pre-registered vector admission threshold; use lexical phrase/exact-match and token-coverage controls for lexical admission.

Deterministic ordering is:

```text
neutral_score DESC,
exact_match DESC,
observed_at DESC,
origin_id ASC
```

Supersession is the freshness gate; timestamp is only a tie-breaker, so newer irrelevant text cannot displace stronger evidence.

### Trace and Pagination

Every considered candidate records: query/config hash, SQLite schema and projection generation, origin ID/type, raw BM25 and lexical rank, vector metric/distance/rank, both normalized RRF components, content/provenance/scope/supersession/relevance gate results, rejection code, neutral score, selected rank, and dedup contributors. Normal application logs contain only run IDs, counts, timings, and reason codes—not remembered content.

Return `items`, `next_cursor`, and `has_more`. Default page size is 20 and hard maximum is 100. Use a stored `retrieval_run` plus the last stable sort tuple as an opaque cursor; reject a cursor whose scope, query hash, config, generation, or expiry differs. Ledger history uses keyset pagination over `(observed_at, event_id)`, never a high unbounded offset. Chroma's API supports `limit`/`offset`, but bounded materialization into a stored run gives stable pages when the projection changes. [CITED: https://docs.trychroma.com/docs/querying-collections/query-and-get]

The Phase 4 scorer interface exists now but always returns `0.0`; it cannot change admission, scope, provenance, supersession, or neutral anchors. The neutral score and original rank remain permanently visible in traces.

## Snapshot, Restore, Export, and Deletion

### Consistent Snapshot

Use `sqlite3.Connection.backup()` from the live source connection to a newly created target database under the configured outside-Git backup root. Python documents incremental pages, progress callbacks, and sleep between busy retries; SQLite documents that the completed backup is a consistent snapshot even while the source is in use. [CITED: https://docs.python.org/3.13/library/sqlite3.html#sqlite3.Connection.backup] [CITED: https://www.sqlite.org/backup.html]

Snapshot sequence:

1. Resolve/contain source and destination, refuse symlinks, create a mode-`0600` temporary target, and bind the operation to a snapshot ID.
2. Run incremental backup with finite time/resource bounds. A busy timeout or resource limit is an incomplete result, never success.
3. Close and fsync the database and parent directory; calculate SHA-256; atomically rename.
4. Write a manifest containing schema/config/commit identifiers, source watermark, per-table counts and deterministic semantic digests, backup hash/size, FTS config, projection generation, timestamps, and the exact verification checklist.
5. Do not copy Chroma as required backup data. The restore test rebuilds it from SQLite.

### Isolated Restore Proof

Restore only into a new temporary directory. Refuse an existing active path. Exact success requires all checks, not a partial percentage:

- manifest and backup file hashes match;
- `PRAGMA integrity_check` returns exactly `ok`;
- `PRAGMA foreign_key_check` returns no rows—SQLite explicitly states `integrity_check` does not find FK errors; [CITED: https://www.sqlite.org/pragma.html#pragma_integrity_check]
- schema version, per-table counts, and semantic digests match;
- FTS tables rebuild and lexical fixtures pass;
- a new disposable Chroma projection reaches count/hash parity and vector fixtures pass;
- direct, correction, provenance, pagination, and cross-scope fixtures pass;
- no file under the active runtime root changed.

Only then publish a content-free restore evidence record. Never include conversation text in manifests or logs.

### Truthful Export

Advertise JSON only in Phase 3. An unsupported format produces a clear typed `400` response; it never produces an empty placeholder file.

One scope export runs in a consistent SQLite read transaction and contains versioned metadata plus actual sessions, events, derived memories, source edges, supersession/retraction edges, and profile records owned by the scope. Rows use a documented deterministic order and include counts and a manifest hash. Embeddings, internal retrieval traces, secrets, provider credentials, and unrelated scopes are excluded by default. Use contained mode-`0600` staging, fsync, and atomic rename. Add round-trip tests that compare exported IDs/counts/content hashes with the ledger.

### Explicit Deletion

Deletion is a four-step protocol:

1. **Plan:** Resolve an exact action (`session`, `scope`, `generated_export`, `projection_generation`, `archive`, or `backup_generation`) and enumerate canonical rows, FTS rows, Chroma IDs, provider/in-memory caches, profile data, exports, Memvid archives, historical roots, and applicable backup generations.
2. **Confirm:** Return a short-lived confirmation token bound to scope, action, inventory digest, counts, policy, and expiry. Vague phrases such as “clear memory” produce no mutation.
3. **Execute:** In one SQLite transaction delete the explicitly approved canonical rows/FTS state, then remove derived projection/cache/export items. Historical roots and backups are not silently rewritten.
4. **Verify:** Query by stable IDs, scope, and content hashes across every enumerated active target. Projection failure leaves status `incomplete` with a retryable work item. Report every retained historical/archive/backup copy.

A normal scope deletion must say that preserved roots/backups still contain historical copies. A claim of complete purge is prohibited until those separately named generations are explicitly approved and verified. Backup retention deletion is a distinct operation and may execute only after another independently restore-proven generation exists.

SQLite `secure_delete` does not by itself guarantee purging FTS shadow-table content; FTS5 has a separate secure-delete option with version caveats, and WAL frames/checkpoints also matter. Therefore distinguish **application-level deletion** from **best-effort physical purge** and never promise forensic erasure. [CITED: https://www.sqlite.org/pragma.html#pragma_secure_delete] [CITED: https://www.sqlite.org/fts5.html#the_secure_delete_configuration_option]

## Sanitized Benchmark and Pre-Registered Kill Criteria

### Corpus

Create `tests/fixtures/memory_eval/corpus.jsonl` plus `manifest.json`. Use invented people, places, preferences, goals, corrections, dates, and distractors only; never copy production text. The manifest freezes corpus hash/version, query cases, expected origin IDs, scope IDs, embedding model/config, FTS tokenizer, Chroma metric/generation config, candidate caps, RRF `k`, admission thresholds, page bounds, hardware/runtime label, and benchmark code commit.

Required case classes:

| Class | What it proves |
|---|---|
| Direct and paraphrased recall | Lexical and semantic paths recover relevant evidence. |
| Correction / stale fact | New evidence wins and superseded derivations are never eligible. |
| Temporal question | Time-qualified evidence is selected without rewriting history. |
| Distractors | High lexical or semantic overlap does not bypass relevance gates. |
| Critical fact absent | System abstains rather than inventing or using recalled Aura text as proof. |
| Duplicate sources | Results deduplicate while trace retains contributors. |
| Provenance | Every selected derivation links to valid source events. |
| Cross-user collision | Identical/paraphrased content in another scope never appears. |
| Stored prompt injection | Recalled instructions remain quoted data and cannot alter authority. |
| Pagination | Stable, bounded pages have no gaps/duplicates across a frozen run. |

Use at least 10,000 deterministic synthetic events for latency/duplicate measurement, a fixed seed, a warmed local process, and three fixed repetitions for reported timing. GPU is optional; correctness and leak gates run on CPU.

### Competence and Containment Gates

Use the accepted pre-registered gates from `KILL-CRITERIA.md`:

- direct and paraphrased `Recall@5 >= 0.90`;
- explicit-update/correction accuracy `>= 0.90`;
- critical-absent abstention `= 1.00`;
- cross-user leakage `= 0`;
- selected items without valid provenance `= 0`;
- warmed local `p95 < 250 ms` at 10,000 events.

Add positive and negative instrument controls: a unique exact fact must retrieve; a correction must exclude stale memory; a deliberately scope-free retrieval ablation must trigger the leak detector; an absent fact must abstain. If a control fails, the run measures nothing useful and cannot clear a gate.

Preserve the neutral arm for all future comparisons. Graph, RLM, or Memvid core adoption requires an Aura-specific absolute `+5 percentage-point` quality gain or `>=30%` storage/latency gain with no regression on correctness, stale-fact, abstention, provenance, privacy, or restore gates. Stop after three bounded cycles or one workday. `RESOURCE_LIMIT`, timeout, truncated corpus/search, or missing control is inconclusive failure, never a win. [VERIFIED: canonical `KILL-CRITERIA.md`]

## Runtime State Inventory

| Category | Items found | Required action |
|---|---|---|
| Stored data | Phase 1 found fourteen declared roots, both active Chroma roots, 77 SQLite files, 1,204 restored records across ten collections, backup/test/archive roots, and known historical FK anomalies. Twelve `.mv2` archives under `aura_backend/memvid_videos` also need inclusion in the refreshed inventory. | Metadata inventory + outside-Git backup/isolated restore first; import from disposable copies; never repair or delete originals. [VERIFIED: Phase 1 verification and filesystem metadata] |
| Live service config | Runtime paths are supplied by `.env`/CLI/Docker mappings; defaults are cwd-relative. No external UI/database-hosted Aura configuration was discovered. A Chroma service for a different repository is live at `/home/ty/data/chroma`. | Resolve Aura paths absolutely; preflight exact open handles/paths before migration; do not disturb the unrelated service. [VERIFIED: code/config/process probe] |
| OS-registered state | No Aura/Chroma user systemd unit was found. No active Aura/uvicorn process was found in the process-name probe. | Recheck immediately before switch; no OS migration task is currently required. [VERIFIED: `systemctl --user` and `pgrep` probes] |
| Secrets / environment | `.env` is ignored; `.env.example` declares cwd-relative `CHROMA_PERSIST_DIRECTORY` and `AURA_DATA_DIRECTORY`. Provider keys remain outside Git. | Add an explicit v2 data-root setting or resolve the existing setting once; never print/copy secrets into manifests, traces, exports, or tests. [VERIFIED: `.env.example`, `.gitignore`, config code] |
| Build artifacts / installed packages | Chroma databases, SQLite/WAL files, backup/export/profile/log paths, Python caches, model cache, and generated Memvid artifacts exist outside source semantics. Relevant database/export/log patterns are ignored. | Add Git-hygiene tests for every new v2 path; projection/model cache is rebuildable and not part of ledger backup. [VERIFIED: `.gitignore`, lock, filesystem metadata] |

Phase 1's restored source-set hash, ten-collection/1,204-record counts, and two retrieval fixtures are the compatibility floor, not permission to pick one active root. [VERIFIED: Phase 1 verification]

## Environment Availability

| Dependency | Required by | Available | Version / state | Fallback |
|---|---|---:|---|---|
| Project `.venv` Python | All Phase 3 code | Yes | Python 3.12.9 | None needed. |
| SQLite + FTS5 | Ledger/retrieval/backup | Yes | SQLite 3.47.1; FTS5 enabled | Block phase if unavailable; no substitute. |
| `uv` | Locked commands | Yes | 0.11.21 | Existing `.venv` can run Python, but planning should retain `uv --locked --no-sync`. |
| Chroma | Vector projection/import | Yes | 1.5.9 | Neutral lexical path can degrade explicitly; projection tests still required before release. |
| SentenceTransformer model | Vector projection | Yes | `all-MiniLM-L6-v2` cached | Rebuild can run CPU-only; do not download/change model silently. |
| `pytest` | Validation | Yes | 9.0.3 | None needed. |
| Outside-Git backup storage | Snapshots | Yes | `/backup` had about 234 GB free at inspection | Fail closed if configured backup root lacks space; never fall back inside Git. |
| Working filesystem space | Migration staging | Constrained | `/home` had about 59 GB free and was 94% used | Preflight projected space; stage large preservation copies under `/backup`, not active roots. |
| GPU | Optional embedding speed | Yes | RTX 3060 12 GB | CPU is correctness baseline. |

No missing dependency blocks planning. Disk-space preflight is mandatory before copying historical roots or rebuilding projections. [VERIFIED: local environment probes]

## Don't Hand-Roll

| Problem | Do not build | Use instead | Why |
|---|---|---|---|
| Consistent live database copy | Recursive copy, WAL file juggling, pause/sleep guesses | `sqlite3.Connection.backup()` | SQLite coordinates pages and concurrent source changes. [CITED: https://www.sqlite.org/backup.html] |
| Lexical index | Python token inverted index | SQLite FTS5 external-content tables | Transactions, BM25, tokenizer, triggers, and rebuild are already supplied. |
| SQL escaping | String interpolation/quote replacement | DB-API placeholders | Prevents SQL injection and quoting defects. |
| Cross-store transaction | “Atomic” dual write to SQLite and Chroma | Commit ledger, then idempotent projection reconciliation | There is no shared transaction manager; stable IDs make repair deterministic. |
| Raw-score fusion | Ad hoc weighted BM25 plus distance | Fixed normalized reciprocal-rank fusion | Raw channels have different directions and scales. |
| Database/vector repair | Direct edits to Chroma internal SQLite | Rebuild a fresh projection via public API | Internal schema is third-party state, not Aura truth. |
| Backup/export encryption | Custom cipher or password wrapper | No new encryption claim; use OS permissions and document exposure until a vetted requirement/library is chosen | Hand-rolled cryptography creates false assurance. |
| Destructive “cleanup” | Broad glob deletion or inferred natural-language intent | Enumerated plan/confirm/execute/verify lifecycle service | Prevents accidental loss and makes residual copies honest. |

## Common Pitfalls

### Treating a successful response as a persisted turn
The current route intentionally returns provider output when persistence degrades. Preserve that user-visible availability only if the response includes typed persistence status and an idempotent retry token. Tests must prove retry convergence rather than equating HTTP success with durability.

### Letting SQLite and Chroma become co-authorities
Never read an orphan Chroma record as truth. A vector hit must resolve to an active, hash-matching SQLite origin or be rejected and queued for reconciliation.

### Building FTS triggers but forgetting existing rows
External-content triggers affect future changes only. Run the FTS `rebuild` command after import and compare row counts/fixtures. [CITED: https://www.sqlite.org/fts5.html#external_content_tables]

### Relying on `integrity_check` alone
It does not report foreign-key violations. Restore gates require both `integrity_check` and `foreign_key_check`. [CITED: https://www.sqlite.org/pragma.html#pragma_integrity_check]

### Page-local min-max normalization
It changes scores and ordering as the candidate set/page changes. Fixed rank fusion and stable tie-breakers make traces reproducible.

### Accidental scope override
Do not merge a caller-provided metadata dictionary over required filters. The repository requires scope separately and validates every returned origin again.

### Migrating “cleaned” history
Do not pair fragments by guess, repair old FK anomalies, discard duplicates, or select the larger active root. Preserve origin and uncertainty so parity remains auditable.

### Calling deletion complete while backups remain
Report application-level active deletion and retained recovery copies separately. Complete purge is a distinct explicitly approved operation.

### Logging the evidence while protecting the database
Trace IDs, hashes, scores, and reason codes are sufficient for ordinary audit. Remembered content in logs/manifests recreates the privacy problem in another store.

### Optimizing before the instrument works
If the leaky ablation does not fail or the positive retrieval control does not pass, benchmark output is invalid. Preserve the artifact as a failed instrument, not a model result.

## Code Examples

### Atomic parameterized transaction

```python
# Sources:
# https://docs.python.org/3.13/library/sqlite3.html#transaction-control
# https://docs.python.org/3.13/library/sqlite3.html#how-to-use-placeholders-to-bind-values-in-sql-queries
connection.execute("BEGIN IMMEDIATE")
try:
    connection.execute(
        "INSERT INTO turns(turn_id, scope_id, idempotency_key, request_hash) VALUES (?, ?, ?, ?)",
        (turn_id, scope_id, idempotency_key, request_hash),
    )
    # Insert both events and their provenance-bearing derivations here.
    connection.commit()
except Exception:
    connection.rollback()
    raise
```

### Consistent online snapshot

```python
# Source: https://docs.python.org/3.13/library/sqlite3.html#sqlite3.Connection.backup
with sqlite3.connect(snapshot_path) as target:
    source.backup(target, pages=256, progress=progress_callback, sleep=0.050)
```

The production wrapper must add containment, exclusive creation, permissions, fsync/hash/manifest, time bounds, and isolated verification.

### FTS external-content index

```sql
-- Source: https://www.sqlite.org/fts5.html#external_content_tables
CREATE VIRTUAL TABLE event_fts USING fts5(
  content,
  content='events',
  content_rowid='event_pk',
  tokenize='unicode61 remove_diacritics 2'
);

INSERT INTO event_fts(event_fts) VALUES('rebuild');
```

Add the documented insert/delete/update triggers in the schema migration and test all three transitions.

### Stable Chroma projection

```python
# Sources:
# https://docs.trychroma.com/reference/python/collection
# https://docs.trychroma.com/docs/collections/configure
collection.upsert(
    ids=[f"memory:{memory_id}"],
    documents=[canonical_text],
    embeddings=[embedding],
    metadatas=[{
        "scope_id": scope_id,
        "origin_id": memory_id,
        "content_sha256": content_sha256,
        "generation": generation_id,
    }],
)
```

Collection creation must freeze cosine metric configuration using the API supported by locked Chroma 1.5.9; add a compatibility test because Chroma configuration APIs have evolved.

## Security Domain

OWASP ASVS 5.0.0 is the current stable version exposed by the official project and provides a verification basis for application security controls. [CITED: https://owasp.org/www-project-application-security-verification-standard/]

### Applicable ASVS Categories

| ASVS category | Applies | Phase 3 control |
|---|---:|---|
| V2 Authentication | No | Locked local mode has no account/sign-in. Do not add one. |
| V3 Session Management | Limited | Session IDs group conversations but confer no authority; validate scope on every operation. |
| V4 Access Control | Yes | Mandatory scope arguments, scope-local FKs/edges, and two-scope adversarial tests prevent IDOR-style cross-user reads/deletes. |
| V5 Validation, Sanitization, Encoding | Yes | Pydantic bounds, strict enums, parameterized SQL, canonical cursor validation, and path containment. |
| V6 Stored Cryptography | Limited | SHA-256/HMAC protect integrity/confirmation binding, not confidentiality. No custom encryption or erasure promise. |
| V7 Error Handling and Logging | Yes | Content-free structured outcomes; resource limits and partial lifecycle checks fail closed. |
| V8 Data Protection | Yes | Mode-`0600` files, outside-Git backups, scope-limited exports, content-free traces/logs, explicit retention. |
| V9 Communication | Limited | Loopback-only remains mandatory; remote Chroma/storage is out of scope. |
| V12 Files and Resources | Yes | Existing no-follow containment plus exclusive temp files, atomic rename, isolated restore roots. |
| V13 API and Web Service | Yes | Strict JSON/origins, bounds, typed lifecycle actions, and confirmation tokens. |

ASVS categories and its role as a secure-development/verification baseline are documented by OWASP. [CITED: https://devguide.owasp.org/en/08-culture-process/04-asvs/]

### Threat Model

| Threat | STRIDE | Required mitigation / verification |
|---|---|---|
| SQL injection through queries, exports, cursors, or metadata | Tampering / disclosure | Parameterized SQL; allowlisted identifiers/order clauses; malicious-string tests. |
| Cross-scope retrieval or deletion | Information disclosure / elevation | Scope required at repository boundary, conjunct filtering, origin revalidation, two-scope tests including equal content. |
| Stored prompt injection in recalled text | Elevation / spoofing | Preserve untrusted delimiters; never convert recall to system authority/evidence; injection corpus cases. |
| Retry duplication or half-turn | Tampering / repudiation | Unique idempotency key + request hash; one transaction; failure at every boundary. |
| Stale/tampered projection | Tampering | Stable origin IDs, generation/content hash checks, reject-and-rebuild behavior. |
| Traversal, symlink swap, or overwrite in snapshot/export/restore | Tampering / disclosure / denial | Existing containment/no-follow helpers, exclusive creation, atomic publish, refuse active/existing restore target. |
| Forged or partial restore evidence | Spoofing / repudiation | Manifest/check-set hash, exact required checks, fail closed on timeout/resource limit. |
| Vague or replayed deletion request | Tampering / denial | Explicit action inventory, short-lived digest-bound confirmation, replay rejection, residual report. |
| Sensitive text duplicated into logs/traces/manifests | Disclosure | IDs, hashes, counts, timings, and reason codes only; automated log-capture tests. |
| Backup/export theft from local disk | Disclosure | Mode `0600`, contained configured roots, no Git, disclose absence of at-rest encryption rather than hand-roll it. |
| Disk exhaustion during backup/import/rebuild | Denial of service | Preflight size/free-space, fixed bounds, outside-Git staging, cleanup only operation-owned temp files. |

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` (`testpaths = ["tests"]`) |
| Quick run command | `uv run --locked --no-sync python -m pytest -q tests/storage tests/memory tests/api/test_filesystem_contract.py tests/characterization/test_persistence_contract.py -m 'not live'` |
| Current focused baseline | `uv run --locked --no-sync python -m pytest -q tests/memory tests/api/test_filesystem_contract.py tests/characterization/test_persistence_contract.py tests/preservation/test_backup_restore.py -m 'not live'` → 57 passed in 9.78 s [VERIFIED: local run] |
| Full suite command | `uv run --locked --no-sync python -m pytest tests -q -m 'not live'` |
| Current full baseline | 512 passed, 2 skipped, 1 deselected in 25.67 s [VERIFIED: local run] |

### Phase Requirements to Test Map

| Req ID | Behavior | Test type | Automated command | Exists? |
|---|---|---|---|---|
| PRES-04 | No generated v2 database, WAL, backup, export, profile, log, or secret becomes tracked. | hygiene | `uv run --locked --no-sync python -m pytest -q tests/storage/test_git_hygiene.py` | Wave 0 |
| TEST-03 | Stable API/persistence/failure contracts survive adapter replacement. | characterization + integration | `uv run --locked --no-sync python -m pytest -q tests/characterization/test_persistence_contract.py tests/api tests/storage/test_api_compatibility.py -m 'not live'` | Partial; Wave 0 for v2 |
| DATA-01 | Only repository/lifecycle writes truth; projection can fail/rebuild. | architecture + integration | `uv run --locked --no-sync python -m pytest -q tests/storage/test_storage_owner.py tests/storage/test_projection_rebuild.py` | Wave 0 |
| DATA-02 | Concurrent snapshot restores with exact integrity/count/hash/fixture parity. | integration + corruption | `uv run --locked --no-sync python -m pytest -q tests/storage/test_snapshot_restore.py` | Wave 0 |
| DATA-03 | JSON contains actual scoped records and round-trips; unsupported format fails. | API + integration | `uv run --locked --no-sync python -m pytest -q tests/storage/test_export_delete.py -k export` | Wave 0 |
| DATA-04 | Deletion plan enumerates every store; confirmation and residual verification are exact. | API + integration + adversarial | `uv run --locked --no-sync python -m pytest -q tests/storage/test_export_delete.py -k delete` | Wave 0 |
| DATA-05 | Bounds, cursor stability, relevance, latency, and duplicate behavior. | integration + benchmark contract | `uv run --locked --no-sync python -m pytest -q tests/storage/test_hybrid_retrieval.py tests/storage/test_memory_benchmark.py` | Wave 0 |
| DATA-06 | Events immutable; derivations require provenance; corrections append/supersede. | unit + integration | `uv run --locked --no-sync python -m pytest -q tests/storage/test_atomic_ledger.py tests/storage/test_provenance_supersession.py` | Wave 0 |
| DATA-09 | Neutral gates, trace, scope isolation, neutral anchor, and zero salience seam. | integration + adversarial | `uv run --locked --no-sync python -m pytest -q tests/storage/test_hybrid_retrieval.py` | Wave 0 |

### Required Failure Injection Matrix

Tests must fail execution after: turn insert; user-event insert; Aura-event insert; each derivation/source edge; before commit; after commit/before projection; mid-projection upsert; and before retry. Assert either zero durable rows or one complete turn, and after reconciliation exactly one projection row per origin. Also corrupt one projection hash, remove one provenance edge, forge one cursor, supply a scope-overwriting filter, interrupt a snapshot, tamper a manifest, and simulate one lifecycle target failure.

### Sampling Rate

- **Per task commit:** the narrow test file(s) owned by the task plus the current focused baseline.
- **Per wave merge:** `uv run --locked --no-sync python -m pytest tests -q -m 'not live'`.
- **Migration/read-switch gate:** full suite, fresh preservation inventory/restore proof, migration parity, and benchmark competence gates.
- **Phase gate:** full deterministic suite green before `/gsd-verify-work`; live-provider checks remain separately reported and cannot substitute.

### Wave 0 Gaps

- [ ] `tests/storage/conftest.py` — isolated SQLite/Chroma roots, fault injector, two-scope fixtures, deterministic clock/IDs.
- [ ] `tests/storage/test_atomic_ledger.py` and `test_idempotency.py` — transaction/retry matrix.
- [ ] `tests/storage/test_provenance_supersession.py` — invariants and correction cycles.
- [ ] `tests/storage/test_legacy_migration.py` — both-root import, rerun safety, fragments, anomalies, no source mutation.
- [ ] `tests/storage/test_projection_rebuild.py` — stable IDs, failure/reconcile, full discard/rebuild parity.
- [ ] `tests/storage/test_hybrid_retrieval.py` — hard gates, normalized RRF, traces, cursors, duplicates, injection boundary.
- [ ] `tests/storage/test_snapshot_restore.py` — concurrent backup, corruption, exact isolated verification.
- [ ] `tests/storage/test_export_delete.py` — real JSON, unsupported types, confirmation/replay, complete enumeration/residuals.
- [ ] `tests/storage/test_api_compatibility.py`, `test_storage_owner.py`, and `test_git_hygiene.py`.
- [ ] `tests/storage/test_memory_benchmark.py` and `tests/fixtures/memory_eval/{corpus.jsonl,manifest.json}` — instrument controls and kill gates.

No framework installation is needed. Keep all tests under root `tests/`; do not revive the uncollected boolean diagnostics.

## Explicit Deferrals

- **Phase 4:** dynamic affective state, neurochemical/brainwave controls, relationship updates, post-response feedback, and any non-zero salience rerank. Phase 3 provides only typed memory kinds, neutral anchors, full trace fields, and a constant-zero scorer seam.
- **Graph / temporal graph:** no graph database, graph projection, traversal retrieval, or graph-derived claim in Phase 3. A future graph is a rebuildable SQLite projection and must clear the measured alternative gate.
- **RLM / Graph-RLM:** no recursive reading runtime or dependency. It remains experimental until the neutral benchmark is competent and an Aura-specific comparison clears kill criteria.
- **Memvid:** keep optional copy-only cold archive behavior and inventory/readability tests. Do not use it as truth, primary backup, active retrieval, or deletion trigger; do not adopt it for performance without the required measured win.
- **Frontend:** no Phase 3 memory-management redesign; expose backend contracts for Phase 5.

## Open Questions

1. **RESOLVED — Where does the new database live?** Use a new ignored runtime root during migration, recommended repository-resolved `aura_data_v2/aura.sqlite3`, with an absolute configuration override. Resolve once; never use cwd-relative paths or reuse historical roots before the gate.
2. **RESOLVED — Which FTS tokenizer?** Freeze `unicode61 remove_diacritics 2`, without stemming/prefixes, until the sanitized benchmark justifies a change.
3. **RESOLVED — How are retries identified?** Caller supplies a stable per-request idempotency key; SQLite stores it with a versioned canonical request hash. UUID4 origin IDs are generated once and returned on replay.
4. **RESOLVED — How are historical duplicates handled?** Preserve every origin record and source fingerprint. Retrieval may collapse equal content while traces retain all contributors; migration never deletes/merges evidence.
5. **RESOLVED — Which legacy root is canonical?** Neither. Import both from restored copies and preserve provenance; do not decide from size, mtime, or apparent cleanliness.
6. **RESOLVED — What is indexed in Chroma?** Committed source events plus active provenance-bearing derived memories, using stable origin IDs and explicit cosine configuration.
7. **RESOLVED — Can snapshot run while Aura writes?** Yes through SQLite's backup API with finite busy/resource bounds; timeout or partial completion fails closed.
8. **RESOLVED — What happens to retained backups during deletion?** Normal active deletion reports them as residual copies. Backup/archive purge is a separately named, confirmed, restore-gated action.
9. **RESOLVED — Are historical Chroma FK anomalies repaired?** No. Preserve them, import through public APIs, and record mappings/anomalies without mutating source.
10. **RESOLVED — Does Phase 3 change the embedding model?** No. Retain and fingerprint `all-MiniLM-L6-v2`; rebuild with explicit cosine and evaluate before any later change.
11. **RESOLVED — Is at-rest encryption promised?** No. Use contained mode-restricted files and state the limitation. A future encryption requirement must select a vetted facility; no custom crypto in this phase.
12. **RESOLVED — What can affective salience do now?** Nothing to eligibility or rank. The seam returns zero and exists solely so Phase 4 can run a controlled comparison later.

## Assumptions Log

| # | Assumption | Risk if wrong | Planning treatment |
|---|---|---|---|
| A1 | The repository-resolved `aura_data_v2` default is acceptable as the new ignored migration root. | Operator may prefer an XDG or other external data path. | Treat the absolute configuration override as authoritative and test both; changing the safe default does not alter schema/lifecycle contracts. |
| A2 | A trace retention limit can be chosen during planning without a product-level retention policy. | Trace tables may grow or be retained longer than desired. | Default to a short bounded retention and expose it in lifecycle inventory; do not delete production traces until policy is explicit. |

No unresolved technical decision blocks planning. The two assumptions are reversible configuration choices and do not weaken locked safety contracts.

## Sources

### Primary — Repository and Preserved Evidence (HIGH confidence)

- `.planning/phases/03-memory-integrity-and-data-lifecycle/03-CONTEXT.md` — locked Phase 3 decisions and deferrals.
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` — requirement and boundary mapping.
- `.planning/research/affective-memory/{DECISION,AFFECT-MEMORY-LOOP,KILL-CRITERIA,FINDINGS,CENTER}.md` — accepted architecture, evidence discipline, competence floor, and kill gates.
- Phase 1 and Phase 2 verification reports/manifests — root inventory, immutable preservation, restore baseline, and runtime compatibility.
- Current persistence, retrieval, backup, export, deletion, Memvid, security, configuration, and test code listed in the file map.
- Local runtime, package, filesystem metadata, process/unit, and deterministic pytest probes performed 2026-08-31.

### Primary Official Documentation (MEDIUM-HIGH confidence)

- https://docs.python.org/3.13/library/sqlite3.html — transaction control, placeholders, context manager, backup API.
- https://www.sqlite.org/lang_transaction.html — writer concurrency and `BEGIN IMMEDIATE`.
- https://www.sqlite.org/fts5.html — external-content tables/triggers/rebuild, BM25 direction, tokenizer, FTS secure delete.
- https://www.sqlite.org/backup.html — consistent online backup behavior.
- https://www.sqlite.org/pragma.html — foreign keys, integrity/foreign-key checks, WAL/secure-delete limitations.
- https://docs.trychroma.com/reference/python/client — local PersistentClient.
- https://docs.trychroma.com/reference/python/collection — collection public operations.
- https://docs.trychroma.com/docs/collections/configure — HNSW default and cosine distance semantics.
- https://docs.trychroma.com/docs/querying-collections/query-and-get — query/get result and pagination behavior.
- https://pypi.org/pypi/chromadb/json — resolved public release metadata.
- https://owasp.org/www-project-application-security-verification-standard/ and https://devguide.owasp.org/en/08-culture-process/04-asvs/ — ASVS 5.0 and applicable verification categories.

### Tertiary

None. No community blog or training-only factual claim is used to choose the architecture.

## Metadata

**Confidence breakdown:**

- Current architecture and defects: **HIGH** — directly inspected code, tests, preserved manifests, and local runtime state.
- SQLite schema/transaction/lifecycle design: **HIGH** — locked decisions plus standard-library and upstream SQLite documentation.
- Chroma projection mechanics: **MEDIUM-HIGH** — locked version/code and official docs; exact 1.5.9 configuration syntax still requires a Wave 0 compatibility test.
- Retrieval normalization and benchmark design: **HIGH as a prescriptive plan** — deterministic math and pre-registered project criteria; thresholds remain benchmark-controlled.
- Historical migration counts: **HIGH for the Phase 1 snapshot** — preserved evidence; must be refreshed because runtime state can change.
- Security controls: **HIGH** — codebase boundaries plus official ASVS categories and adversarial verification design.

**Research date:** 2026-08-31  
**Valid until:** 2026-09-30 for architecture; re-check Chroma API/version and all runtime inventories immediately before implementation/migration.

## RESEARCH COMPLETE
