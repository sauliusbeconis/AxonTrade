from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_AUCTION_REGIME_BREAKEVEN_REPORT_HEADER,
    SignalAuctionRegimeBreakevenReportError,
    report_signal_auction_regime_breakeven,
)


def _bar(
    trade_date: str,
    bar_index: int,
    *,
    high: float,
    low: float,
    close: float,
) -> dict[str, object]:
    return {
        "timestamp": f"{trade_date} 10:0{bar_index}:00",
        "symbol": "ESU26-CME",
        "bar_index": bar_index,
        "high": high,
        "low": low,
        "close": close,
    }


def _candidate(index: int, trade_date: str) -> dict[str, object]:
    return {
        "event_type": "candidate_signal",
        "event_key": f"ESU26-CME:1:{trade_date}:test:candidate_signal:long",
        "strategy_id": "test_strategy",
        "signal_id": f"test_strategy_ESU26-CME_{index}",
        "symbol": "ESU26-CME",
        "bar_index": 0,
        "bar_start_time": f"{trade_date} 10:00:00",
        "direction": "long",
        "signal_price": "100",
        "stop_price": "99",
        "target_price": "104",
    }


def _regime_row(
    index: int,
    trade_date: str,
    *,
    vwap_stretch: float = 5,
    exit_reason: str = "target_hit",
    net_usd: float = 100,
) -> dict[str, object]:
    return {
        "signal_id": f"test_strategy_ESU26-CME_{index}",
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


def test_reports_breakeven_exit_selected_after_auction_guard() -> None:
    bars = []
    signal_rows = []
    regime_rows = []
    for index, trade_date in enumerate(("2026-06-10", "2026-06-11", "2026-06-12"), start=1):
        bars.extend(
            [
                _bar(trade_date, 0, high=100, low=99.75, close=100),
                _bar(trade_date, 1, high=102.25, low=100.5, close=102),
            ],
        )
        signal_rows.append(_candidate(index, trade_date))
        regime_rows.append(_regime_row(index, trade_date))
    regime_rows.append(
        _regime_row(
            4,
            "2026-06-12",
            vwap_stretch=20,
            exit_reason="stop_hit",
            net_usd=-200,
        ),
    )

    report_rows = report_signal_auction_regime_breakeven(
        bars=bars,
        signal_rows=signal_rows,
        regime_rows=regime_rows,
        selection_rows=[
            _selection_row(sample="train", trade_dates="2026-06-10;2026-06-11"),
            _selection_row(sample="holdout", trade_dates="2026-06-12"),
        ],
        target_r_multiples=[1.5, 2],
        breakeven_trigger_r_multiples=[1],
        minimum_train_trades=2,
    )

    assert list(report_rows[0].keys()) == SIGNAL_AUCTION_REGIME_BREAKEVEN_REPORT_HEADER
    assert [row["sample"] for row in report_rows] == ["train", "holdout"]
    assert report_rows[0]["target_r_multiple"] == "2"
    assert report_rows[0]["breakeven_trigger_r"] == "1"
    assert report_rows[1]["evaluated_trades"] == 1
    assert report_rows[1]["target_hits"] == 1
    assert report_rows[1]["breakeven_exits"] == 0
    assert report_rows[1]["auction_skipped_trades"] == 1
    assert report_rows[1]["auction_skipped_net_usd"] == "-200"


def test_requires_train_breakeven_rows_to_meet_minimum() -> None:
    with pytest.raises(SignalAuctionRegimeBreakevenReportError, match="minimum_train_trades"):
        report_signal_auction_regime_breakeven(
            bars=[],
            signal_rows=[_candidate(1, "2026-06-10")],
            regime_rows=[_regime_row(1, "2026-06-10")],
            selection_rows=[
                _selection_row(sample="train", trade_dates="2026-06-10"),
                _selection_row(sample="holdout", trade_dates="2026-06-11"),
            ],
            target_r_multiples=[1.5],
            breakeven_trigger_r_multiples=[1],
            minimum_train_trades=2,
        )
