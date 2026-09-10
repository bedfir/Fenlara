# Decisive Test: Does Policy-External Selection Hold Up? (v0.1.0)

Follow-up to `PRIOR_ART.md`. That note established that other systems
reimplement `constraints -> scoring -> ranking` in domain-specific ways.
This note asks the sharper question it left open: does Fenlara actually
add something useful beyond `filter -> score -> first`, or is it an
over-formalized version of the same thing?

## Setup

One fixed pool of five offers, unchanged across every request below:

| Offer | Price | Latency (ms) | Trust | Availability |
|---|---|---|---|---|
| A | 0.40 | 900  | 0.91  | 0.98  |
| B | 2.50 | 200  | 0.99  | 0.995 |
| C | 1.20 | 500  | 0.96  | 0.99  |
| D | 4.00 | 100  | 0.999 | 0.999 |
| E | 0.80 | 3000 | 0.94  | 0.97  |

Five policies, expressed only as `SelectionRequest` objects, with zero
changes to `selection.py`:

| Policy | `SelectionRequest` | Chosen |
|---|---|---|
| `cheapest` | `{"preferences": {"price": 1.0}}` | **A** |
| `lowest_latency` | `{"preferences": {"latency": 1.0}}` | **D** |
| `most_trusted` | `{"preferences": {"trust": 1.0}}` | **D** |
| `balanced` | `{"preferences": {"price": .25, "latency": .25, "trust": .25, "availability": .25}}` | **B** |
| custom: availability floor 0.98, then trust-weighted | `{"constraints": {"min_availability": 0.98}, "preferences": {"trust": 0.8, "price": 0.2}}` | **None — every offer rejected** |

`lowest_latency` and `most_trusted` both land on D in this particular
pool, because D happens to dominate on both axes at once (fastest *and*
most trusted). That's a property of this dataset, not evidence against
the hypothesis — a pool where each criterion has a distinct winner would
demonstrate the differentiation more cleanly, and is worth re-running as
a follow-up.

## Findings

### 1. External policy works

Four of the five policies were expressed purely as data passed to
`select()`, with no knowledge of A2A, MCP, HTTP, or DNS, and no change
to Fenlara's own code. The same offer pool produced three different
winners (A, D, B) depending only on the declared policy — the core
claim ("same supply, different valid choice depending on the
requester") holds for every criterion Fenlara already treats as a
native preference.

### 2. Hard constraints are not yet generic

The fifth policy failed outright: `min_availability` is not one of the
four constraint keys `_constraint_reasons` recognizes
(`jurisdiction`, `max_price`, `max_latency_ms`, `required_protocol`), so
it was rejected fail-closed — correctly, per the documented contract,
but revealing every offer as a casualty rather than filtering to a
smaller survivor set.

This exposes a real asymmetry: `preferences` is already generic (any
key is scored against a same-named offer field via
`FIELD_BY_CRITERION.get(criterion, criterion)`), but `constraints` is a
closed, hardcoded enum. Expressing a hard floor on `trust` or
`availability` today requires modifying `selection.py` itself — which
is exactly the kind of abstraction leak the second half of this
experiment was designed to catch. This is kept here as a result, not
patched quietly: **the experiment produced a precise negative result**,
turning a vague "scoring policy abstraction" line item into a concrete,
scoped architectural problem — generalize the constraint mechanism to
accept arbitrary offer fields, symmetrically with preferences — for
whoever picks up v0.2.

### 3. Fail-closed + explicit warnings provide a concrete advantage

A direct comparison on the same data: a one-line hand-rolled selection
that most applications would actually write —

```python
min(offers, key=lambda o: o.get("price", 0))
```

— silently treats an offer with a missing `price` field as *free*, and
wrongly picks it. Given the same corrupted data, Fenlara scores the
missing attribute as the *worst* possible value instead, correctly
avoids that offer, picks the next valid one, and reports the reason
(`"A: missing 'price', scored 0"`) instead of failing silently. This
costs the caller nothing extra — no additional application code, just
using `select()` instead of the one-liner.

## Verdict

The experiment strengthens the case for Fenlara as a policy-driven
selection primitive, while exposing a concrete abstraction leak that
must be addressed before the API can be considered generic.
