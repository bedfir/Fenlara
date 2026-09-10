# Prior Art & Validation Status

**Thesis:** Fenlara does not invent agent selection. It proposes to make
agent/execution-offer selection a reusable, policy-driven primitive
rather than an application-specific routing implementation.

This note exists to keep an honest, dated record of what research has
actually shown so far — not to argue that Fenlara is validated. As of
this writing, it is not. See "What remains to be demonstrated" below.

---

## 1. What is already demonstrated

- **`constraints → scoring → ranking` already exists, independently, in
  multiple production systems.** LLM/model routers (OpenRouter,
  LiteLLM) and at least one documented A2A-marketplace pattern all
  implement some version of: filter candidates by hard requirements,
  then score survivors by a weighted or ratio-based function.
- **The criteria converge.** Across every system found, the same small
  set of attributes keeps reappearing: cost, latency, availability
  (recent outages / rate limits), trust or reputation, and
  jurisdiction/data-residency/compliance. This is not Fenlara's own
  vocabulary bleeding into the search results — it shows up
  independently in LLM routing docs, agent-marketplace guides, and
  older multi-agent-systems literature on partner selection.
- **Selection policy legitimately differs by requester, in production,
  today.** LiteLLM ships six distinct, named routing strategies
  (weighted pick, latency-based, rate-limit-aware, least-busy,
  lowest-cost, custom). Different deployments pick different ones. This
  is direct evidence for the "same supply, different valid choice"
  hypothesis this project is built on — not a hypothetical.
- **These implementations are consistently domain-coupled.** Every
  instance found is embedded inside the system that needs it: OpenRouter's
  scoring lives in OpenRouter, LiteLLM's in LiteLLM, a marketplace's
  reputation-to-cost ratio lives in that marketplace's matching logic.
  None of them are extracted as a standalone, reusable library that a
  different system could import.

## 2. What remains to be demonstrated

- That the same model actually works for **execution offers in an open,
  multi-party agent environment** (A2A/MCP-style), not just for a
  gateway routing between a fixed, known set of LLM providers, or a
  closed marketplace with its own payment rails.
- That the **`agent_id` / `offer_id` split** carries real value outside
  of the scenarios this project designed for itself — i.e., that
  someone building against this contract actually needs to distinguish
  "who published this" from "which specific offer is this," rather than
  it being a solution in search of a problem.
- That Fenlara is a **useful layer between discovery and execution**,
  rather than an over-formalized version of `filter → sort → first`
  that most real deployments would happily inline in a few lines of
  application code instead of adding a dependency for.
- That a **shared standard of criteria/policy** is valuable enough to
  justify an independent primitive — as opposed to every ecosystem
  (LLM routing, agent marketplaces, A2A) being fine with its own
  bespoke, non-interoperable version forever, the way it is today.

## 3. The decisive test for "is an independent layer necessary"

Construct several cases where the *same list of offers* produces a
*different* choice depending purely on the requester's declared policy:

- `cheapest`
- `lowest_latency`
- `most_trusted`
- `balanced`
- a custom policy

If Fenlara can express all of these through one generic API — without
knowing anything about A2A, MCP, HTTP, DNS, or any specific
marketplace — the argument for an independent layer gets considerably
stronger. If it turns out that expressing these policies requires
Fenlara to grow domain-specific knowledge of any of those systems, that
would be a sign the abstraction is leaking and the "does not know about
A2A/MCP/DNS" boundary (see README) is not actually holding.

---

## Related work found (dated, non-exhaustive)

Kept here so the research isn't re-done from scratch later, and so
claims above are traceable.

- **OpenRouter** — hosted multi-provider LLM gateway. Default routing:
  deprioritize providers with a recent outage, then weight by the
  inverse square of price; explicit provider filters for price,
  throughput, latency, data policy, and region (EU routing for GDPR).
- **LiteLLM** — self-hosted LLM proxy/router. Six named routing
  strategies (see above), fully custom Python routing supported.
- **RouteWise** (Harvard SEAS / MadSys Lab) — dependency-free Python
  library for cost-aware, latency-optimized LLM routing with outcome
  feedback. Closest in spirit (small, dependency-free) but adaptive/
  learning-based rather than deterministic, and scoped to LLM API
  providers specifically.
- **A2A marketplace pattern** (documented example, "The Complete Guide
  to Agent-to-Agent Marketplaces," 2026) — a GraphQL query filtering
  agents by capability and max price, returning `pricePerCall`,
  `latencySlaMs`, `reputationScore`, with guidance to "pick the agent
  with the best reputation-to-cost ratio." Bespoke to that one
  marketplace's schema and (crypto) payment rail.
- **Generic AI agent marketplace pattern** (nullpath, 2026) — describes
  agents being "sorted by price or reputation," and callers either
  hard-filtering on reputation or trading it off against price. Same
  constraint/preference split as Fenlara, described independently, not
  factored into a shared library.
- **Microsoft Semantic Kernel — `SelectionStrategy` /
  `KernelFunctionSelectionStrategy`** — a real, shipped abstract class
  for pluggable agent selection in multi-agent conversations. The
  closest *named engineering abstraction* found to what Fenlara
  proposes — but scoped to choosing which agent speaks next in a
  conversation (turn-taking), not to choosing among competing external
  execution offers.
- **AgentSelect** (arXiv:2603.03761, 2026) — a benchmark reframing
  "agent selection" as narrative-query-to-agent *recommendation* over
  capability profiles, using retrieval/ranking metrics (nDCG, MRR).
  Despite the name, this solves what Fenlara's own README calls
  **matching** (is this offer relevant to the intent at all), not
  **selection** (which relevant, already-eligible offer to pick). Worth
  tracking because the terminology overlap invites confusion.
- **Multi-agent-systems academic literature on "partner selection"**
  (e.g., Lim Choi Keung & Griffiths, "Towards improved partner
  selection using recommendations and trust," 2008) — the problem is
  old and has its own research lineage under "trust and reputation in
  agent societies." Historically, these models tend to fuse trust
  computation and selection logic together, rather than treating
  "consume a trust score" and "decide what to do with it" as separable
  concerns the way Fenlara's schema does.
- **"Capability Advertisement as a Market for Lemons"**
  (arXiv:2606.03034, 2026) — argues self-reported agent capability
  claims are unreliable in open heterogeneous networks (information
  asymmetry, no calibration, silent model swaps behind stable
  advertisements) and proposes a trust layer with signaling and
  screening. Solves a different, upstream problem ("can I trust what
  this offer claims?"), but is a plausible future input source for
  Fenlara's `trust` field rather than a competing selection layer.

## Caveat

All of the production examples above (OpenRouter, LiteLLM, RouteWise)
operate in **LLM/model routing**, a neighboring but distinct domain
from **A2A/MCP execution-offer selection**. The shape of the problem
transfers closely; whether the underlying need does too is exactly
what section 2 and the test in section 3 are meant to find out.
