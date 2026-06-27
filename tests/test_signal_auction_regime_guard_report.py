from __future__ import annotations

from axontrade.research import (
    SIGNAL_AUCTION_REGIME_GUARD_REPORT_HEADER,
    report_signal_auction_regime_guard,
)


def _regime_row(
    index: int,
    *,
    trade_date: str,
    vwap_stretch: float,
    exit_reason: str = "target_hit",
    net_usd: float = 100.0,
) -> dict[str, object]:
    return {
        "signal_id": f"signal-{index}",
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


def _selection_row() -> dict[str, object]:
    return {
        "split_id": "window=1",
        "sample": "holdout",
        "selected_on_train": "true",
        "trade_dates": "2026-06-10",
        "experiment_id": "rule-1",
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


def test_reports_accepted_and_skipped_auction_regime_guard_rows() -> None:
    report_rows = report_signal_auction_regime_guard(
        regime_rows=[
            _regime_row(1, trade_date="2026-06-10", vwap_stretch=5, net_usd=100),
            _regime_row(
                2,
                trade_date="2026-06-10",
                vwap_stretch=20,
                exit_reason="stop_hit",
                net_usd=-50,
            ),
        ],
        selection_rows=[_selection_row()],
    )

    assert list(report_rows[0].keys()) == SIGNAL_AUCTION_REGIME_GUARD_REPORT_HEADER
    assert report_rows[0]["accepted_trades"] == 1
    assert report_rows[0]["skipped_trades"] == 1
    assert report_rows[0]["target_hits"] == 1
    assert report_rows[0]["skipped_losses"] == 1
    assert report_rows[0]["net_usd"] == "100"
    assert report_rows[0]["skipped_net_usd"] == "-50"
    assert report_rows[0]["total_net_usd"] == "50"


def test_guard_report_can_skip_unselected_rows() -> None:
    unselected = _selection_row()
    unselected["selected_on_train"] = "false"

    report_rows = report_signal_auction_regime_guard(
        regime_rows=[_regime_row(1, trade_date="2026-06-10", vwap_stretch=5)],
        selection_rows=[unselected],
    )

    assert report_rows == []
