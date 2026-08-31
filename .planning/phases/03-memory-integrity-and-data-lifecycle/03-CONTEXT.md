# Phase 3: Memory Integrity and Data Lifecycle - Context

**Gathered:** 2026-08-31  
**Status:** Ready for planning  
**Source:** Accepted affective-memory decisions and Ty's direction

<domain>
## Phase Boundary

Build one truthful, local, recoverable memory foundation. This phase owns the
append-only typed event ledger, provenance-bound derived memories, neutral hybrid
retrieval, backup/restore/export/deletion, bounded history access, and rebuildable
indexes. It exposes a tested seam for later affective reranking but does not
implement the Phase 4 emotional simulation.

</domain>

<decisions>
## Implementation Decisions

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

### Claude's Discretion
- Exact SQLite schema, repository/module names, migration staging, FTS tokenizer,
  deterministic score normalization, and plan decomposition, provided all locked
  contracts above are observable and tested.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture and safety
- `.planning/research/affective-memory/DECISION.md` — accepted storage, retrieval,
  archive, graph, and RLM disposition.
- `.planning/research/affective-memory/AFFECT-MEMORY-LOOP.md` — two-key retrieval
  gate, one-way evidence discipline, and Phase 4 seam.
- `.planning/research/affective-memory/KILL-CRITERIA.md` — fixed targets, controls,
  resource limit, and stopping condition.
- `.planning/research/affective-memory/FINDINGS.md` — append-only evidence and
  current-system audit.
- `.planning/research/affective-memory/CENTER.md` — competence floor and separation
  between memory, relationship, affect, task state, and values.

### Project contracts
- `.planning/REQUIREMENTS.md` — DATA-01 through DATA-06, DATA-09, TEST-03, PRES-04,
  and local/privacy constraints.
- `.planning/ROADMAP.md` — Phase 3 boundary and explicit Phase 4 deferrals.
- `.planning/phases/01-preservation-and-trusted-baseline/01-VERIFICATION.md` —
  preserved-root, backup, restore, and no-deletion baseline.
- `.planning/phases/02-provider-and-runtime-core/02-VERIFICATION.md` — current
  runtime/provider compatibility baseline.

</canonical_refs>

<specifics>
## Specific Ideas

- Preserve Aura's recognizable continuity while replacing the storage foundation
  behind stable interfaces.
- Prefer understandable local code over broad memory frameworks.
- Treat absence of feedback as unknown, not success.
- Keep full audit evidence on disk while user-facing results stay concise.

</specifics>

<deferred>
## Deferred Ideas

- Dynamic affective state, neurochemical/brainwave controls, relationship update,
  and post-response feedback belong to Phase 4.
- Graph-RLM reading, temporal graph projection, and Memvid performance adoption
  remain experimental candidates after the neutral baseline is valid.
- Frontend memory-management redesign belongs to Phase 5.

</deferred>

---

*Phase: 03-memory-integrity-and-data-lifecycle*  
*Context gathered: 2026-08-31 from accepted project decisions*
