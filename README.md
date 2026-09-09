# Fenlara

**Deterministic selection for the Internet of Agents.**

Fenlara is a lightweight, deterministic selection layer for agent execution offers. It takes a pre-discovered candidate pool of offers and a request containing hard constraints and soft preferences, then deterministically selects the optimal offer.

> **Scope Note:** Fenlara does **not** discover agents, verify identities, resolve endpoints, negotiate capabilities, or execute tasks. Its sole responsibility is selection.

```text
                    Internet of Agents
                            │
                            ▼
                   ┌─────────────────┐
                   │    Discovery    │
                   │                 │
                   │ Who / what      │
                   │ might match?    │
                   └────────┬────────┘
                            │
                    candidate offers
                            │
                            ▼
                   ┌─────────────────┐
                   │     Fenlara     │
                   │                 │
                   │ Which offer     │
                   │ should I choose?│
                   └────────┬────────┘
                            │
                     selected offer
                            │
                            ▼
                   ┌─────────────────┐
                   │   Resolution    │
                   │                 │
                   │ Where / how     │
                   │ can I connect?  │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │   Connection    │
                   │                 │
                   │ A2A / ANP / ... │
                   └─────────────────┘
```

---

## The Problem

As the ecosystem of interoperable agents expands, discovering capability matches is only half the challenge. A requester will frequently receive multiple competing offers for a single task:

| Offer | Trust | Price (€) | Latency (ms) |
| :--- | :--- | :--- | :--- |
| **Offer A** | 0.99 | 2.50 | 2000 |
| **Offer B** | 0.97 | 0.40 | 15000 |
| **Offer C** | 0.999 | 5.00 | 3000 |

Selecting the right offer requires trade-offs. While **Discovery** asks *"Which entities might satisfy my request?"*, **Fenlara** answers *"Given these candidates and my constraints, which offer should I execute?"*

---

## Core Abstraction

Fenlara selects **execution offers**, not agents. Every offer maintains a distinct dual identity:

```json
{
  "agent_id": "agent-1",
  "offer_id": "offer-fast"
}
```

* `agent_id`: Identifies the publishing entity.
* `offer_id`: Identifies the specific execution tier or offer.

A single agent can expose multiple offers (e.g., `offer-cheap`, `offer-fast`, `offer-premium`). Fenlara evaluates each offer independently.

---

## Selection Model

Selection consists of two sequential operations:

```text
                    offers
                       │
                       ▼
             hard constraint filter
                       │
                 ┌─────┴─────┐
                 │           │
             rejected     survivors
                 │           │
                 │           ▼
                 │        scoring
                 │           │
                 │           ▼
                 │     deterministic
                 │       selection
                 │           │
                 └─────┬─────┘
                       ▼
                    result
```

### 1. Hard Constraints (Fail-Closed)
Binary filters where missing or non-matching required attributes result in immediate rejection before scoring.

* **Example Constraints:** `jurisdiction = EU`, `max_price = 3.00`, `max_latency_ms = 5000`, `required_protocol = a2a`
* **Fail-Closed Policy:** `unknown != acceptable`. If a required constraint field is missing from an offer, it is rejected.

### 2. Soft Preferences (Scored)
Surviving offers are evaluated against weighted preferences. Weights and criteria are normalized across the surviving pool.

* **Lower is better:** `price`, `latency`
* **Higher is better:** `trust`, `availability`

```json
{
  "trust": 0.7,
  "price": 0.2,
  "latency": 0.1
}
```

### Missing Data Handling

* **In Constraints:** Triggers immediate rejection (`REJECT`).
* **In Preferences:** Survives filter with `score = 0` for that specific attribute, accompanied by a warning (e.g., `warning: missing price`).

---

## Determinism & Tie-Breaking

Given identical offers and selection requests, Fenlara produces identical outputs without non-deterministic components (e.g., no LLMs in the execution path).

If candidate scores are identical, Fenlara executes a deterministic lexicographic tie-break on `offer_id` and explicitly flags the event in the audit result. This guarantees that decisions remain **reproducible**, **testable**, **explainable**, and **auditable**.

---

## Architecture & Boundaries

Fenlara strictly decouples **matching** from **selection**. It assumes discovery/matching has occurred upstream and treats properties like capabilities or endpoints as passthrough payload.

```text
Discovery Source (A2A / ANP / Registry / Local)
                      │
                      ▼
            Normalized Offer Payload
                      │
                      ▼
               Fenlara Engine
```

### Explicit Non-Goals
To preserve a narrow responsibility layer, Fenlara does **not** handle:
* Registries, discovery, or capability matching
* Identity, trust, attestation, or capability negotiation
* Endpoint resolution, transport protocols (A2A/ANP/MCP), or LLM reasoning

### Trust Boundary
Fenlara does not calculate or attest to upstream trust scores or post-selection endpoint availability. Upstream components must provide validated trust telemetry, and downstream resolution mechanisms should re-verify endpoints before establishing connections.

---

## API & Data Contract

### Single Operation Surface
```python
select(offers: List[Offer], request: SelectionRequest) -> SelectionResult
```

### Execution Offer Schema (v0.1)
```json
{
  "offer_id": "offer-fast",
  "agent_id": "agent-1",
  "protocol": "a2a",
  "jurisdiction": "EU",
  "price": 3.0,
  "latency_ms": 50,
  "trust": 0.94,
  "availability": 0.99,
  "endpoint": "https://example.com/agent",
  "capabilities": ["translation"]
}
```

---

## Project Status & Roadmap

### v0.1 — Prototype (Current)
* Pure Python implementation with **zero** external network, registry, DNS, or LLM dependencies.
* Verified with **24 passing tests** under **JSON Schema 2020-12**.
* Implements basic `agent_id` / `offer_id` separation, constraint filtering, scoring, deterministic tie-breaking, and audit reporting.

### Roadmap

- [ ] **v0.2:** Formalize `SelectionRequest` / `SelectionResult` schemas, introduce scoring policy abstractions, and enhance audit tooling.
- [ ] **Open Architecture Question:** Evaluate relative pool normalization vs. absolute scoring models before stabilizing public contracts (preventing candidate C from skewing relative preferences between A and B).
- [ ] **Future:** Local API wrapper → Network API → Ecosystem integrations (A2A, ANP, MCP).
