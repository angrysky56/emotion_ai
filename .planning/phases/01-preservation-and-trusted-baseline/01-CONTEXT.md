# Phase 1: Preservation and Trusted Baseline — Context

**Gathered:** 2026-08-19
**Status:** Ready for planning
**Source:** User direction plus evidence-based codebase map

<domain>
## Phase Boundary

Make the legacy system safe to change: preserve data, establish honest automated
signals, and contain the private local runtime. Do not redesign companion behavior,
migrate storage, delete artifacts, or rewrite Git history in this phase.
</domain>

<decisions>
## Implementation Decisions

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

### Claude's Discretion
- Inventory report schema and checksum algorithm.
- Which legacy scripts contain assertions worth migrating first.
- Exact temporary-directory structure for restore drills.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/codebase/CONCERNS.md` — ranked current risks and safe remediation order.
- `.planning/codebase/TESTING.md` — actual test validity and missing coverage.
- `.planning/codebase/ARCHITECTURE.md` — current entry points and data flows.
- `.planning/REQUIREMENTS.md` — phase requirement contracts.
- `aura_backend/database_protection.py` — current backup behavior under test.
- `aura_backend/main.py` — current filesystem and application boundary.
- `pyproject.toml` — deterministic test discovery and Python tool configuration.
</canonical_refs>

<specifics>
## Specific Ideas

- An inventory should be safe to commit: paths, roles, byte sizes, hashes, SQLite
  integrity/count summaries, and classification only—never message bodies.
- Restore tests must target temporary paths and never point writers at the originals.
- The trusted test command should stay short enough to run after every slice.
</specifics>

<deferred>
## Deferred Ideas

- Provider consolidation and Ornith quality evaluation: Phase 2.
- Storage migration and tracked-data removal: Phase 3 after the restore gate.
- Frontend redesign: Phase 5.
- Remote Git-history rewrite: Phase 6 with explicit approval.
</deferred>

---

*Phase: 01-preservation-and-trusted-baseline*
*Context gathered: 2026-08-19*
