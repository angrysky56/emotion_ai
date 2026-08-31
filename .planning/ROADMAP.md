# Roadmap: Aura Rehabilitation

## Phase 1: Preservation and Trusted Baseline

**Goal:** Make Aura safe to change without losing data or mistaking scripts for tests.
**Requirements:** PRES-01, PRES-02, PRES-03, PRES-04, TEST-01, TEST-02,
LOCAL-01, LOCAL-02, LOCAL-03, LOCAL-04
**Status:** Complete

- Inventory and checksum data roots without reading personal content.
- Prove an isolated restore before migration or deletion.
- Establish deterministic pytest discovery and classify legacy checks.
- Capture filesystem, startup, CORS, and current core API behavior.

**Execution plan:**

- Wave 1: 01-01 metadata inventory, 01-03 test truth, 01-05 local API boundary.
- Wave 2 *(blocked on Wave 1)*: 01-02 preservation CLI contract, 01-04 legacy
  characterization migration, 01-06 filesystem contract, 01-07 companion contract.
- Wave 3 *(blocked on Wave 2)*: 01-08 repository inventory and safe evidence.
- Wave 4 *(blocked on Wave 3)*: 01-09 quiescence preflight and explicit checkpoint.
- Wave 5 *(blocked on checkpoint approval)*: 01-10 real backup and isolated restore.

**Cross-cutting constraints:** no personal content in committable evidence; originals
remain immutable; no Chroma client opens originals; deterministic tests require no
live model/service; existing FK anomalies require exact source/restore parity; no
deletion, migration, tracked-data removal, sign-in, or Git-history rewrite.

## Phase 2: Provider and Runtime Core

**Goal:** Deliver one reliable conversation path through Ollama and the existing
cloud providers behind a typed, testable runtime boundary.
**Depends on:** Phase 1
**Requirements:** TEST-03, TEST-05, AI-01, AI-02, AI-03, OPS-01, OPS-02

**Wave 1:** 02-01 typed provider contract; 02-14 package-legitimacy evidence.

**Wave 2** *(blocked on Wave 1):* 02-02 deterministic provider runtime/fakes;
02-03 neutral tool boundary; 02-15 package-legitimacy approval checkpoint.

**Waves 3–4** *(blocked on provider contracts):* 02-04 Ollama/OpenRouter shared
transport; 02-05 async Gemini; 02-06 local-first factory/autonomic integration.

**Waves 5–9** *(blocked on adapters):* 02-07 application runtime; 02-08
import-safe FastAPI lifespan; 02-09 provider-neutral conversation path; 02-10
honest health; 02-11 canonical non-mutating preflight/serve CLI.

**Waves 10–11** *(blocked on runtime and package approval):* 02-12 launcher
delegation; 02-16 Python dependency authority; 02-13 startup documentation;
02-17 Node dependency and typing authority.

**Wave 12** *(final gate):* 02-18 optional bounded Ornith evidence, performance
baselines, and independent CI truth lanes.

Cross-cutting constraints: preserve Phase 1's seven-field response, HTTP-200
provider fallback, persistence/session behavior, loopback/no-sign-in boundary, and
offline deterministic suite; partial, cancelled, malformed, unavailable, blocked,
or resource-limited provider work cannot become completed success; no package or
lock mutation before Plan 02-15 approval; no storage migration/deletion, broad
upgrade, prompt-quality redesign, frontend refactor, or Git-history rewrite.

## Phase 3: Memory Integrity and Data Lifecycle

**Goal:** Make conversation memory, backup, restore, export, and deletion truthful
and recoverable through one storage boundary.
**Depends on:** Phase 1, Phase 2
**Requirements:** TEST-03, DATA-01, DATA-02, DATA-03, DATA-04, DATA-05,
DATA-06, PRES-04

- Characterize and consolidate active persistence implementations.
- Establish one append-only typed event ledger as the source of truth; keep
  derived memories provenance-bound and explicitly supersedable.
- Treat lexical/vector/graph indexes as rebuildable projections, with SQLite
  full-text plus existing Chroma as the initial hybrid retrieval baseline.
- Replace live-directory copying with a verified snapshot strategy.
- Implement complete export/deletion behavior and bounded history retrieval.
- Keep Memvid v2 copy-only and optional until it beats the baseline for portable
  cold archival; never let archive creation delete active records.
- Remove tracked runtime data only after restore verification passes.

## Phase 4: Reflective Companion Core

**Goal:** Preserve and sharpen Aura's emotionally perceptive, reflective behavior
with explicit uncertainty and measurable model/provider behavior.
**Depends on:** Phase 2, Phase 3
**Requirements:** PRES-03, AI-04, AI-05, AI-06, AI-07, AI-08, AI-09,
DATA-07, DATA-08, ARCH-01, ARCH-02

- Define versioned conversation, emotional-state, and reflection contracts.
- Replace the fixed emotion lookup with a bounded time-evolving affective state:
  appraisal, pre-response update, decay/homeostasis, response modulation,
  post-response self-feedback, and persisted snapshots.
- Implement Aura's versioned center: immutable values and competence floor,
  slow temperament/relationship state, fast affect, per-task state, clear
  boundaries, and a tested repair path. Hostility may reduce relational openness
  but never sabotage tools or make truth conditional on politeness.
- Make simulated neurochemical channels and mixed brainwave controls causally
  affect behavior, encoding, consolidation, and capped retrieval salience while
  stating clearly that they are computational analogies rather than measured EEG
  or literal biology.
- Separate orchestration from providers, memory, MCP, and autonomic processing.
- Build a small sanitized evaluation corpus covering useful emotional response,
  state trajectories, knowledge updates, abstention, implicit personal
  constraints, paired polite/hostile task equivalence, rupture/repair, center
  capture attempts, and the constant-salience/mechanism-removed controls.
- Retain useful reflection summaries without exposing hidden chain-of-thought.
- Keep Graph-RLM/RLM reading and temporal graph projection optional until a
  multi-hop or over-context evaluation demonstrates a material gain.

## Phase 5: API and Frontend Rehabilitation

**Goal:** Provide a maintainable, accessible, safe interface for the complete local
companion workflow without losing Aura's recognizable character.
**Depends on:** Phase 3, Phase 4
**Requirements:** TEST-04, LOCAL-05, ARCH-03, ARCH-04, ARCH-05

- Split the TypeScript god object by feature and state boundary.
- Sanitize all model/memory rendering and remove sensitive production logging.
- Add unit/component and browser tests for conversation, history, settings, and
  failures.
- Refine responsive design and accessibility using the preserved product spirit.

## Phase 6: Performance, Packaging, and Honest Release

**Goal:** Ship a reproducible local application whose performance and documentation
are supported by current evidence.
**Depends on:** Phase 1 through Phase 5
**Requirements:** OPS-03, PERF-01, PERF-02, GIT-01, GIT-02

- Benchmark and optimize measured bottlenecks on the target RTX 3060 system.
- Package a clear local startup/update/diagnostic experience.
- Remove obsolete archives and generated artifacts from the current tree.
- Replace all public and planning documentation with verified instructions.
- Prepare, but do not perform, optional Git-history rewriting without approval.
