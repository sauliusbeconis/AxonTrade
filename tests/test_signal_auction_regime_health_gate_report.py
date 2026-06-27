from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_AUCTION_REGIME_HEALTH_GATE_REPORT_HEADER,
    SignalAuctionRegimeHealthGateReportError,
    report_signal_auction_regime_health_gate,
)


def _regime_row(
    index: int,
    *,
    trade_date: str,
    vwap_stretch: float = 5,
    exit_reason: str = "target_hit",
    net_usd: float = 100,
) -> dict[str, object]:
    return {
        "signal_id": f"test_strategy_ESU26-CME_{index}",
        "symbol": "ESU26-CME",
        "direction": "long",
        "entry_time": f"{trade_date} 10:00:00",
        "original_reward_risk": "2",
        "minutes_after_rth_open": "30",
        "session_range_points": "20",
        "fade_edge_score": "0.75",
        "direction_aware_vwap_stretch_points": vwap_stretch,
        "direction_aware_open_stretch_points": "5",
        "exit_reason": exit_reason,
        "net_usd": net_usd,
    }


def _selection_row(*, sample: str, trade_dates: str) -> dict[str, object]:
    return {
        "split_id": "window=1",
        "sample": sample,
        "selected_on_train": "true",
        "trade_dates": trade_dates,
        "experiment_id": "auction-rule-1",
        "strategy_id": "test_strategy",
        "direction_filter": "all",
        "max_original_reward_risk": "3",
        "min_minutes_after_rth_open": "0",
        "max_minutes_after_rth_open": "120",
        "max_session_range_points": "30",
        "max_fade_edge_score": "0.85",
        "max_vwap_stretch_points": "10",
        "max_open_stretch_points": "10",
    }


def _report(
    rows: list[dict[str, object]],
    *,
    maximum_consecutive_losses: list[int] | None = None,
) -> list[dict[str, object]]:
    return report_signal_auction_regime_health_gate(
        regime_rows=rows,
        selection_rows=[
            _selection_row(sample="train", trade_dates="2026-06-10;2026-06-11"),
            _selection_row(sample="holdout", trade_dates="2026-06-12"),
        ],
        maximum_daily_losses=[999],
        daily_loss_limits_usd=[999999],
        maximum_consecutive_losses=maximum_consecutive_losses or [999],
        consecutive_loss_pause_trade_dates=[1],
        maximum_equity_drawdowns_usd=[999999],
        drawdown_pause_trade_dates=[0],
        minimum_train_accepted_trades=2,
    )


def test_reports_auction_skips_and_final_health_gate_outcomes() -> None:
    rows = [
        _regime_row(1, trade_date="2026-06-10", net_usd=100),
        _regime_row(2, trade_date="2026-06-11", net_usd=100),
        _regime_row(
            3,
            trade_date="2026-06-11",
            vwap_stretch=20,
            exit_reason="stop_hit",
            net_usd=-200,
        ),
        _regime_row(
            4,
            trade_date="2026-06-12",
            exit_reason="stop_hit",
            net_usd=-50,
        ),
        _regime_row(5, trade_date="2026-06-12", vwap_stretch=20, net_usd=500),
    ]

    report_rows = _report(rows)

    assert list(report_rows[0].keys()) == SIGNAL_AUCTION_REGIME_HEALTH_GATE_REPORT_HEADER
    assert [row["sample"] for row in report_rows] == ["train", "holdout"]
    assert report_rows[0]["accepted_trades"] == 2
    assert report_rows[0]["auction_skipped_trades"] == 1
    assert report_rows[0]["auction_skipped_losses"] == 1
    assert report_rows[0]["auction_skipped_net_usd"] == "-200"
    assert report_rows[1]["accepted_trades"] == 1
    assert report_rows[1]["losses"] == 1
    assert report_rows[1]["net_usd"] == "-50"
    assert report_rows[1]["auction_skipped_trades"] == 1
    assert report_rows[1]["auction_skipped_target_hits"] == 1
    assert report_rows[1]["auction_skipped_net_usd"] == "500"
    assert report_rows[1]["total_candidate_net_usd"] == "450"


def test_health_gate_warms_holdout_from_auction_eligible_train_rows() -> None:
    rows = [
        _regime_row(1, trade_date="2026-06-10", net_usd=100),
        _regime_row(2, trade_date="2026-06-11", exit_reason="stop_hit", net_usd=-100),
        _regime_row(3, trade_date="2026-06-12", net_usd=500),
    ]

    report_rows = _report(rows, maximum_consecutive_losses=[1])

    assert report_rows[1]["state_warmup_rows"] == 2
    assert report_rows[1]["accepted_trades"] == 0
    assert report_rows[1]["health_skipped_trades"] == 1
    assert report_rows[1]["health_skipped_target_hits"] == 1
    assert report_rows[1]["health_skipped_net_usd"] == "500"


def test_requires_selected_train_and_holdout_rows() -> None:
    with pytest.raises(SignalAuctionRegimeHealthGateReportError, match="selected holdout"):
        report_signal_auction_regime_health_gate(
            regime_rows=[_regime_row(1, trade_date="2026-06-10")],
            selection_rows=[
                _selection_row(sample="train", trade_dates="2026-06-10"),
            ],
            maximum_daily_losses=[999],
            daily_loss_limits_usd=[999999],
            maximum_consecutive_losses=[999],
            consecutive_loss_pause_trade_dates=[0],
            maximum_equity_drawdowns_usd=[999999],
            drawdown_pause_trade_dates=[0],
        )
