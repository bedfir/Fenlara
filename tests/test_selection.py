"""Tests for fenlara.select — see selection.py's module docstring for the
design contract each of these enforces."""

import pytest

from fenlara import select


@pytest.fixture
def baseline():
    offers = [
        {"offer_id": "agent-a", "agent_id": "agent-a", "trust": 0.99, "price": 2.50,
         "latency_ms": 2000, "jurisdiction": "EU", "protocol": "a2a"},
        {"offer_id": "agent-b", "agent_id": "agent-b", "trust": 0.97, "price": 0.40,
         "latency_ms": 15000, "jurisdiction": "EU", "protocol": "a2a"},
        {"offer_id": "agent-c", "agent_id": "agent-c", "trust": 0.999, "price": 5.00,
         "latency_ms": 3000, "jurisdiction": "EU", "protocol": "a2a"},
        {"offer_id": "agent-d", "agent_id": "agent-d", "trust": 0.94, "price": 0.00,
         "latency_ms": 4000, "jurisdiction": "US", "protocol": "a2a"},
    ]
    request = {
        "constraints": {"jurisdiction": "EU", "max_price": 3.00, "max_latency_ms": 5000},
        "preferences": {"trust": 0.7, "price": 0.2, "latency": 0.1},
    }
    return offers, request


def test_baseline_translation_example(baseline):
    offers, request = baseline
    r = select(offers, request)
    assert "agent-d" in r["rejections"]
    assert "agent-c" in r["rejections"]
    assert r["chosen"]["offer_id"] in ("agent-a", "agent-b")
    assert set(r["chosen"]) == {"offer_id", "agent_id"}
    assert set(r["scores"][r["chosen"]["offer_id"]]) >= {"trust", "price", "latency", "total"}


def test_exact_tie_resolved_lexicographically():
    tied = [
        {"offer_id": "x", "agent_id": "agent-x", "trust": 0.9, "price": 1.0, "latency_ms": 100},
        {"offer_id": "y", "agent_id": "agent-y", "trust": 0.9, "price": 1.0, "latency_ms": 100},
    ]
    r = select(tied, {"preferences": {"trust": 1.0}})
    assert r["chosen"]["offer_id"] == "x"
    assert r.get("tie_with") == ["y"]


def test_missing_constraint_attribute_rejects_offer():
    missing_attr = [{"offer_id": "no-price", "agent_id": "agent-1", "trust": 0.9}]
    r = select(missing_attr, {"constraints": {"max_price": 2.0}})
    assert "no-price" in r["rejections"]
    assert "missing attribute: price" in r["rejections"]["no-price"]


def test_missing_preference_attribute_survives_scored_zero():
    r = select([{"offer_id": "unpriced", "agent_id": "agent-1", "trust": 0.9}],
               {"preferences": {"price": 1.0}})
    assert r["chosen"]["offer_id"] == "unpriced"
    assert any("missing 'price'" in w for w in r["warnings"])


def test_missing_trust_preference_still_yields_decision():
    r = select([{"offer_id": "untrusted-unknown", "agent_id": "agent-1", "price": 1.0}],
               {"preferences": {"trust": 1.0}})
    assert r["chosen"]["offer_id"] == "untrusted-unknown"


def test_non_normalized_weights_still_produce_valid_decision(baseline):
    offers, request = baseline
    r = select(offers, {**request, "preferences": {"trust": 7, "price": 2, "latency": 1}})
    assert r["chosen"]["offer_id"] in ("agent-a", "agent-b")


def test_all_offers_rejected_yields_none(baseline):
    offers, _ = baseline
    r = select(offers, {"constraints": {"jurisdiction": "JP"}})
    assert r["chosen"] is None
    assert "all offers rejected by hard constraints" in r["warnings"]


def test_no_preferences_ties_broken_by_offer_id(baseline):
    offers, _ = baseline
    r = select(offers, {"constraints": {"jurisdiction": "EU"}})
    assert r["chosen"]["offer_id"] == "agent-a"


def test_single_offer_trivially_chosen():
    r = select([{"offer_id": "only-one", "agent_id": "agent-1", "trust": 0.5}],
               {"preferences": {"trust": 1.0}})
    assert r["chosen"]["offer_id"] == "only-one"


def test_required_protocol_constraint_filters():
    protocol_offers = [
        {"offer_id": "a2a-offer", "agent_id": "agent-1", "protocol": "a2a"},
        {"offer_id": "anp-offer", "agent_id": "agent-2", "protocol": "anp"},
    ]
    r = select(protocol_offers, {"constraints": {"required_protocol": "anp"}})
    assert r["chosen"]["offer_id"] == "anp-offer"
    assert "a2a-offer" in r["rejections"]


def test_unrecognized_constraint_key_fails_closed():
    r = select([{"offer_id": "z", "agent_id": "agent-1"}], {"constraints": {"made_up_field": "x"}})
    assert "z" in r["rejections"]


def test_published_values_are_trusted_as_is():
    """Documented limitation: Fenlara has no way to catch a false published
    value — that is a discovery/evidence problem, not a selection problem."""
    lying = [
        {"offer_id": "honest", "agent_id": "agent-1", "trust": 0.6},
        {"offer_id": "liar", "agent_id": "agent-2", "trust": 1.0},
    ]
    r = select(lying, {"preferences": {"trust": 1.0}})
    assert r["chosen"]["offer_id"] == "liar"


def test_offers_from_same_agent_compared_independently():
    same_agent = [
        {"offer_id": "offer-cheap", "agent_id": "agent-1", "price": 0.10, "latency_ms": 5000},
        {"offer_id": "offer-fast", "agent_id": "agent-1", "price": 3.00, "latency_ms": 50},
        {"offer_id": "offer-standard", "agent_id": "agent-2", "price": 1.00, "latency_ms": 1000},
    ]
    r = select(same_agent, {"preferences": {"latency": 1.0}})
    assert {"offer-cheap", "offer-fast", "offer-standard"} <= set(r["scores"])
    assert r["chosen"]["offer_id"] == "offer-fast"
    assert r["chosen"]["agent_id"] == "agent-1"

    r2 = select(same_agent, {"preferences": {"price": 1.0}})
    assert r2["chosen"]["offer_id"] == "offer-cheap"
    assert r2["chosen"]["agent_id"] == "agent-1"


def test_missing_agent_id_raises():
    try:
        select([{"offer_id": "offer-1", "price": 1.0}], {"preferences": {"price": 1.0}})
        assert False, "expected ValueError"
    except ValueError as e:
        assert "agent_id" in str(e)


def test_missing_offer_id_raises():
    try:
        select([{"agent_id": "agent-1", "price": 1.0}], {"preferences": {"price": 1.0}})
        assert False, "expected ValueError"
    except ValueError as e:
        assert "offer_id" in str(e)
