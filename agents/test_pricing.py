import pytest

from agents.pricing import compute_tiers, recalc_boq, run_pricing, sla_stress_test


BASE_BOQ = [
    {
        "item": "Firewall appliance",
        "qty": 2,
        "unit_cost": 100000,
        "margin_pct": 20,
        "total": 240000,
    }
]


def test_recalc_boq_applies_margin_and_recomputes_total() -> None:
    totals = [recalc_boq(BASE_BOQ, margin)[0]["total"] for margin in (15, 25, 35)]

    assert totals == pytest.approx([230000, 250000, 270000])


def test_compute_tiers_are_ordered_by_grand_total() -> None:
    tiers = compute_tiers(BASE_BOQ)

    assert (
        tiers["optimistic"]["grand_total"]
        < tiers["expected"]["grand_total"]
        < tiers["conservative"]["grand_total"]
    )


def test_sla_stress_test_calculates_daily_penalty() -> None:
    result = sla_stress_test(10_000_000, 0.5, 14)

    assert result["penalty_amount"] == 700_000


def test_empty_memory_adds_user_input_marker(monkeypatch) -> None:
    monkeypatch.setattr(
        "agents.pricing.query_similar",
        lambda text, k, only_won: [],
    )

    result = run_pricing({"extracted_text": "A bespoke requirement."})

    assert result["boq_items"]
    assert all("[USER INPUT REQUIRED]" in item["item"] for item in result["boq_items"])


def test_nonsense_item_adds_user_input_marker_with_real_memory() -> None:
    result = run_pricing(
        {"extracted_tables": [{"item": "wedding catering", "quantity": 1}]}
    )

    assert result["boq_items"][0]["item"] == "wedding catering [USER INPUT REQUIRED]"


def test_security_audit_gets_real_rate_from_memory() -> None:
    result = run_pricing(
        {"extracted_tables": [{"item": "Security Audit", "quantity": 1}]}
    )

    assert result["boq_items"][0]["unit_cost"] > 0
    assert "[USER INPUT REQUIRED]" not in result["boq_items"][0]["item"]


def test_network_switch_uses_closest_historical_rate() -> None:
    result = run_pricing(
        {"extracted_tables": [{"item": "Network Switch", "quantity": 1}]}
    )

    assert result["boq_items"][0]["unit_cost"] == 1_480_000


def test_title_case_items_get_real_rates_from_memory() -> None:
    result = run_pricing(
        {
            "extracted_tables": [
                {"item": "Penetration Test", "quantity": 1},
                {"item": "Network Switch", "quantity": 1},
            ]
        }
    )

    assert all(item["unit_cost"] > 0 for item in result["boq_items"])
    assert all("[USER INPUT REQUIRED]" not in item["item"] for item in result["boq_items"])
