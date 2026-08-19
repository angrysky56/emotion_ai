# Codebase Concerns

**Analysis Date:** 2026-08-19

## Assessment Scope and Confidence

- **Confirmed** means the behavior is directly visible in current source, Git metadata, or a command run during this audit.
- **Hypothesis** means the code creates a credible failure mode that requires a targeted reproduction before calling it an observed incident.
- Existing planning documents were not used as evidence. Current implementation, manifests, tests, tracked files, and user-facing documentation were inspected directly.
- No secret-bearing file contents were read. Environment-file existence is treated only as configuration evidence.

## Priority Summary

| Severity | Status | Concern | Primary evidence |
|---|---|---|---|
| Critical | Confirmed | No authentication or authorization protects private conversation, export, deletion, MCP, backup, or control endpoints | `aura_backend/main.py:2830`, `aura_backend/main.py:2849`, `aura_backend/main.py:3057`, `aura_backend/main.py:3113`, `aura_backend/main.py:3813`, `aura_backend/main.py:4150` |
| Critical | Confirmed | User-controlled identifiers are interpolated into filesystem paths without containment validation | `aura_backend/main.py:269`, `aura_backend/main.py:315`, `aura_backend/main.py:366` |
| High | Confirmed | Default server exposure and wildcard CORS enlarge the attack surface | `aura_backend/main.py:1345`, `aura_backend/main.py:1354`, `aura_backend/main.py:1370`, `aura_backend/main.py:4250` |
| High | Confirmed | Frontend renders untrusted Markdown/analysis through `innerHTML` without sanitization | `index.tsx:1124`, `index.tsx:1151`, `index.tsx:1689` |
| High | Confirmed | Repository tracks database artifacts and test/user data while local runtime data occupies gigabytes | `.gitignore:38`, `aura_chroma_db/chroma.sqlite3`, `auto_backups/`, `aura_backend/archive_unused/` |
| High | Confirmed | The advertised test command cannot finish collection | `aura_backend/tests/test_aura_parameter_fix.py:13`, `aura_backend/tests/test_aura_parameter_fix.py:22`, `README.md:410` |
| High | Confirmed | Backup implementation copies a live ChromaDB directory as ordinary files | `aura_backend/database_protection.py:79`, `aura_backend/database_protection.py:94` |
| Medium | Confirmed | Core modules are oversized and combine unrelated responsibilities | `aura_backend/main.py`, `index.tsx`, `aura_backend/conversation_persistence_service.py` |
| Medium | Confirmed | One global semaphore serializes database reads and writes | `aura_backend/conversation_persistence_service.py:118`, `aura_backend/conversation_persistence_service.py:1304` |
| Medium | Confirmed | Dependency footprint is unusually large and internally conflicting | `pyproject.toml:12`, `pyproject.toml:13`, `pyproject.toml:35` |
| Medium | Confirmed | Documentation claims controls and features that are absent or incomplete | `README.md:558`, `aura_backend/THINKING_GUIDE.md:167`, `aura_backend/main.py:328` |

## Tech Debt

**[Medium, Confirmed] Monolithic application modules:**
- Issue: API composition, lifecycle, provider calls, emotion analysis, persistence orchestration, administrative controls, and operational utilities coexist in the 4,256-line `aura_backend/main.py`. The browser UI is a 1,942-line manager in `index.tsx`; persistence is 1,908 lines in `aura_backend/conversation_persistence_service.py`.
- Files: `aura_backend/main.py`, `index.tsx`, `aura_backend/conversation_persistence_service.py`, `aura_backend/mcp_to_gemini_bridge.py`, `aura_backend/mcp_integration.py`
- Impact: Security boundaries are hard to see, changes have broad regression radius, import-time side effects complicate tests, and duplicated recovery paths can diverge.
- Fix approach: First capture endpoint contracts and persistence behavior with black-box tests. Then extract routers, request services, repository adapters, and UI features one vertical slice at a time; do not rewrite persistence and routing simultaneously.

**[Medium, Confirmed] Broad exception handling masks failure semantics:**
- Issue: Active modules repeatedly catch `Exception`, log a string, and return empty data or generic HTTP 500 responses. For example, profile loading turns corruption and permission failures into “missing profile” at `aura_backend/main.py:324`; history query failure becomes an empty history-shaped result at `aura_backend/conversation_persistence_service.py:1316`.
- Files: `aura_backend/main.py`, `aura_backend/conversation_persistence_service.py`, `aura_backend/aura_intelligent_memory_manager.py`, `aura_backend/enhanced_vector_db.py`, `aura_backend/mcp_integration.py`
- Impact: Data loss, corruption, transient provider errors, validation faults, and expected absence become indistinguishable. Callers may overwrite or continue from false empty state.
- Fix approach: Define typed domain errors and an API exception mapper. Preserve “not found,” “temporarily unavailable,” “corrupt,” and “unauthorized” as distinct statuses; add tests before changing fallback behavior.

**[Medium, Confirmed] Duplicate and legacy implementations remain importable:**
- Issue: Multiple vector database, memory, server, MCP, and Memvid implementations coexist, plus backups and “fixed” variants.
- Files: `aura_backend/robust_vector_db.py`, `aura_backend/enhanced_vector_db.py`, `aura_backend/aura_server.py`, `aura_backend/aura_as_mcp_server.py`, `aura_backend/archive_unused/`, `archive/index_backup.tsx`, `docs/main.py`
- Impact: Maintainers can patch the wrong implementation; pytest discovers archived tests; documentation and scripts reference obsolete layouts.
- Fix approach: Create an explicit runtime entry-point inventory, add import tests for only supported modules, exclude archives from discovery, then move immutable historical material outside the application package or package it as a release artifact.

## Known Bugs

**[High, Confirmed] Pytest collection aborts:**
- Symptoms: `.venv/bin/python -m pytest --collect-only -q` exits with code 3 after 17 collected tests and 11 errors. `aura_backend/tests/test_aura_parameter_fix.py` constructs the wrong import path and calls `sys.exit(1)` during module import.
- Files: `aura_backend/tests/test_aura_parameter_fix.py:13`, `aura_backend/tests/test_aura_parameter_fix.py:18`, `aura_backend/tests/test_aura_parameter_fix.py:22`, `aura_backend/archive_unused/test_*.py`, `aura_backend/scratch/test_memvid_v2.py`
- Trigger: Run pytest from the repository root.
- Workaround: None that provides a trustworthy full-suite result. Narrow file-by-file invocation bypasses collection failures but is not equivalent to a passing suite.

**[High, Confirmed] Export API does not export conversation data:**
- Symptoms: The endpoint reports success and a path, but the generated JSON contains empty `conversations`, `emotional_patterns`, and `cognitive_patterns` arrays. Non-JSON formats can return a path without writing a file.
- Files: `aura_backend/main.py:328`, `aura_backend/main.py:366`, `aura_backend/main.py:369`, `aura_backend/main.py:379`, `aura_backend/main.py:2830`
- Trigger: Call `POST /export/{user_id}` for a user with stored history, or request a format other than JSON.
- Workaround: Query history separately and preserve the backing database; do not treat the endpoint as a verified backup/export.

**[Medium, Confirmed] Frontend and backend disagree on export format transport:**
- Symptoms: The frontend posts `{format}` in the request body while the backend reads `format_type` as a query parameter. The frontend accepts JSON/CSV/HTML, while backend documentation advertises JSON/CSV/XML/YAML and only implements JSON.
- Files: `src/services/auraApi.ts:612`, `src/services/auraApi.ts:618`, `aura_backend/main.py:328`, `aura_backend/main.py:341`, `aura_backend/main.py:2831`
- Trigger: Select CSV or HTML export from the frontend.
- Workaround: Use JSON and verify file contents manually.

## Security Considerations

**[Critical, Confirmed] Missing identity, authentication, and authorization:**
- Risk: Any client that can reach the service can choose an arbitrary `user_id` to read private chat history and emotional analysis, delete sessions, request exports, execute MCP tools, inspect autonomic tasks, trigger backups/optimization, or stop/restart autonomous processing. A user name stored in browser local storage is an identifier, not proof of identity.
- Files: `aura_backend/main.py:2721`, `aura_backend/main.py:2830`, `aura_backend/main.py:2849`, `aura_backend/main.py:2965`, `aura_backend/main.py:3057`, `aura_backend/main.py:3113`, `aura_backend/main.py:3510`, `aura_backend/main.py:3813`, `aura_backend/main.py:3954`, `aura_backend/main.py:4024`, `aura_backend/main.py:4150`, `aura_backend/main.py:4211`, `index.tsx:169`
- Current mitigation: Database queries filter on the caller-supplied `user_id`; this scopes data but does not authenticate ownership.
- Recommendations: Bind to loopback immediately unless remote access is explicitly required. Add authenticated principals, derive user scope server-side, enforce per-route authorization, separate administrator capabilities, and add denial tests for cross-user access before exposing the service beyond localhost.

**[Critical, Confirmed] Filesystem path traversal through `user_id` and format:**
- Risk: `user_id` is inserted directly into profile and export filenames. Values containing path separators or traversal components can escape intended `users/` or `exports/` directories; the export extension is also caller-controlled.
- Files: `aura_backend/main.py:269`, `aura_backend/main.py:315`, `aura_backend/main.py:366`, `aura_backend/main.py:2831`
- Current mitigation: None visible in `AuraFileSystem`; docstrings claim validation, but no validation occurs before path construction.
- Recommendations: Stop using external identifiers as filenames. Map authenticated opaque IDs to storage keys; allowlist export formats; resolve paths and assert containment; use atomic create/write permissions; add traversal tests for encoded and platform-specific separators.

**[High, Confirmed] Unsafe default network and browser policy:**
- Risk: `DEV_MODE` defaults to true, which produces wildcard CORS with credentials enabled, and direct execution binds Uvicorn to all interfaces with reload enabled. The API has destructive and privileged routes.
- Files: `aura_backend/main.py:1345`, `aura_backend/main.py:1354`, `aura_backend/main.py:1356`, `aura_backend/main.py:1370`, `aura_backend/main.py:4250`, `aura_backend/main.py:4252`, `aura_backend/main.py:4254`, `aura_backend/start_api.sh:11`
- Current mitigation: Production-mode fallback origins are localhost-only, but production mode is not the default and there is no startup refusal for unsafe combinations.
- Recommendations: Default host to `127.0.0.1`, default development mode off, reject wildcard-plus-credentials, disable reload in the supported launcher, and require explicit configuration to expose a remote interface.

**[High, Confirmed] Stored/client-side XSS surface:**
- Risk: AI response text and thinking content are parsed as Markdown and assigned to `innerHTML`; emotional-analysis fields are also interpolated without consistent escaping. If the model, memory store, or upstream content emits HTML/event attributes, it can execute in the app origin.
- Files: `index.tsx:1124`, `index.tsx:1151`, `index.tsx:1689`, `index.tsx:1700`
- Current mitigation: Some history previews, search results, and recommendations use `escapeHtml`, but main messages and several analysis values do not.
- Recommendations: Sanitize parsed Markdown with a maintained allowlist sanitizer, disable raw HTML in Markdown where possible, use DOM nodes/`textContent` for scalar fields, add adversarial rendering tests, and deploy a restrictive Content Security Policy.

**[Medium, Confirmed] Internal errors are returned to clients:**
- Risk: Many endpoints use `HTTPException(..., detail=str(e))`, exposing provider, filesystem, database, and tool error details useful for reconnaissance and possibly containing sensitive context.
- Files: `aura_backend/main.py:2844`, `aura_backend/main.py:2960`, `aura_backend/main.py:3838`, `aura_backend/main.py:4206`, `aura_backend/main.py:4237`
- Current mitigation: Server-side logging exists, but client errors are not redacted.
- Recommendations: Return stable public error codes and correlation IDs; retain detailed exceptions only in access-controlled logs with content redaction.

## Privacy and Data Risks

**[Critical, Confirmed] Highly sensitive data has no enforced access boundary:**
- Risk: Conversations, emotional patterns, cognitive state, AI reasoning, profiles, and task results are retrievable by caller-selected IDs. These categories can reveal health, relationships, location, beliefs, and inferred mental state.
- Files: `aura_backend/main.py:1542`, `aura_backend/main.py:2721`, `aura_backend/main.py:2849`, `aura_backend/main.py:2965`, `aura_backend/main.py:3954`, `aura_backend/main.py:4115`
- Current mitigation: Local persistence and query filtering only.
- Recommendations: Treat all stored/inferred content as sensitive personal data. Add explicit consent, access control, retention/deletion semantics, encryption-at-rest strategy, and a tested complete export/delete workflow before multi-user or remote operation.

**[High, Confirmed] Sensitive conversation material is logged in the browser:**
- Risk: User identifiers, search queries, request objects, responses, thinking content/metrics, and chat history responses are written to developer-console logs, which extensions, shared-device users, or support captures may expose.
- Files: `index.tsx:297`, `index.tsx:898`, `index.tsx:919`, `index.tsx:923`, `index.tsx:1004`, `index.tsx:1107`, `index.tsx:1357`
- Current mitigation: None beyond the browser's normal console boundary.
- Recommendations: Remove content-bearing logs from production builds; log only event codes and opaque correlation IDs; add a redaction utility and a build-time production logger policy.

**[Medium, Confirmed] Retention and deletion are partial and ambiguous:**
- Risk: Deleting an active chat session does not establish erasure across exports, automatic backups, Memvid archives, logs, provider history, or historical database copies. Backup retention is based on ten directories, not privacy policy.
- Files: `aura_backend/main.py:3057`, `aura_backend/main.py:3510`, `aura_backend/database_protection.py:99`, `aura_backend/memvid_archival_service.py`, `aura_backend/aura_data/`, `aura_backend/auto_backups/`, `aura_backend/chromadb_backups/`
- Current mitigation: Session-level ChromaDB deletion and local backup rotation.
- Recommendations: Document every data copy, define retention by data category, implement a deletion ledger/tombstone propagation across stores, and verify deletion against a temporary end-to-end fixture.

## Database and Git Hygiene

**[High, Confirmed] Runtime and historical database artifacts are tracked:**
- Issue: Git tracks active/root Chroma SQLite data, ten root backup databases, a 16.76 MB test vector segment, corrupted/archive Chroma segments, WAL/SHM files, and a sample user profile. The working tree is approximately 7.4 GB while tracked files total about 40 MB.
- Files: `aura_chroma_db/chroma.sqlite3`, `auto_backups/`, `aura_backend/tests/test_aura_chroma_db/`, `aura_backend/archive_unused/aura_chroma_db_corrupted_20250620_160946/`, `aura_backend/aura_data/users/test_user.json`, `.gitignore:38`
- Impact: Personal or derived data can enter history, clones are heavier, binary churn obscures review, and stale WAL/SHM snapshots are not reliable portable backups.
- Fix approach: Preservation first: inventory and checksum every database/archive, create an offline verified backup outside Git, prove restore and record counts, classify personal data, then remove runtime artifacts from tracking and expand ignore rules. Never begin with bulk deletion.

**[High, Confirmed] Ignore rules cover only one of several runtime roots:**
- Issue: `.gitignore` excludes `aura_backend/aura_chroma_db/` and backend user JSON, but not root `aura_chroma_db/`, root `auto_backups/`, backend backup descendants, exports, sessions, test databases, `.venv/`, or generic SQLite/WAL/SHM artifacts.
- Files: `.gitignore:26`, `.gitignore:38`, `aura_chroma_db/`, `auto_backups/`, `aura_backend/auto_backups/`, `aura_backend/chromadb_backups/`, `aura_backend/aura_data/exports/`, `.venv/`
- Impact: Accidental commits and workspace bloat remain likely.
- Fix approach: After preservation and classification, add explicit runtime-root rules plus safe placeholder exceptions; add a pre-commit secret/data-size check and CI assertion that no database artifacts are newly tracked.

**[High, Hypothesis] Live filesystem backups may be inconsistent:**
- Problem: The protection thread calls `shutil.copytree` on the live Chroma directory without an application-wide write barrier, SQLite backup API, or checkpoint/snapshot protocol.
- Files: `aura_backend/database_protection.py:47`, `aura_backend/database_protection.py:64`, `aura_backend/database_protection.py:79`, `aura_backend/database_protection.py:94`
- Cause: Concurrent SQLite/Chroma writes can span multiple files while the copy is in progress.
- Improvement path: Before changing the backup mechanism, run restore drills against representative snapshots and record collection counts/hashes. Then use Chroma-supported export/snapshot semantics or SQLite's online backup API under a coordinated quiescence boundary.

## Performance Bottlenecks

**[Medium, Confirmed] Read traffic is serialized behind writes:**
- Problem: A single `asyncio.Semaphore(1)` protects persistence and chat-history retrieval, and retrieval deliberately sleeps before querying.
- Files: `aura_backend/conversation_persistence_service.py:118`, `aura_backend/conversation_persistence_service.py:1304`, `aura_backend/conversation_persistence_service.py:1307`
- Cause: A process-local global lock substitutes for a database concurrency contract.
- Improvement path: Measure p50/p95 latency and corruption rate first. Separate read and write paths only after database-version-specific concurrency behavior is covered by stress and multi-process tests.

**[Medium, Confirmed] Oversized history defaults and payloads:**
- Problem: Chat history defaults to 5,000 records/sessions, materializes messages in Python, and includes previews up to 10,000 characters despite documentation claiming 50 sessions and 100-character previews.
- Files: `aura_backend/main.py:2850`, `aura_backend/main.py:2861`, `aura_backend/main.py:2940`, `aura_backend/conversation_persistence_service.py:1295`
- Cause: No bounded pagination contract; limits and documentation have drifted.
- Improvement path: Add cursor pagination with a conservative server maximum, return summaries without full message arrays, and benchmark representative large histories.

**[Medium, Confirmed] Backup amplification and disk growth:**
- Problem: Startup creates a full initial copy; a daemon can create further full copies; multiple backup roots and historical snapshots coexist. The repository working directory is approximately 7.4 GB.
- Files: `aura_backend/database_protection.py:47`, `aura_backend/database_protection.py:50`, `aura_backend/database_protection.py:62`, `aura_backend/auto_backups/`, `aura_backend/chromadb_backups/`, `auto_backups/`
- Cause: Full-directory copying and fragmented backup ownership.
- Improvement path: Consolidate backup ownership after a restore audit; use deduplicated/versioned backups, quotas, low-disk alerts, and documented retention.

## Fragile Areas

**Persistence and recovery pipeline:**
- Files: `aura_backend/conversation_persistence_service.py`, `aura_backend/robust_vector_db.py`, `aura_backend/enhanced_vector_db.py`, `aura_backend/database_protection.py`, `aura_backend/scripts/recover_chromadb.py`
- Why fragile: Multiple retry, emergency persistence, backup, cleanup, lock, and recovery mechanisms overlap. Some paths convert failure into empty results, and historical corruption artifacts show the data format has required repair work.
- Safe modification: Freeze representative databases; capture counts, metadata schemas, ordering, deduplication behavior, and failure responses; test restore in a temporary directory; change one ownership boundary at a time.
- Test coverage: Full pytest collection is broken, archived tests are discovered, and several “tests” return booleans or run as scripts rather than making reliable assertions.

**Provider/MCP execution boundary:**
- Files: `aura_backend/mcp_integration.py`, `aura_backend/mcp_to_gemini_bridge.py`, `aura_backend/mcp_client.py`, `aura_backend/main.py:3113`
- Why fragile: Subprocess lifecycle, inherited environment, model-produced tool arguments, retries, and unauthenticated HTTP execution meet at one boundary.
- Safe modification: Record sanitized tool schemas and golden request/response/error fixtures; enforce tool allowlists, argument schemas, timeouts, output caps, and per-principal authorization before refactoring subprocess management.
- Test coverage: Collection failure prevents a repository-wide signal; many MCP tests depend on ambient services or script-style execution.

**Browser rendering and session state:**
- Files: `index.tsx`, `src/services/auraApi.ts`
- Why fragile: Large mutable class state, direct DOM manipulation, inline event handlers, local-storage identity, retry behavior, and unsanitized Markdown are tightly coupled.
- Safe modification: Add browser-level tests for message rendering, identity switching, cross-session deletion, offline retries, and malicious HTML before component extraction.
- Test coverage: `package.json` has no frontend test command or browser/E2E framework.

## Scaling Limits

**Single-process in-memory state:**
- Current capacity: Not benchmarked or enforced. Active chat sessions, provider objects, MCP clients, and autonomic state are process globals in `aura_backend/main.py`.
- Limit: Multiple Uvicorn workers or replicas will hold divergent session/task state; process-local semaphores do not coordinate database access across processes.
- Scaling path: Keep a single supported process until behavior is measured; externalize coordination and task state, introduce stable request IDs/idempotency, then test multi-process database safety.

**Autonomic work queue and remote calls:**
- Current capacity: Defaults include up to 30 concurrent tasks, a queue size of 40, and remote-call limits configured from environment in `aura_backend/aura_autonomic_system.py:938`.
- Limit: Unauthenticated submission/control can consume provider quota and local resources; maximum output-token defaults are very large in `aura_backend/aura_autonomic_system.py:941` and `aura_backend/thinking_processor.py:709`.
- Scaling path: Authenticate first, impose per-user/global budgets and backpressure, persist task ownership, and measure cost/latency before increasing concurrency.

## Dependencies at Risk

**FAISS CPU and GPU installed together:**
- Risk: `faiss-cpu` and `faiss-gpu-cu12` are both direct dependencies, increasing install size and creating overlapping module/provider ambiguity. `torch==2.11.0` plus CUDA transitive packages makes the environment hardware-specific and heavy.
- Impact: Slow, fragile installs; unnecessary GPU dependencies for CPU deployments; harder reproducibility across developer, CI, and container environments.
- Migration plan: Establish CPU and CUDA optional dependency groups with separate lock/CI lanes; retain one FAISS provider per environment; prove identical retrieval contracts on a fixture before switching.
- Files: `pyproject.toml:12`, `pyproject.toml:13`, `pyproject.toml:35`, `requirements.txt:99`, `requirements.txt:101`

**Unbounded direct dependency ranges:**
- Risk: Most direct Python dependencies use lower bounds only. `uv.lock` and `requirements.txt` pin current resolution, but updating either can introduce major behavior changes across FastAPI, ChromaDB, MCP, provider, ML, and media stacks at once.
- Impact: A broad re-lock has high regression potential, especially without a collecting test suite.
- Migration plan: Repair tests first; document supported upgrade windows; group upgrades by subsystem; run persistence restore, API contract, MCP, and model-provider tests for each group.
- Files: `pyproject.toml`, `uv.lock`, `requirements.txt`

## Missing Critical Features

**Enforced security baseline:**
- Problem: Authentication, authorization, rate limiting, secure transport termination, and admin separation are absent from current application code despite documentation claims.
- Blocks: Safe LAN/Internet exposure, credible multi-user privacy, and production deployment.
- Files: `aura_backend/main.py`, `README.md:558`

**Verified data lifecycle:**
- Problem: Complete export, delete-across-copies, retention, consent, and restore verification are not implemented as one auditable workflow.
- Blocks: Trustworthy portability, privacy requests, and safe database cleanup/refactoring.
- Files: `aura_backend/main.py:328`, `aura_backend/main.py:2830`, `aura_backend/main.py:3057`, `aura_backend/database_protection.py`, `aura_backend/memvid_archival_service.py`

**Operational guardrails:**
- Problem: No visible application-level rate limiter, request/body cap policy, admin authentication, disk quota alert, structured redaction policy, or production startup validation.
- Blocks: Resilient unattended operation and safe expensive-tool/model access.
- Files: `aura_backend/main.py`, `aura_backend/aura_autonomic_system.py`, `aura_backend/mcp_integration.py`

## Test Coverage Gaps

**Security and privacy boundaries — High:**
- What's not tested: Authentication denial, cross-user reads/deletes, traversal payloads, admin endpoint access, CORS policy, XSS payloads, rate/cost abuse, and data redaction.
- Files: `aura_backend/main.py`, `index.tsx`, `src/services/auraApi.ts`
- Risk: Critical vulnerabilities remain invisible to the current suite.
- Priority: High

**Persistence preservation and restoration — High:**
- What's not tested: Restoring a copied live database, completeness across collections/backups/Memvid, power-loss behavior, multi-process access, and end-to-end delete/export.
- Files: `aura_backend/database_protection.py`, `aura_backend/conversation_persistence_service.py`, `aura_backend/robust_vector_db.py`, `aura_backend/scripts/recover_chromadb.py`
- Risk: A cleanup or refactor can silently lose irreplaceable conversation history.
- Priority: High

**Test harness integrity — High:**
- What's not tested: The suite itself is not gated by successful collection; archive and scratch files are included; some test functions return status booleans instead of asserting; import-time `sys.exit` aborts pytest.
- Files: `aura_backend/tests/test_aura_parameter_fix.py`, `aura_backend/tests/test_vector_db.py`, `aura_backend/archive_unused/test_*.py`, `aura_backend/scratch/test_memvid_v2.py`
- Risk: Partial output can be mistaken for validation, and regressions can ship without a trustworthy pass/fail signal.
- Priority: High

**Frontend behavior — Medium:**
- What's not tested: DOM rendering, sanitized Markdown, session switching, retry/idempotency, accessibility, and browser/API integration.
- Files: `index.tsx`, `src/services/auraApi.ts`, `package.json`
- Risk: Privacy, XSS, duplication, and user-state regressions are found manually.
- Priority: Medium

## Documentation Drift

**[High, Confirmed] Security claims exceed implementation:**
- Drift: README claims API-key authentication, rate limiting, encrypted transit, anonymized embeddings, and input sanitization. No authentication or rate-limiting middleware is present; the documented URLs and frontend client use HTTP; stored metadata is keyed by user identifiers; Markdown is unsanitized.
- Files: `README.md:558`, `README.md:562`, `README.md:565`, `README.md:569`, `README.md:572`, `aura_backend/main.py:1337`, `src/services/auraApi.ts:154`, `index.tsx:1151`
- Action: Mark unimplemented controls as roadmap items immediately; only restore claims after executable verification.

**[Medium, Confirmed] Testing instructions are not executable as written:**
- Drift: README says `pytest tests/` from a repository layout where tests live under `aura_backend/tests/`; the thinking guide references test files that do not exist in the active tests directory.
- Files: `README.md:410`, `aura_backend/THINKING_GUIDE.md:195`, `aura_backend/THINKING_GUIDE.md:206`, `aura_backend/tests/`
- Action: Publish one canonical root-level command only after collection and environment markers are repaired.

**[Medium, Confirmed] Privacy controls are described but not implemented:**
- Drift: The thinking guide states user-controlled retention, consent, opt-out, secure transmission, and export of reasoning patterns; current export returns empty placeholders and no consent/retention interface was found.
- Files: `aura_backend/THINKING_GUIDE.md:167`, `aura_backend/THINKING_GUIDE.md:170`, `aura_backend/THINKING_GUIDE.md:176`, `aura_backend/THINKING_GUIDE.md:179`, `aura_backend/main.py:369`
- Action: Relabel as planned work and define testable acceptance criteria.

## Safe Remediation Order

1. **Contain exposure without touching data:** bind the supported launcher to loopback, disable wildcard CORS/reload defaults, and block unauthenticated administrative/MCP endpoints.
2. **Capture behavior and provenance:** inventory active entry points and every storage/backup root; record sizes, checksums, Chroma collection counts, metadata schemas, representative API responses, and known failure outputs. Store sanitized evidence outside mutable databases.
3. **Prove preservation:** create an offline backup outside Git, restore into a temporary isolated directory, compare record counts/hashes/search fixtures, and document rollback. Do not delete or migrate any database before this gate passes.
4. **Repair the test signal:** constrain pytest discovery to active tests, remove import-time exits, convert boolean/script checks to assertions, classify live-service/model/GPU tests, and make collection itself a CI gate.
5. **Close critical boundaries:** implement authenticated principals, server-derived ownership, admin roles, path containment/opaque storage keys, format allowlists, request limits, and redacted errors/logging.
6. **Fix browser trust boundaries:** sanitize Markdown, escape all analysis fields, remove sensitive production console logging, and add CSP plus adversarial browser tests.
7. **Make data lifecycle real:** implement and verify complete export, retention, deletion propagation, backup policy, and consent/opt-out across Chroma, profiles, Memvid, exports, logs, and backups.
8. **Rationalize Git/runtime data:** only after verified external backup, stop tracking database artifacts, expand ignore rules, add size/secret/data checks, and separate immutable fixtures from personal runtime state.
9. **Refactor incrementally:** extract routers/services/repositories and frontend components behind preserved contract tests; consolidate duplicate implementations and backup ownership one slice at a time.
10. **Optimize last:** benchmark lock contention, history payloads, backup amplification, model cost, and dependency variants; change concurrency or storage strategy only against measured baselines and restore-tested fixtures.

---

*Concerns audit: 2026-08-19*
