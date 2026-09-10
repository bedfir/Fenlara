# Agent Selection Layer — Problem Statement

**Status:** Draft v0.1 — pre-code, pre-name
**Scope:** This document defines a single layer in the emerging agent-interoperability stack. It does not propose a protocol, a name, or an implementation.

## Position in the stack

```
Discovery Layer     (DAWN)         "which entities match my request?"
        |
        v
   candidates
        |
        v
Selection Layer      (this project) "which candidate is best, right now,
        |                            given my constraints?"
        |
        v
   chosen agent
        |
        v
Resolution Layer     (DN-ANR)       "does this identifier really map to
        |                            this endpoint?"
        |
        v
Connection Layer     (A2A / ANP / MCP / ...)
```

DAWN's own scope documents explicitly exclude "search, ranking, or marketplace discovery" and "entity selection mechanisms and policies." DN-ANR explicitly starts *after* an identifier has already been selected. Between the two, there is no standardized layer that turns a list of candidates into one decision. That gap is this project.

## 1. Input

A selection request combines three things, all supplied by the requesting agent (or its operator):

- **A candidate set** — the output of a discovery step (DAWN-shaped or not; this layer does not care where candidates came from, only that each carries a minimum set of comparable attributes: capability match, protocol, endpoint reference, and whatever trust/price/latency/availability data the candidate publishes).
- **Constraints** — hard filters that eliminate candidates outright (e.g. jurisdiction, max price, max latency, required protocol). A candidate failing any constraint is rejected before scoring, not scored low.
- **Preferences** — a weighting across soft criteria (trust, price, latency, availability, ...) used only among candidates that survive the constraints.

```json
{
  "task": "translate_contract",
  "constraints": { "jurisdiction": "EU", "max_price": 3.00, "max_latency_ms": 5000 },
  "preferences": { "trust": 0.7, "price": 0.2, "latency": 0.1 }
}
```

## 2. Output

- The chosen candidate (or a ranked shortlist, if the caller asks for more than one).
- A **score breakdown per candidate**, not just a winner — the weighted contribution of each criterion to the final score.
- A **rejection reason** for every candidate eliminated by a hard constraint.

The output must be enough, on its own, to answer "why this one and not that one" without re-running the computation.

## 3. Constraints — what this layer does NOT do

- Does **not** discover candidates. It consumes a candidate set; it never queries an external world for one.
- Does **not** verify that an identifier resolves to a genuine endpoint (DN-ANR's job).
- Does **not** negotiate capabilities or execute the task.
- Does **not** compute trust scores from raw evidence — it consumes a trust score (or comparable signal) as an input attribute, exactly as published by discovery. Trust *computation* belongs to the discovery/registry side (cf. AINS's evidence model).
- Does **not** use a language model to make the final choice. An LLM may help translate a fuzzy intent into structured constraints/preferences *before* this layer runs (matching), but the scoring and ranking step itself must be deterministic and reproducible from the same inputs.

## 4. Interfaces

- **Upstream (from Discovery):** accepts a list of candidate records. No assumption is made about their source protocol — DAWN-shaped, raw A2A Agent Cards, ANP descriptions, or a hand-built list all work as long as they can be normalized to the minimum comparable attribute set.
- **Downstream (to Resolution):** emits exactly one selected candidate identifier, handed to a resolution mechanism (DN-ANR or equivalent) for endpoint verification — this layer never talks to an endpoint directly.
- **Sideways (to the requester):** returns the score breakdown and rejection reasons synchronously, so the calling agent (or its human operator) can audit or override the decision before it is acted on.

## 5. Decision model

- **Hard filter, then weighted score.** Constraints are boolean gates; preferences produce a weighted sum over normalized per-criterion scores (e.g. price and latency inverted and scaled 0–1, trust used as-is).
- **Deterministic and explainable by design.** Same candidate set + same request → same output, every time. This matters specifically because the layer's decisions can route real tasks (and money) to a specific agent — an operator must be able to answer "why this one?" without re-asking a model.
- **Matching vs. selection are kept separate on purpose.** Turning "I need to translate a contract" into `{"capability": "legal-translation", "jurisdiction": "EU"}` is a matching problem and may reasonably use an LLM. Turning four scored candidates into one choice is a selection problem and should not.
- **Pluggable scoring, fixed contract.** The specific weighting formula is expected to evolve (and to be overridden per-deployment); what stays fixed is the input/output contract above, so the layer can be swapped or extended without breaking callers.
