"""Tests for property observation stability analysis."""
from detection.property_observations import (
    analyze_property_stability,
    compute_context_hash,
    normalize_properties,
)


def test_normalize_properties_skips_empty():
    props = normalize_properties(
        {"automation_id": "num2Button", "role": "Button", "x": 10, "y": 20}
    )
    assert props["automation_id"] == "num2Button"
    assert "x" not in props


def test_stable_automation_id_after_three_same():
    obs = [
        {
            "context_hash": "abc",
            "run_id": "r1",
            "properties_json": '{"automation_id": "equalButton", "role": "Button"}',
        },
        {
            "context_hash": "abc",
            "run_id": "r2",
            "properties_json": '{"automation_id": "equalButton", "role": "Button"}',
        },
        {
            "context_hash": "abc",
            "run_id": "r3",
            "properties_json": '{"automation_id": "equalButton", "role": "Button"}',
        },
    ]
    stats = analyze_property_stability(obs)
    assert "automation_id" in stats["stable"]
    assert stats["samples"] == 3


def test_volatile_name_when_values_differ():
    obs = [
        {"properties_json": '{"name": "Estándar"}', "run_id": "1"},
        {"properties_json": '{"name": "Científica"}', "run_id": "2"},
        {"properties_json": '{"name": "Graficar"}', "run_id": "3"},
    ]
    stats = analyze_property_stability(obs)
    assert "name" in stats["volatile"]


def test_context_hash_deterministic():
    a = compute_context_hash(app_id="x", framework="uwp")
    b = compute_context_hash(app_id="x", framework="uwp")
    assert a == b
