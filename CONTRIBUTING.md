# Contributing to Fenlara

Fenlara is intentionally small. Before proposing a change, it's worth
re-reading the "What Fenlara does not do" section of the README — most
feature requests that sound reasonable in isolation (capability matching,
trust computation, endpoint verification, networking) belong in a
different layer on purpose. If in doubt, open an issue before a PR.

## Setup

```bash
git clone git@github.com:bedfir/Fenlara.git
cd fenlara
pip install -e ".[dev]"
pytest
```

No network access, no external services, and no LLM are required to
develop or test Fenlara — if a change you're making needs any of those,
that's a signal it may not belong in this repository.

## Design questions vs. bugs

- **Bug** (wrong output for a case the contract already covers): open a
  PR directly, with a failing test added first.
- **Design question** (anything that changes the `select()` contract,
  the scoring model, or what counts as a constraint vs. a preference):
  open an issue first. See `agent-selection-layer-problem-statement.md`
  for the reasoning behind the current contract, and check whether your
  question is already one of the open design questions noted there or
  in the README.

## Tests

Every behavioral decision documented in `selection.py`'s module
docstring should have a corresponding test in `tests/test_selection.py`.
If you change a decision, update the docstring and the test together —
they're meant to stay in sync.

## Schemas

`schema/*.json` describe the data contracts, not the engine's internal
logic. If your change adds a new field or changes what a field means,
update the relevant schema in the same PR, and re-run the cross-validation
(schema against real `select()` output) rather than just checking the
schema is syntactically valid.

## License

By contributing, you agree your contribution is licensed under the
project's Apache License 2.0 (see `LICENSE`).
