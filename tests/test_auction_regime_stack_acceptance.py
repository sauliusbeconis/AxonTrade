from __future__ import annotations

import pytest

from axontrade.config import ConfigError
from axontrade.research import (
    AuctionRegimeStackAcceptanceError,
    auction_regime_stack_acceptance_passed,
    evaluate_auction_regime_stack_acceptance,
    load_auction_regime_stack_acceptance_config,
    render_auction_regime_stack_acceptance_report,
    summarize_auction_regime_stack_sample,
    validate_auction_regime_stack_acceptance_config,
)


def test_loads_default_auction_regime_stack_acceptance_config() -> None:
    config = load_auction_regime_stack_acceptance_config()

    assert config["profile_id"] == "auction_regime_stack_acceptance_gates_v1"
    assert config["gates"]["minimum_unique_holdout_evaluated_signals"] == 30


def test_acceptance_passes_when_all_gates_pass() -> None:
    findings = evaluate_auction_regime_stack_acceptance(
        _audit_rows(30, trade_dates=15, net_usd=10),
        config=_config(),
    )

    assert auction_regime_stack_acceptance_passed(findings)
    assert all(finding.passed for finding in findings)


def test_acceptance_fails_underpowered_single_survivor() -> None:
    audit_rows = [
        _audit_row(
            "signal-1",
            trade_date="2026-06-17",
            net_usd=171.50,
            duplicate=True,
        ),
        _audit_row(
            "signal-1",
            trade_date="2026-06-17",
            net_usd=221.50,
            duplicate=True,
        ),
    ]
    findings = evaluate_auction_regime_stack_acceptance(
        audit_rows,
        config=_config(),
    )
    summary = summarize_auction_regime_stack_sample(audit_rows, config=_config())

    by_gate = {finding.gate_id: finding for finding in findings}

    assert not auction_regime_stack_acceptance_passed(findings)
    assert by_gate["minimum_unique_holdout_evaluated_signals"].passed is False
    assert by_gate["minimum_unique_holdout_trade_dates"].passed is False
    assert by_gate["maximum_duplicate_holdout_evaluated_rows"].passed is False
    assert by_gate["positive_unique_holdout_net"].passed is True
    assert by_gate["maximum_single_signal_net_share"].passed is False
    assert summary.unique_holdout_evaluated_signals == 1
    assert summary.unique_holdout_trade_dates == 1
    assert summary.additional_unique_signals_required == 29
    assert summary.additional_trade_dates_required == 14
    assert summary.duplicate_rows_to_remove == 2


def test_renders_auction_regime_stack_acceptance_report() -> None:
    audit_rows = [_audit_row("signal-1", trade_date="2026-06-17", net_usd=221.50)]
    findings = evaluate_auction_regime_stack_acceptance(audit_rows, config=_config())
    summary = summarize_auction_regime_stack_sample(audit_rows, config=_config())

    report = render_auction_regime_stack_acceptance_report(
        findings,
        config=_config(),
        sources={"audit": "audit.csv"},
        sample_summary=summary,
    )

    assert "# Auction-Regime Stack Acceptance Report" in report
    assert "| Overall status | FAIL |" in report
    assert "| FAIL | minimum_unique_holdout_evaluated_signals | 1 | >= 30 |" in report
    assert "## Sample Coverage" in report
    assert "| Additional unique signals required | 29 |" in report
    assert "| Additional trade dates required | 14 |" in report


def test_rejects_invalid_acceptance_config() -> None:
    config = _config()
    config["gates"]["maximum_single_signal_net_share"] = 1.5

    with pytest.raises(ConfigError, match="maximum_single_signal_net_share"):
        validate_auction_regime_stack_acceptance_config(config)


def test_rejects_non_numeric_audit_net() -> None:
    row = _audit_row("signal-1", trade_date="2026-06-17", net_usd=1)
    row["selected_net_usd"] = "bad"

    with pytest.raises(AuctionRegimeStackAcceptanceError, match="selected_net_usd"):
        evaluate_auction_regime_stack_acceptance([row], config=_config())


def _config() -> dict[str, object]:
    return {
        "schema_version": 1,
        "profile_id": "test_auction_regime_stack_acceptance",
        "gates": {
            "minimum_unique_holdout_evaluated_signals": 30,
            "minimum_unique_holdout_trade_dates": 15,
            "maximum_duplicate_holdout_evaluated_rows": 0,
            "require_positive_unique_holdout_net": True,
            "maximum_single_signal_net_share": 0.25,
        },
    }


def _audit_rows(count: int, *, trade_dates: int, net_usd: float) -> list[dict[str, str]]:
    return [
        _audit_row(
            f"signal-{index}",
            trade_date=f"2026-06-{(index % trade_dates) + 1:02d}",
            net_usd=net_usd,
        )
        for index in range(count)
    ]


def _audit_row(
    signal_id: str,
    *,
    trade_date: str,
    net_usd: float,
    duplicate: bool = False,
) -> dict[str, str]:
    return {
        "sample": "holdout",
        "decision": "evaluated",
        "signal_id": signal_id,
        "trade_date": trade_date,
        "selected_net_usd": str(net_usd),
        "sample_duplicate_signal": str(duplicate).lower(),
    }
