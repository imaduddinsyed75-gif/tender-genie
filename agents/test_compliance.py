from agents.compliance import scan_rules


SAMPLE_TEXT = (
    "[PAGE 3] The vendor shall pay liquidated damages of 2% per day. "
    "[PAGE 7] Uptime of 99.95% is required. Payment within 120 days net. "
    "[PAGE 9] Sub-contracting is strictly prohibited. Bidder must hold ISO 27001."
)


def test_scan_rules_classifies_sample_items_by_risk_and_page() -> None:
    items = scan_rules(SAMPLE_TEXT)

    classified = {(item.category, item.risk_level, item.page) for item in items}

    assert classified == {
        ("Liquidated damages", "RED", 3),
        ("Service levels", "YELLOW", 7),
        ("Payment terms", "YELLOW", 7),
        ("Sub-contracting", "RED", 9),
        ("Certifications and registration", "RED", 9),
    }


def test_payment_within_30_days_is_not_flagged() -> None:
    items = scan_rules("[PAGE 2] Payment within 30 days net.")

    assert not any(item.category == "Payment terms" for item in items)


def test_uptime_below_99_9_percent_is_not_flagged() -> None:
    items = scan_rules("[PAGE 2] Uptime of 99.0% is required.")

    assert not any(item.category == "Service levels" for item in items)


def test_capped_liquidated_damages_are_yellow() -> None:
    items = scan_rules(
        "[PAGE 4] Liquidated damages of 2% per day, capped at 10% of contract value."
    )

    liquidated_damages = [item for item in items if item.category == "Liquidated damages"]
    assert len(liquidated_damages) == 1
    assert liquidated_damages[0].risk_level == "YELLOW"
    assert liquidated_damages[0].mitigation == "Cap exists, verify percentage is acceptable"


def test_text_without_page_markers_uses_page_one() -> None:
    items = scan_rules("Sub-contracting is strictly prohibited.")

    assert items
    assert all(item.page == 1 for item in items)


def test_unrelated_child_safety_text_is_not_liquidated_damages() -> None:
    items = scan_rules("The contractor shall hold the world record for child safety.")

    assert not any(item.category == "Liquidated damages" for item in items)
