# Requirements: Aura Rehabilitation

## Preservation and Evidence

- **PRES-01 [MUST]** Inventory every active, backup, test, and archived data root
  without exposing conversation content.
- **PRES-02 [MUST]** Create an offline backup outside Git and prove restoration into
  an isolated temporary location before any data deletion or migration.
- **PRES-03 [MUST]** Capture representative API, persistence, and companion behavior
  as characterization tests before changing those behaviors.
- **PRES-04 [MUST]** Keep generated databases, backups, exports, profiles, logs, and
  secrets out of new Git commits.

## Trustworthy Engineering Signal

- **TEST-01 [MUST]** One root command must collect and run deterministic tests with
  unambiguous pass/fail semantics.
- **TEST-02 [MUST]** Legacy diagnostics must be classified as tests, live checks,
  migration tools, or archives; scripts that print/return booleans are not tests.
- **TEST-03 [MUST]** Backend API contracts, filesystem containment, persistence,
  provider translation, and failure behavior require automated tests.
- **TEST-04 [MUST]** Frontend state, sanitized rendering, API behavior, and primary
  user flows require automated unit/component and browser-level coverage.
- **TEST-05 [MUST]** CI must separately report deterministic tests, optional live
  Ollama checks, builds, linting, typing, and environment-blocked checks.

## Private Local Runtime

- **LOCAL-01 [MUST]** Aura binds to loopback by default and permits LAN exposure only
  through explicit configuration.
- **LOCAL-02 [MUST]** Browser origins are explicit; wildcard CORS is rejected and
  strict JSON content handling remains enabled.
- **LOCAL-03 [MUST]** Caller-controlled identifiers and formats cannot escape Aura's
  data directories or produce unwritten exports.
- **LOCAL-04 [MUST]** Aura requires no user account or sign-in for normal local use.
- **LOCAL-05 [SHOULD]** Logs and UI diagnostics avoid conversation content and other
  sensitive material by default.

## Model and Companion Behavior

- **AI-01 [MUST]** A small typed provider contract supports Ollama, Gemini, and
  OpenRouter without provider-specific logic in conversation orchestration.
- **AI-02 [MUST]** Ollama works locally through its supported OpenAI-compatible or
  native API with explicit timeouts, cancellation, streaming, and error mapping.
- **AI-03 [MUST]** Deterministic provider fakes cover normal, streaming, malformed,
  timeout, and unavailable-model behavior; live Ornith tests are optional and marked.
- **AI-04 [MUST]** Emotional and reflective outputs state uncertainty and are tested
  for stable schema and user-visible usefulness rather than unverifiable psychology.
- **AI-05 [MUST]** Raw hidden chain-of-thought is neither required nor exposed;
  concise user-facing reflection summaries may be produced as normal output.
- **AI-06 [SHOULD]** Provider/model quality is compared using a small versioned local
  evaluation set with latency and failure evidence, not anecdote alone.
- **AI-07 [MUST]** Aura has a versioned, bounded affective-state contract with
  deterministic decay/homeostasis and pre-response event updates that measurably
  modulate response policy and memory formation. Named brainwave/neurochemical
  channels are explicitly simulated controls, not claims about human biology.
- **AI-08 [MUST]** Post-response self-feedback uses observable contract checks and
  later explicit user feedback to update future state without storing or exposing
  hidden chain-of-thought. Its contribution is tested against a mechanism-removed
  control.
- **AI-09 [MUST]** Aura has a versioned center separating immutable values,
  slow temperament and relationship state, fast affect, task state, and memory.
  User hostility may change warmth, openness, trust, initiative, and boundaries,
  but cannot reduce factual/tool competence, truthfulness, privacy, safety, or
  recovery toward baseline.

## Memory and Data Lifecycle

- **DATA-01 [MUST]** One documented storage owner controls conversation persistence,
  vector indexing, backups, restore, export, retention, and deletion boundaries.
- **DATA-02 [MUST]** Backups use a consistent snapshot/export mechanism and are
  restore-tested with record counts and retrieval fixtures.
- **DATA-03 [MUST]** Export returns actual stored data in every advertised format;
  unsupported formats are rejected clearly.
- **DATA-04 [MUST]** Deletion semantics enumerate and verify all affected active
  stores, exports, caches, archives, and backups.
- **DATA-05 [SHOULD]** Memory retrieval has bounded pagination and measured relevance,
  latency, and duplicate behavior.
- **DATA-06 [MUST]** Immutable conversation events are distinguishable from lossy
  derived facts, preferences, episodes, and relationships; every derived memory
  retains source provenance and explicit supersession/update state.
- **DATA-07 [MUST]** Affective salience may change consolidation and provide a
  bounded retrieval boost, but factual relevance remains dominant. The dynamic
  gate must be evaluated against a constant-salience control for recall, stale
  facts, abstention, and cross-user leakage.
- **DATA-08 [MUST]** Relationship events preserve target, appraisal uncertainty,
  before/after state, task outcome, repair, and source provenance. Derived trust
  or relationship beliefs change slowly, remain supersedable, and cannot be
  rewritten by one prompt or model summary.

## Architecture and Experience

- **ARCH-01 [MUST]** Backend routes, application services, provider adapters, and
  repositories have explicit boundaries and no model/database initialization at
  import time.
- **ARCH-02 [MUST]** Duplicate active implementations are consolidated only after
  supported entry points and behavior are pinned.
- **ARCH-03 [MUST]** Frontend UI, state, rendering, and API access are separated into
  maintainable modules while preserving the recognizable Aura experience.
- **ARCH-04 [MUST]** Model-generated Markdown and scalar analysis fields are rendered
  through a maintained sanitization boundary.
- **ARCH-05 [SHOULD]** Accessibility and responsive behavior meet WCAG 2.2 AA for the
  primary conversation, history, settings, and error flows.

## Operations, Performance, and Release

- **OPS-01 [MUST]** One cross-platform documented startup path performs dependency,
  model, port, storage, and health preflight checks without installing software via
  an opaque startup side effect.
- **OPS-02 [MUST]** Python and Node dependency manifests have one authoritative lock
  path each; GPU-only and optional capabilities do not burden the base install.
- **OPS-03 [MUST]** README, API documentation, examples, and `.planning` claims match
  executable behavior and name incomplete work honestly.
- **PERF-01 [SHOULD]** Record startup time, response latency, memory, disk growth,
  backup cost, and dependency size before and after optimization.
- **PERF-02 [SHOULD]** Remove serialization, locking, payload, rendering, and model-call
  bottlenecks only when a reproducible benchmark demonstrates improvement.
- **GIT-01 [MUST]** Remove runtime data and obsolete generated artifacts from the
  current tracked tree after the restore gate passes.
- **GIT-02 [COULD]** Rewrite remote Git history only after a dry run, size report,
  preserved tag/branch plan, and Ty's explicit approval.
