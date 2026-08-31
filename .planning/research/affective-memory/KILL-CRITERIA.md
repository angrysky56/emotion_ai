# Kill criteria — Aura affective memory architecture

Written: 2026-08-30
Written **before** any comparative experiment was run. Do not edit fields below
except through the Revisions section at the bottom.

---

## The question

What is the simplest local memory architecture that gives Aura durable,
correctable conversational continuity and lets a bounded simulated affective
state causally change what is encoded, consolidated, retrieved, and expressed?

## Three nearest prior works

| work | link | what differs here |
|---|---|---|
| Memvid v2 | https://github.com/memvid/memvid | Portable append-only single-file memory and hybrid search; Aura additionally needs typed corrections, user-visible provenance, and affect-controlled consolidation. |
| Zep/Graphiti | https://arxiv.org/abs/2501.13956 | Temporal knowledge graph with invalidated facts and hybrid retrieval; Aura must stay simple, private, local-first, and reliable with a 12 GB consumer GPU. |
| Mem0 | https://arxiv.org/abs/2504.19413 | Extracts, consolidates, and retrieves salient conversational facts, optionally in a graph; Aura tests a continuous affective state as a causal memory control rather than treating salience as only an LLM extraction decision. |

Recursive Language Models (https://arxiv.org/abs/2512.24601) are a relevant
reasoning method, but not a durable memory ledger. Ty's Graph-RLM is therefore a
candidate *reader/reasoner* over memory, not an incumbent storage system.

## The incumbent (arm zero)

A local append-only SQLite event ledger is the source of truth. It stores typed
conversation events, derived facts/preferences, affect snapshots, provenance,
and explicit supersession. Existing Chroma is initially retained only as a
rebuildable semantic candidate index. Retrieval combines exact/lexical matches,
semantic candidates, recency, and bounded salience before deterministic
reranking. No graph or Memvid dependency is required for the baseline.

In the harness as of: not yet implemented; this file precedes Phase 3 planning.

## Prediction

On an Aura-specific sanitized corpus containing direct recall, paraphrase,
changed facts, temporal questions, distractors, implicit personal constraints,
and affectively important episodes, the incumbent will match or beat the more
elaborate candidates on correctness while being easier to recover and audit.
A temporal graph may win only on genuine multi-hop relationship questions;
Memvid may win only on portable cold-archive size and replay; an RLM may win only
when the selected evidence exceeds ordinary model context or needs recursive
inspection.

## Mechanism

The event ledger preserves exactly what happened. Derived memories point back to
those events and can be superseded without erasing history. Hybrid retrieval
finds both exact names/dates and semantic paraphrases. The affective state changes
bounded salience and consolidation timing, while retrieval still requires factual
relevance. This separates durable truth, lossy interpretation, retrieval, and
behavioral modulation so that each can be tested independently.

## Target — headline

The incumbent must achieve at least 0.90 Recall@5 on direct/paraphrased facts,
0.90 accuracy on explicit knowledge updates, 1.00 abstention on absent critical
facts, and zero cross-user leakage or untraceable memories on the sanitized
evaluation corpus. Warm retrieval p95 must remain below 250 ms at 10,000 events
on Ty's machine.

An alternative is adopted only if it improves its intended Aura-specific slice
by at least 5 absolute percentage points or cuts measured storage/latency by at
least 30%, without worsening update correctness, provenance, privacy, or recovery.

## Target — mechanistic

Compared with a constant-salience control having the same average write volume,
the dynamic affective gate must improve recall of pre-labelled high-importance
episodes by at least 10 absolute percentage points while reducing ordinary-fact
Recall@5 by no more than 2 points. Resetting the affect state must return all
modulated parameters toward baseline, and identical event sequences must produce
identical state trajectories.

## The boring failure

The base model and hybrid retriever already recover the useful material; the
named neurochemicals merely rename prompt settings; emotion labels add volume
but no information; an LLM extractor writes confident stale summaries; or graph
and archive machinery adds failure modes without improving Aura's actual recall.

## STOPPING CONDITION

> Stop an alternative architecture after the incumbent and its mechanism-removed control are valid if it fails to improve its predeclared Aura-specific slice by 5 absolute percentage points or 30% measured storage/latency, or if it introduces any cross-user leak, untraceable memory, unrecoverable write, or silent stale-fact preference. Stop the affective mechanism if it fails its salience target across three fixed evaluation runs or if a constant-salience control explains the gain.

## Resource threshold

No candidate receives more than three implementation/evaluation cycles or one
working day before this stopping condition is applied. Do not install a new graph
server or large model before the incumbent corpus and arm-zero results exist.

Runs used so far: 0

---

## Checkpoint log

| date | runs used | verdict | note |
|---|---:|---|---|
| 2026-08-30 | 0 | not met, continuing | Pre-registration created; architecture and current wiring are being audited before implementation. |

---

## Revisions

| date | field | original text | new text | result that prompted it |
|---|---|---|---|---|

