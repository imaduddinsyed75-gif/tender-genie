from agents.adapter import build_compliance_report, build_pricing_estimate


def test_adapter_builds_compliance_and_pricing_outputs(monkeypatch) -> None:
    raw_text = (
        "[PAGE 3] Liquidated damages apply without a cap. "
        "[PAGE 7] Uptime of 99.95% is required. Firewall and security audit services are requested."
    )
    fake_boq = [
        {
            "item": "Firewall",
            "qty": 1.0,
            "unit_cost": 280000.0,
            "margin_pct": 20.0,
            "total": 336000.0,
        },
        {
            "item": "Security Audit",
            "qty": 1.0,
            "unit_cost": 560000.0,
            "margin_pct": 25.0,
            "total": 700000.0,
        },
    ]
    monkeypatch.setattr(
        "agents.adapter.run_pricing",
        lambda state: {"boq_items": fake_boq},
    )

    compliance = build_compliance_report({"raw_text": raw_text})
    pricing = build_pricing_estimate({"raw_text": raw_text})

    assert [flag["severity"] for flag in compliance["risk_flags"]] == ["Red", "Yellow"]
    assert [item["page"] for item in compliance["compliance_matrix"]] == [3, 7]
    assert all({"unit_rate_usd", "total_usd"} <= item.keys() for item in pricing["items"])
    assert pricing["final_bid_amount_usd"] == sum(
        item["total_usd"] for item in pricing["items"]
    )


def test_empty_raw_text_returns_empty_zero_pricing() -> None:
    result = build_pricing_estimate({"raw_text": ""})

    assert result["items"] == []
    assert result["boq_items"] == []
    assert result["subtotal_usd"] == 0
    assert result["final_bid_amount_usd"] == 0
