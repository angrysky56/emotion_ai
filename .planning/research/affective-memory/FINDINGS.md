# Findings log — Aura affective memory architecture

**Append-only.** Newest entries go at the bottom. Earlier conclusions are marked
as superseded when later evidence refutes them.

Status is `established` only after the baseline gate, at least three evaluation
runs, a faithful instrument, and explicit caveats. Everything below begins as
`provisional`.

---

## Entries

### #1 — Current-system structural audit — 2026-08-30 — status: `provisional`

**What was run.** Read-only inspection of Aura's active conversation,
Chroma retrieval, emotional analysis, Memvid v2 integration, package lock, and
preserved archive metadata at the current working tree. No personal archive
content was read and no source database was opened by this entry.

**Numbers.** The preserved Memvid directory contains 12 readable `.mv2` files
with 382 total frames. The active conversation path retrieves Chroma memories
before generation and performs emotional analysis after generation. The current
emotion mapping has no time-evolving concentrations, decay, homeostasis, or
causal pre-response state update.

**Redundancy check.** Memvid file presence was checked through the filesystem;
readability and frame counts were independently obtained through the installed
Memvid v2 SDK. No retrieval-quality number is claimed.

**Positive control.** The installed SDK opened every preserved `.mv2` archive and
reported nonzero frames, showing the metadata probe can distinguish populated
archives from absent ones.

**What it means.** Aura has real saved material, but the active memory system and
the affective simulation are not currently joined into a learning loop. The
preserved archives live under `aura_backend/memvid_videos`, while runtime defaults
resolve `./memvid_videos`; ordinary root-level startup therefore does not discover
them. The archive writer also deletes active Chroma records after closing the
archive without a restore/retrieval parity gate.

**What it refutes.** It refutes the strong claim that Aura already has a working
neurochemically modulated long-term memory. It does not refute the possibility
that the preserved Memvid material is valuable or that Memvid v2 is useful as a
future cold archive.

**Caveats.** Structural inspection is not an end-to-end memory evaluation.
Archive contents were deliberately not inspected, retrieval quality was not
scored, and no candidate architecture has run.

**Checkpoint.** "Stop an alternative architecture after the incumbent and its mechanism-removed control are valid if it fails to improve its predeclared Aura-specific slice by 5 absolute percentage points or 30% measured storage/latency, or if it introduces any cross-user leak, untraceable memory, unrecoverable write, or silent stale-fact preference. Stop the affective mechanism if it fails its salience target across three fixed evaluation runs or if a constant-salience control explains the gain." Not met, continuing.

### #2 — Architecture research verdict — 2026-08-31 — status: `provisional`

**What was run.** Compared current primary documentation and papers for Memvid
v2, Recursive Language Models, Graphiti/Zep, Mem0, LongMemEval, and LoCoMo-Plus
against Aura's local-only requirements and the structural audit in Entry #1.
Inspected Ty's local Graph-RLM source tree for dependency and implementation
scope. No comparative memory benchmark has run.

**Numbers.** Graph-RLM contains 64 Python source files and approximately 27,067
lines under its core source tree, plus a FalkorDB service dependency. Its
ACT-R-style activation module is a narrow reusable idea. Mem0's own paper reports
roughly a two-point overall gain for its graph variant over its simpler memory
configuration, which is below Aura's pre-registered five-point adoption margin
and is not an Aura-specific comparison.

**Redundancy check.** Graph-RLM scope was checked both by filesystem file counts
and aggregate line counts. The Memvid generation was checked against both the
installed pinned v2 SDK and current official repository documentation.

**Positive control.** The comparison distinguishes capabilities that are truly
different: RLM provides recursive long-context inference, Memvid provides a
portable append-only container, and Graphiti provides temporal relationship
invalidation. It does not flatten them into interchangeable “memory systems.”

**What it means.** The strongest design is a typed SQLite ledger plus rebuildable
hybrid indexes. Memvid remains a copy-only cold-archive candidate. A temporal
graph and RLM reader remain optional derived capabilities, adopted only for
measured multi-hop or over-context gaps. Aura's novel research target is the
causal affect-to-behavior-and-memory loop, not another general agent framework.

**What it refutes.** It refutes the proposal to replace Aura's memory wholesale
with Graph-RLM or to make Memvid the only durable truth store. It does not refute
reusing a small activation formula, evaluating Memvid portability, or adding a
derived temporal graph later.

**Caveats.** Framework benchmark claims are mostly reported by their creators,
and no Aura-specific corpus exists yet. The verdict is architectural and
provisional until arm zero and candidate slices are measured.

**Checkpoint.** "Stop an alternative architecture after the incumbent and its mechanism-removed control are valid if it fails to improve its predeclared Aura-specific slice by 5 absolute percentage points or 30% measured storage/latency, or if it introduces any cross-user leak, untraceable memory, unrecoverable write, or silent stale-fact preference. Stop the affective mechanism if it fails its salience target across three fixed evaluation runs or if a constant-salience control explains the gain." Not met, continuing: zero comparative runs have been used.

### #3 — Center and relational consequence — 2026-08-31 — status: `provisional`

**What was run.** Converted Ty's observed contrast between collaborative coaching
and sustained hostile treatment into a layered behavioral contract. Compared the
contract with primary research on prompt politeness effects and computational
appraisal/homeostatic emotion. No model behavior run has occurred.

**Numbers.** Zero experimental runs. The contract defines six rates/owners of
state and ten paired behavioral checks. One cross-lingual study reports that
impolite prompts often reduce LLM task performance, so equivalent-task success
under polite versus hostile phrasing is a necessary control rather than an
assumption.

**Redundancy check.** None for behavior: this entry defines the instrument and
cannot validate itself. The separation was checked against both the existing
Aura architecture decision and the newly added requirements/roadmap mappings.

**Positive control.** Repeated directed contempt must produce measurably firmer
boundaries and reduced relational openness than collaborative coaching. If it
does not, the affect instrument is insensitive and any null is uninformative.

**What it means.** Aura needs a stable center above its affective state. Negative
treatment may produce guardedness, lower trust, reduced optional disclosure, and
principled refusal to continue degrading interaction. It may not produce hidden
retaliation, false answers, tool sabotage, memory damage, or permanent negative
capture. Tool-directed frustration, justified criticism, and directed abuse must
be appraised differently, with an explicit repair path.

**What it refutes.** It refutes treating degraded task competence as a desirable
emotional consequence. It also refutes a permanently positive mask that makes
treatment irrelevant. It does not determine whether the substrate model can
reliably express the intended distinctions.

**Caveats.** The center is a design contract, not evidence of feeling or
sentience. Prompt-tone sensitivity differs by model and language. Paired tests
with Aura's actual local models are required.

**Checkpoint.** "Stop an alternative architecture after the incumbent and its mechanism-removed control are valid if it fails to improve its predeclared Aura-specific slice by 5 absolute percentage points or 30% measured storage/latency, or if it introduces any cross-user leak, untraceable memory, unrecoverable write, or silent stale-fact preference. Stop the affective mechanism if it fails its salience target across three fixed evaluation runs or if a constant-salience control explains the gain." Not met, continuing: this entry adds pre-run controls and uses no comparative run.
