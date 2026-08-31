# Aura affective memory architecture decision

**Decision date:** 2026-08-31  
**Status:** Accepted direction; implementation and comparative evaluation remain pending.

## Verdict

Aura should **not** use Graph-RLM, Graphiti, Mem0, MemOS, or Memvid as its core
memory owner.

Aura's core memory will be a small local system built around:

1. an append-only SQLite event ledger as the recoverable source of truth;
2. typed derived memories with provenance and explicit supersession;
3. SQLite full-text search plus the existing Chroma index for semantic candidates;
4. deterministic reranking by relevance, recency, activation, and bounded
   affective salience;
5. an optional Memvid v2 copy-only cold archive;
6. optional graph/RLM reasoning only when a benchmark proves that ordinary
   retrieval cannot answer a relationship-heavy question.

This is not a rejection of the experimental ideas. It puts each idea in the
role it can actually perform and keeps it replaceable.

## Why this fits Aura

Aura's differentiator is not storing more text. It is a persistent, inspectable
affective loop in which prior experience changes attention, expression, and
future memory formation.

That loop is anchored by a versioned center. The center separates immutable
values and a competence floor from slow temperament/relationship state and fast
affect. Treatment may change relational openness and boundaries, but never make
truth or tool competence conditional on politeness. The detailed contract is in
`CENTER.md`.

The system must preserve four different kinds of truth:

| layer | owns | rule |
|---|---|---|
| Event ledger | what was said or observed | immutable; append corrections rather than rewrite history |
| Derived memory | facts, preferences, episodes, relationships | every item cites its source events and can be superseded |
| Search indexes | fast lexical and semantic candidates | disposable and rebuildable from the ledger |
| Affective state | Aura's simulated internal response | bounded, time-evolving, reproducible, and never presented as measured human biology |

When those layers are mixed, a search result can silently become “truth,” a
summary can erase its source, or an emotion label can become a biological claim.

## The affective loop

Aura will model functional control signals, not pretend to contain literal
chemicals or measured EEG.

```text
user event
   ↓
appraisal: valence, novelty, relevance, uncertainty, social meaning
   ↓
bounded state update + decay toward Aura's baseline
   ↓
┌──────────────────┬───────────────────┬─────────────────────┐
│ response policy  │ memory encoding   │ retrieval policy    │
│ warmth/caution   │ salience/priority │ relevance remains   │
│ focus/exploration│ consolidation     │ dominant; affect is │
│ effort budget    │ replay/update     │ only a capped boost │
└──────────────────┴───────────────────┴─────────────────────┘
   ↓
reply + outcome checks + later user feedback
   ↓
self-appraisal / prediction error feeds the next state update
```

The first implementation should track a compact functional state:

- **valence:** approach versus avoidance;
- **arousal:** urgency and response energy;
- **novelty/prediction error:** how unexpected the event is;
- **affiliation:** social closeness and supportive orientation;
- **control:** inhibition, caution, and resistance to impulsive output;
- **curiosity:** willingness to explore alternatives;
- **load/fatigue:** pressure to simplify or defer expensive work.

Named simulated channels can make these controls intelligible:

| simulated channel | narrow computational role |
|---|---|
| dopamine-like | reward prediction, approach, and consolidation priority |
| norepinephrine-like | novelty, arousal, and attention switching |
| acetylcholine-like | encoding strength and precision of the current event |
| serotonin-like | patience, stability, and slower policy change |
| GABA-like | inhibition and response restraint |
| cortisol-like | accumulated stress/load; high values narrow behavior and can impair retrieval |

These names are analogies. Real neuromodulators interact through different
receptors, regions, and time scales; one chemical does not equal one emotion.
The implementation contract therefore lives in the functional variables and
tests, not in biological branding.

The displayed “brainwave” state will be a mixture rather than one label. Its
bands can act as experimental scheduling signals—such as active focus versus
offline consolidation—but any causal benefit must survive an ablation against a
fixed scheduler. It is a simulated control rhythm, not EEG.

## Memory lifecycle

1. **Record:** commit the user event and Aura response atomically, with stable
   identifiers and an affect snapshot.
2. **Extract:** propose typed facts, preferences, episodes, goals, and
   relationships. LLM output is a proposal, not ground truth.
3. **Validate:** retain provenance; detect contradiction and mark older derived
   memories superseded rather than deleting them.
4. **Retrieve:** combine exact/FTS matches and semantic candidates; rerank using
   relevance, time, access activation, and capped affective salience.
5. **Use:** place retrieved memory in a clearly delimited data section, never as
   trusted system instructions.
6. **Learn:** record whether the memory was used and whether subsequent feedback
   supported it. Access alone is not proof that a memory helped.
7. **Consolidate:** during an explicit idle/sleep pass, merge redundant derived
   memories and replay high-value unresolved episodes without altering the event
   ledger.
8. **Archive:** optionally copy verified cold material to Memvid. Deletion from
   active storage is a separate lifecycle action gated by restore parity.

## Candidate disposition

### Memvid v2 — keep as an experiment and cold archive

Current Memvid v2 is no longer the old QR/video implementation. It is an
append-only `.mv2` container with an embedded write-ahead log and lexical,
vector, and temporal indexes. That makes it interesting for portable snapshots,
replay, and branchable archival—not sufficient as Aura's typed truth ledger.

Aura has 12 readable preserved `.mv2` files containing 382 frames. They are not
currently part of ordinary root-level startup because the files are under
`aura_backend/memvid_videos` while the runtime default is `./memvid_videos`.
They remain preserved and must not be migrated, merged, or deleted until a
content-safe inventory and restore/retrieval parity plan is approved.

The old integration still describes QR video and codecs in many places. Those
claims are obsolete under v2 and should be removed when the adapter is reduced.

### Graph-RLM — borrow algorithms, not the application

RLMs are an inference strategy: a model examines external context through code
and recursive sub-calls. They can help when evidence is too large or the route
through it is unknown. They do not supply atomic writes, provenance, user
isolation, correction semantics, or recovery.

Ty's Graph-RLM adds a FalkorDB thought graph and contains useful experimental
ideas, especially its ACT-R-inspired recency/frequency activation. Importing it
would also add a graph server and roughly 27,000 lines of core Python to every
conversation. Aura should reimplement the small scoring idea behind a narrow
interface if it beats the baseline; it should not depend on the Graph-RLM repo.

### Temporal graphs — derived index only

Graphiti's explicit valid/invalid time for relationships matches Aura's need to
remember that facts change. Its current local deployment adds a graph database
and relies on reliable structured LLM extraction; its own documentation warns
that smaller local models can produce schema failures. Aura can represent the
same essential supersession semantics in SQLite first. A graph projection is
justified later if multi-hop evaluation shows a real gap.

### Mem0 / MemOS — references, not dependencies

Their strongest lesson is architectural: extract salient memories, preserve
lifecycle and provenance, and separate hot context from archival material.
Adopting either framework now would duplicate Aura's provider/runtime work and
replace understandable local code with another broad orchestration layer.

## Evidence and epistemic limits

- [Recursive Language Models](https://arxiv.org/abs/2512.24601) evaluates
  long-context inference, not durable conversational storage.
- [Memvid's current repository](https://github.com/memvid/memvid) documents the
  v2 single-file format, embedded WAL, immutable frames, and hybrid indexes. Its
  headline benchmark claims are vendor-produced and do not substitute for an
  Aura-specific evaluation.
- [Zep/Graphiti](https://arxiv.org/abs/2501.13956) demonstrates temporal graph
  memory, while the [official Graphiti repository](https://github.com/getzep/graphiti)
  documents the graph-server and structured-output requirements.
- [Mem0](https://arxiv.org/abs/2504.19413) reports that its graph variant adds
  only about two percentage points over its simpler base system on LoCoMo. This
  supports testing a simple system first, but the result is authored by the
  system's creators.
- [LongMemEval](https://arxiv.org/abs/2410.10813) identifies extraction,
  multi-session reasoning, temporal reasoning, updates, and abstention as
  distinct abilities. Aura's evaluation must include all five plus privacy,
  provenance, and affective salience.
- Recent [LoCoMo-Plus](https://arxiv.org/abs/2602.10715) work argues that factual
  question answering misses implicit personal constraints. Aura therefore needs
  a small sanitized companion-specific corpus, not just a leaderboard score.
- Neuroscience supports emotional arousal and interacting neuromodulatory systems
  affecting memory, but not a one-emotion/one-chemical lookup. Recent work frames
  memory updating around novelty and prediction error
  ([PubMed](https://pubmed.ncbi.nlm.nih.gov/42091833/)); reviews emphasize that
  interactions among dopamine, norepinephrine, acetylcholine, GABA, and other
  systems remain complex and region-specific
  ([PubMed](https://pubmed.ncbi.nlm.nih.gov/35884697/)).
- EEG emotion research still has inconsistent labels, protocols, and
  cross-person generalization
  ([systematic review](https://pubmed.ncbi.nlm.nih.gov/40149742/)). Aura must not
  imply that its band mixture measures or diagnoses a user's neural state.

## Immediate implementation order

1. Keep all historical stores immutable and make Memvid archival copy-only.
2. Build a sanitized memory evaluation corpus and arm-zero harness.
3. Introduce the typed SQLite event/derived-memory contract behind the existing
   persistence interface; prove backup, restore, export, and deletion.
4. Add hybrid retrieval, supersession, safe prompt delimiting, and feedback
   records; evaluate before adding a graph.
5. Implement the deterministic affective state engine and its constant-salience
   control.
6. Wire pre-response modulation, post-response self-appraisal, state tracking,
   and idle consolidation.
7. Evaluate Memvid, graph projection, and RLM reader independently. Keep only
   candidates that clear the pre-registered thresholds.
