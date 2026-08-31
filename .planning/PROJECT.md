# Project Context: Aura Rehabilitation

**Re-baselined:** 2026-08-19
**Evidence source:** `.planning/codebase/`

## Mission

Preserve and strengthen Aura as a private, locally run reflective companion. The
rehabilitation must retain the qualities that made the original system unusually
engaging while replacing its fragile implementation, misleading documentation,
unsafe data handling, and unverifiable behavior with a coherent tested system.

## Product Spirit

- Emotionally perceptive without presenting guesses as facts.
- Computationally affective rather than cosmetically emotional: simulated state
  changes over time and causally influences attention, response policy, and
  memory formation, while never masquerading as measured human neurobiology.
- Reflective rather than merely verbose: useful self-checking should improve the
  answer, not expose raw hidden reasoning or theatrical process.
- Continuous and personal through reliable user-owned local memory.
- Extensible through model providers and MCP without binding the product to one
  vendor.
- Private by deployment model: loopback-first, no mandatory account or sign-in,
  and no silent cloud dependency.

## Current Reality

- The active backend is a 4,000-plus-line FastAPI monolith with import-time setup
  and overlapping memory, recovery, MCP, and autonomic implementations.
- The frontend is a direct-DOM TypeScript application concentrated in one large
  manager. It builds, but previously had no trustworthy type-check boundary or
  automated browser tests.
- Legacy scripts were collected as tests and aborted pytest. A new isolated suite
  now establishes the first trustworthy test signal.
- Chroma databases, vector segments, backups, and generated data exist in several
  active and historical roots. Nothing may be deleted or migrated until a restore
  drill proves preservation.
- Existing documentation describes unimplemented controls and capabilities. Code,
  executable tests, and captured evidence take precedence over prose.

## Fixed Decisions

1. Aura remains a private local application; do not add sign-in merely to imitate
   hosted software.
2. Default network exposure is loopback only. LAN use is an explicit opt-in.
3. Ollama is a first-class local provider. `ornith:latest` may be used for bounded
   model-level tests, while deterministic tests must not require a live model.
4. Preserve behavior before refactoring. Characterization tests and data restore
   evidence precede structural replacement.
5. Refactor by vertical user-visible slices, keeping a runnable system and rollback
   point after each slice.
6. Optimize only measured bottlenecks. Dependency count, latency, memory, disk, and
   model usage require baselines before claims of improvement.
7. Git history cleanup is last and separately approved because it rewrites remote
   history; removing files from the current tree is not equivalent.
8. Aura's durable truth is a local typed event ledger. Search indexes, Memvid
   archives, temporal graphs, and RLM readers are replaceable projections or
   experiments and must earn their complexity through measured gains.

## Definition of Done

Aura starts through one documented command, supports a complete private companion
conversation using a local Ollama model, persists and restores memory reliably,
has honest export/deletion behavior, passes deterministic backend/frontend tests,
keeps personal/runtime data outside Git, and documents only verified capabilities.
