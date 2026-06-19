from __future__ import annotations

from axontrade.reports import render_price_only_outcome_report


def test_renders_price_only_outcome_report() -> None:
    signals = [
        {
            "event_type": "candidate_signal",
            "strategy_id": "price_only_test",
            "direction": "long",
            "rejection_reason": "not_applicable",
        },
        {
            "event_type": "rejected_signal",
            "strategy_id": "price_only_test",
            "direction": "none",
            "rejection_reason": "no_setup",
        },
    ]
    outcomes = [
        {
            "direction": "long",
            "exit_reason": "target_hit",
            "gross_usd": "200",
            "net_usd": "171.5",
        },
    ]

    report = render_price_only_outcome_report(
        signals,
        outcomes,
        signals_source="data/processed/signals.csv",
        outcomes_source="data/processed/outcomes.csv",
    )

    assert "# Price-Only Outcome Report" in report
    assert "| Total signal rows | 2 |" in report
    assert "| Candidate signals | 1 |" in report
    assert "| Rejected signals | 1 |" in report
    assert "| Target hits | 1 |" in report
    assert "| Net USD | 171.50 |" in report
    assert "| price_only_test | 2 |" in report
    assert "| long | 1 | 171.50 |" in report
    assert "| no_setup | 1 |" in report


def test_interprets_empty_candidate_sample() -> None:
    report = render_price_only_outcome_report(
        [{"event_type": "rejected_signal", "rejection_reason": "no_setup"}],
        [],
        signals_source="signals.csv",
        outcomes_source="outcomes.csv",
    )

    assert "No candidate trades were generated in this sample." in report
