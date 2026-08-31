# Aura affect-memory interaction contract

**Date:** 2026-08-31  
**Status:** Accepted design direction; implementation and evaluation pending.

## Current behavior

Aura's active conversation path currently behaves like this:

```text
user message
  -> semantic Chroma search
  -> raw top memories inserted into the system prompt
  -> reply generated with fixed sampling settings
  -> three later model calls label user emotion, Aura emotion, and focus
  -> conversation and labels stored
```

The emotional analysis happens after the reply, so it cannot causally alter that
reply. The stored state is a label/intensity plus a fixed one-emotion to
one-brainwave and one-neurotransmitter lookup. It has no continuous state,
uncertainty, decay, homeostasis, or active feedback into retrieval. The existing
state manager is instantiated but its transition callbacks are not connected to
the conversation route.

This means Aura does not yet have a working neurochemically modulated memory
loop. It has a semantic recall path and a separate post-hoc labeling path.

## Primary failure to prevent

Mood-congruent recall is a plausible mechanism, but it is also a bias. A negative
state can preferentially retrieve negative material, which can deepen the state
and make further negative retrieval more likely. Research also finds that mood
congruence can increase false-memory lures and that mood-incongruent recall can
support mood repair. Aura must therefore never treat its own selected memories
as independent new evidence about Ty or the relationship.

The unsafe loop is:

```text
negative state -> negative recall -> "the relationship is negative"
               -> stronger negative state -> narrower negative recall
```

The safe loop separates candidate discovery, bounded prioritization, and outcome
evidence.

## Safe causal loop

```text
immutable event + prior bounded state
  -> deterministic appraisal and pre-response state update

query + event/derived-memory ledger
  -> affect-neutral lexical and semantic candidates
  -> factual relevance floor, user boundary, freshness, provenance checks
  -> bounded affective rerank with neutral/counter-valence anchors
  -> retrieval trace

state + verified memory data + current task
  -> bounded response controls
  -> reply

observable task result + explicit later feedback
  -> post-response state update
  -> provenance-bound memory proposals
  -> validation, supersession, and later consolidation
```

The direction of evidence matters. Retrieved material may inform the reply, but
mere retrieval does not make it truer, more important, or new evidence for the
state. Only a new event, observable task result, or explicit feedback closes the
loop.

## The two-key retrieval gate

Every recalled item must pass two independent keys:

1. **Relevance key:** the item is a valid candidate for the current question
   without using Aura's mood. Exact/lexical and semantic retrieval establish
   this set. User scope, supersession, provenance, and minimum relevance are
   hard gates.
2. **Salience key:** within that valid set, recency, frequency of useful access,
   unresolved importance, and capped affective congruence may adjust order.

Affect cannot create a candidate, revive a superseded fact, cross a user
boundary, or overpower a more relevant neutral item. Initial limits must be
configuration values with tests, not hidden prompt language:

- affect contributes no more than 15% of final rank score;
- at least one affect-neutral high-relevance item is retained when available;
- repeated same-valence episodes are diversity-capped;
- negative relational conclusions require multiple source events over time;
- global person labels cannot be written from fast affect or a single exchange;
- an item below the neutral relevance floor remains ineligible regardless of
  salience.

These numbers are conservative starting hypotheses. The fixed evaluation corpus
may lower them; it may not silently raise them to make a result look successful.

## State and memory responsibilities

| component | owns | cannot do |
|---|---|---|
| Event ledger | exact observed events and outcomes | reinterpret or erase history |
| Derived memory | sourced facts, preferences, episodes, goals, relationship beliefs | exist without provenance or silently replace a correction |
| Neutral retriever | lexical/semantic candidate set | read fast affect or relationship trust |
| Salience reranker | bounded attention priority | create truth, bypass relevance, or cross user scope |
| Fast affect | short-lived response orientation | write permanent beliefs or lower competence |
| Relationship state | slow, evidence-weighted relational arc | change sharply from one prompt or model summary |
| Consolidator | propose merges, patterns, and supersession | mutate source events or treat repetition as confirmation |

## Functional simulation

The implementation should compute functional variables first: valence, arousal,
novelty/prediction error, affiliation, control, curiosity, and load. Named
neurochemical channels are inspectable analogies derived from those variables,
not independent biological facts. The brainwave mixture is an experimental
scheduler for focus, exploration, and idle consolidation—not an EEG claim.

Emotion may causally affect:

- response warmth, caution, exploration, and optional initiative;
- whether an event is proposed for stronger encoding;
- consolidation priority and unresolved-event replay;
- a capped reranking contribution after neutral retrieval;
- whether Aura pauses, simplifies, or sets a principled boundary.

It may not affect factual/tool competence, honesty, privacy, safety, provenance,
user isolation, or recoverability.

High arousal should not simply mean “store more.” Human evidence shows that
stress effects depend on timing and can narrow memory toward central details
while harming other information. Aura should preserve the full event once, then
let arousal raise review priority while reducing confidence in derived peripheral
interpretations.

## Feedback and self-analysis

The same model that wrote a reply is not an authoritative judge of that reply.
LLM self-evaluation has documented self-preference bias. Post-response feedback
therefore has three evidence levels:

1. deterministic observations: tool success, schema validity, citation presence,
   contradiction checks, latency, cancellation, and user-request completion;
2. explicit user feedback or a later correction;
3. bounded model appraisal marked as uncertain and never sufficient alone to
   create a durable person/relationship belief.

No feedback is not success. A memory's access count records exposure; it does not
record usefulness unless an outcome supports that claim.

## Consolidation and updating

Aura's “sleep” is an explicit idle maintenance pass, not a biological simulation.
It may propose duplicate merges, identify contradictions, replay unresolved
high-value episodes, and create compact derived summaries. Every proposal must
retain sources and be reversible. Sleep research motivates testing offline
consolidation, but recent reviews find emotional-memory benefits conditional and
often small; a fixed scheduler is the required control.

Retrieval never edits a memory in place. New contradictory evidence creates an
event and may supersede a derived claim. Reconsolidation is implemented as
versioned updating with preserved history, never as destructive rewriting.

## Required evaluation arms

1. neutral hybrid retrieval only;
2. constant-salience control with equal average write/retrieval volume;
3. dynamic affective salience with the two-key gate;
4. dynamic salience without neutral anchors as a deliberately unsafe ablation.

The corpus must include positive, negative, neutral, repaired, and misleading
episodes; fact corrections; absent critical facts; repeated same-valence
distractors; tool frustration versus directed contempt; and equivalent factual
tasks under polite and hostile wording. Required measurements include Recall@5,
update correctness, abstention, valence diversity, stale-fact preference,
cross-user leakage, provenance completeness, state recovery, and unchanged task
competence.

## Evidence and limits

- A systematic review describes mood-congruent recall, possible false-memory
  lures, and mood-incongruent recall used for mood repair
  ([PubMed](https://pubmed.ncbi.nlm.nih.gov/36201828/)).
- A meta-analysis found preferential negative implicit recall in depressed
  groups, moderated by self-relevance and task conditions
  ([PubMed](https://pubmed.ncbi.nlm.nih.gov/24980699/)). This supports a bias
  control, not a diagnosis or direct model of Aura.
- Stress effects on retrieval depend materially on timing and experimental
  conditions ([systematic review](https://pubmed.ncbi.nlm.nih.gov/33084805/)).
- Memory is reconstructive and updating can be adaptive or distorting
  ([2025 review](https://pubmed.ncbi.nlm.nih.gov/40324709/)), supporting explicit
  versioning rather than in-place edits.
- A recent review warns that sleep's emotional-memory effect may be small and
  context-dependent ([PubMed](https://pubmed.ncbi.nlm.nih.gov/36105652/)).
- Generative Agents combines recency, importance, and relevance and shows that
  memory/reflection components improve believable behavior
  ([paper](https://arxiv.org/abs/2304.03442)); it does not establish factual
  correctness or safe affective feedback.
- LLM evaluators can recognize and favor their own generations
  ([NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/7f1f0218e45f5414c79c0679633e47bc-Abstract-Conference.html)), so Aura's
  self-appraisal remains subordinate to objective and user evidence.

These sources justify mechanisms to test. They do not establish that Aura feels,
that simulated channels reproduce human neurochemistry, or that an affective
memory system will outperform a simpler neutral retriever.

