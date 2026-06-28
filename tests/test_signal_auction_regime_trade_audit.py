from __future__ import annotations

from axontrade.research import (
    SIGNAL_AUCTION_REGIME_TRADE_AUDIT_HEADER,
    audit_signal_auction_regime_trades,
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


def _selection_row(
    *,
    split_id: str = "window=1",
    sample: str,
    trade_dates: str,
) -> dict[str, object]:
    return {
        "split_id": split_id,
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


def test_audits_target_r_stack_trades_and_duplicates() -> None:
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
    selection_rows = [
        _selection_row(split_id="window=1", sample="train", trade_dates="2026-06-10;2026-06-11"),
        _selection_row(split_id="window=1", sample="holdout", trade_dates="2026-06-12"),
        _selection_row(split_id="window=2", sample="train", trade_dates="2026-06-10;2026-06-11"),
        _selection_row(split_id="window=2", sample="holdout", trade_dates="2026-06-12"),
    ]

    audit_rows = audit_signal_auction_regime_trades(
        bars=bars,
        signal_rows=signal_rows,
        regime_rows=regime_rows,
        selection_rows=selection_rows,
        stack_type="target_r",
        target_r_multiples=[1, 2],
        minimum_train_trades=2,
    )

    assert list(audit_rows[0].keys()) == SIGNAL_AUCTION_REGIME_TRADE_AUDIT_HEADER
    holdout_rows = [row for row in audit_rows if row["sample"] == "holdout"]
    assert [row["decision"] for row in holdout_rows] == [
        "evaluated",
        "auction_skipped",
        "evaluated",
        "auction_skipped",
    ]
    evaluated_rows = [row for row in holdout_rows if row["decision"] == "evaluated"]
    assert [row["sample_signal_occurrence"] for row in evaluated_rows] == [1, 2]
    assert all(row["sample_duplicate_signal"] == "true" for row in evaluated_rows)
    assert all(row["selected_target_r_multiple"] == "2" for row in evaluated_rows)
    assert all(row["selected_exit_reason"] == "target_hit" for row in evaluated_rows)


def test_audits_breakeven_stack_trade() -> None:
    bars = []
    signal_rows = []
    regime_rows = []
    for index, trade_date in enumerate(("2026-06-10", "2026-06-11", "2026-06-12"), start=1):
        bars.extend(
            [
                _bar(trade_date, 0, high=100, low=99.75, close=100),
                _bar(trade_date, 1, high=101.25, low=100.5, close=101),
                _bar(trade_date, 2, high=101.25, low=99.75, close=100),
            ],
        )
        signal_rows.append(_candidate(index, trade_date))
        regime_rows.append(_regime_row(index, trade_date))

    audit_rows = audit_signal_auction_regime_trades(
        bars=bars,
        signal_rows=signal_rows,
        regime_rows=regime_rows,
        selection_rows=[
            _selection_row(sample="train", trade_dates="2026-06-10;2026-06-11"),
            _selection_row(sample="holdout", trade_dates="2026-06-12"),
        ],
        stack_type="breakeven",
        target_r_multiples=[1.5],
        breakeven_trigger_r_multiples=[1],
        minimum_train_trades=2,
    )

    holdout_rows = [row for row in audit_rows if row["sample"] == "holdout"]
    assert len(holdout_rows) == 1
    assert holdout_rows[0]["decision"] == "evaluated"
    assert holdout_rows[0]["selected_breakeven_trigger_r"] == "1"
    assert holdout_rows[0]["selected_exit_reason"] == "breakeven_stop_hit"
    assert holdout_rows[0]["selected_net_usd"] == "-28.5"
