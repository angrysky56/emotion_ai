# Phase 2: Provider and Runtime Core — Context

**Gathered:** 2026-08-19
**Status:** Ready for planning
**Source:** Project decisions, Phase 1 characterization, and Ty's autonomous-refactor authorization

<domain>
## Phase Boundary

Deliver one typed, testable conversation-provider boundary for Ollama, Gemini, and
OpenRouter; make local Ollama a complete first-class path; remove heavyweight
provider/runtime initialization from import time; establish truthful startup,
health, dependency, and CI lanes. Preserve the characterized companion response
and persistence contracts. Storage ownership, memory migration, and frontend
restructuring remain later phases.

</domain>

<decisions>
## Implementation Decisions

### D-01 — Local-first provider behavior
- Ollama is a complete first-class provider, not a fallback demo.
- `ornith:latest` is the preferred bounded live-test model when installed, but no
  deterministic test may require Ollama or any network service.
- Cloud providers remain supported when explicitly configured; Aura must have no
  silent cloud dependency.

### D-02 — Provider contract and failures
- Conversation orchestration consumes one small typed provider interface and must
  not branch on provider names or SDK response types.
- Normal, streamed, malformed, timeout, cancellation, missing-model, unavailable-
  service, and provider-auth failures require distinct typed outcomes.
- Resource limits, unavailable services, malformed output, and partial streams may
  not be reported as successful completed answers.
- Raw provider exceptions, credentials, prompts, and conversation content must not
  leak through public health/error responses or default logs.

### D-03 — Streaming and cancellation
- Streaming is a real incremental contract with deterministic fake coverage; it
  must not be implemented by buffering a full response and replaying chunks.
- Client cancellation and shutdown must stop provider work promptly and clean up
  sessions/resources without converting cancellation into a fallback success.
- The existing non-streaming conversation path remains functional throughout the
  refactor.

### D-04 — Runtime lifecycle
- Importing `aura_backend.main` or provider modules must not construct model clients,
  connect to services, scan/download models, start subprocesses, or open databases.
- One explicit application/runtime factory owns initialization and shutdown.
- Health distinguishes process liveness, application readiness, and optional
  provider availability; an unavailable optional cloud provider must not make a
  valid local-only runtime dishonest.
- Aura remains loopback-first with no mandatory sign-in.

### D-05 — Startup and dependencies
- Provide one documented cross-platform startup/preflight entry point; it reports
  missing dependencies, occupied port, unwritable storage, and unavailable selected
  model with actionable redacted messages and never installs software implicitly.
- `pyproject.toml` plus `uv.lock` are the authoritative Python dependency path;
  `package.json` plus its lockfile are authoritative for Node.
- GPU-heavy and optional provider/tool capabilities belong in explicit optional
  groups and may not burden the base local runtime without evidence they are needed.
- Reconcile manifests against actual imports before removing or moving dependencies;
  do not perform broad speculative upgrades in this phase.

### D-06 — Verification lanes
- The root deterministic suite uses provider fakes and stays offline.
- Live Ollama/Ornith checks are explicitly marked, bounded by timeouts, skip with a
  truthful environment reason when unavailable, and report failures separately.
- CI/reporting must keep deterministic tests, live-model checks, lint, typing,
  frontend build, and environment-blocked lanes distinct.
- Performance claims require captured startup and provider-latency measurements;
  this phase may record baselines but must not claim optimization from anecdotes.

### Claude's Discretion
- Exact module names and class decomposition inside the provider/runtime boundary.
- Whether the Ollama adapter uses the native API or supported OpenAI-compatible API,
  based on current official behavior and the cleanest streaming/cancellation contract.
- Exact CLI framework and health payload field names, provided the contracts above
  are typed, tested, and documented.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product and requirements
- `.planning/PROJECT.md` — fixed local/private product decisions and definition of done.
- `.planning/REQUIREMENTS.md` — TEST-03, TEST-05, AI-01 through AI-03, OPS-01, OPS-02.
- `.planning/ROADMAP.md` — Phase 2 boundary and dependencies.

### Verified Phase 1 contracts
- `.planning/phases/01-preservation-and-trusted-baseline/01-VERIFICATION.md` — trusted baseline and deferred boundaries.
- `.planning/phases/01-preservation-and-trusted-baseline/01-05-SUMMARY.md` — localhost/no-sign-in behavior.
- `.planning/phases/01-preservation-and-trusted-baseline/01-07-SUMMARY.md` — current companion/persistence response and fallback behavior.

### Current architecture evidence
- `.planning/codebase/ARCHITECTURE.md` — provider and lifecycle call paths.
- `.planning/codebase/INTEGRATIONS.md` — current SDKs, settings, and provider integrations.
- `.planning/codebase/TESTING.md` — current provider/runtime test gaps.
- `.planning/codebase/CONCERNS.md` — monolith, initialization, dependency, and error risks.

</canonical_refs>

<specifics>
## Specific Ideas

- Use the locally installed `ornith:latest` only for marked live evidence.
- Keep Aura runnable after every plan; provider consolidation must be incremental and
  retain a rollback point.
- Prefer clear user-facing failure categories over broad HTTP 200 fallback behavior,
  but treat any intentional API behavior change as an explicit tested decision.

</specifics>

<deferred>
## Deferred Ideas

- Chroma root ownership, FK repair, storage consolidation, export, deletion, and
  tracked-data removal are Phase 3.
- Emotion/reflection quality evaluation and prompt redesign are Phase 4.
- Frontend modularization and browser experience are Phase 5.
- Broad performance optimization and final packaging are Phase 6.
- Remote Git-history rewriting remains separately approved and out of scope.

</deferred>

---

*Phase: 02-provider-and-runtime-core*
*Context gathered: 2026-08-19*
