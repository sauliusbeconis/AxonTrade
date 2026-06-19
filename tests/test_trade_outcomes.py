from __future__ import annotations

import pytest

from axontrade.research import (
    TRADE_OUTCOME_DAILY_CSV_HEADER,
    TradeOutcomeError,
    evaluate_trade_outcomes,
    summarize_trade_outcomes_by_day,
    summarize_trade_outcomes,
)


def _bar(
    bar_index: int,
    *,
    timestamp: str,
    high: float,
    low: float,
    close: float,
    symbol: str = "ESU26-CME",
) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "symbol": symbol,
        "bar_index": bar_index,
        "high": high,
        "low": low,
        "close": close,
    }


def _signal(
    bar_index: int,
    *,
    direction: str,
    entry: float,
    stop: float,
    target: float,
    symbol: str = "ESU26-CME",
) -> dict[str, object]:
    return {
        "event_type": "candidate_signal",
        "event_key": f"{symbol}:1:{bar_index}:strategy:candidate_signal:{direction}",
        "signal_id": f"strategy_{symbol}_{bar_index}",
        "symbol": symbol,
        "bar_index": bar_index,
        "bar_start_time": f"2026-06-19 10:{bar_index:02d}:00",
        "direction": direction,
        "signal_price": entry,
        "stop_price": stop,
        "target_price": target,
    }


def test_evaluates_long_target_hit_after_costs() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=102, low=100, close=101),
        _bar(1, timestamp="2026-06-19 10:01:00", high=105, low=101, close=104),
    ]
    signals = [_signal(0, direction="long", entry=101, stop=99, target=105)]

    outcomes = evaluate_trade_outcomes(bars, signals)

    assert outcomes[0]["exit_reason"] == "target_hit"
    assert outcomes[0]["exit_price"] == "105"
    assert outcomes[0]["gross_points"] == "4"
    assert outcomes[0]["gross_usd"] == "200"
    assert outcomes[0]["commission_usd"] == "3.5"
    assert outcomes[0]["slippage_usd"] == "25"
    assert outcomes[0]["net_usd"] == "171.5"
    assert outcomes[0]["r_multiple"] == "2"


def test_evaluates_short_stop_hit() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=101, low=99, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=102, low=98, close=99),
    ]
    signals = [_signal(0, direction="short", entry=100, stop=102, target=96)]

    outcomes = evaluate_trade_outcomes(bars, signals)

    assert outcomes[0]["exit_reason"] == "stop_hit"
    assert outcomes[0]["exit_price"] == "102"
    assert outcomes[0]["gross_points"] == "-2"
    assert outcomes[0]["net_usd"] == "-128.5"
    assert outcomes[0]["r_multiple"] == "-1"


def test_same_bar_stop_and_target_uses_conservative_stop_first() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=102, low=100, close=101),
        _bar(1, timestamp="2026-06-19 10:01:00", high=105, low=99, close=104),
    ]
    signals = [_signal(0, direction="long", entry=101, stop=99, target=105)]

    outcomes = evaluate_trade_outcomes(bars, signals)

    assert outcomes[0]["exit_reason"] == "ambiguous_stop_first"
    assert outcomes[0]["exit_price"] == "99"
    assert outcomes[0]["gross_points"] == "-2"


def test_summarizes_trade_outcomes() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=102, low=100, close=101),
        _bar(1, timestamp="2026-06-19 10:01:00", high=105, low=101, close=104),
        _bar(2, timestamp="2026-06-19 10:02:00", high=106, low=101, close=102),
    ]
    signals = [
        _signal(0, direction="long", entry=101, stop=99, target=105),
        _signal(1, direction="long", entry=104, stop=100, target=108),
    ]

    outcomes = evaluate_trade_outcomes(bars, signals)
    summary = summarize_trade_outcomes(outcomes)

    assert summary["total_trades"] == 2
    assert summary["wins"] == 1
    assert summary["losses"] == 0
    assert summary["other_exits"] == 1
    assert summary["net_usd"] == 43.0
    assert summary["average_net_usd"] == 21.5


def test_summarizes_trade_outcomes_by_day_with_drawdown() -> None:
    outcomes = [
        {
            "entry_time": "2026-06-19 10:00:00",
            "direction": "long",
            "exit_reason": "target_hit",
            "gross_usd": "200",
            "net_usd": "171.5",
            "holding_bars": "1",
        },
        {
            "entry_time": "2026-06-19 10:05:00",
            "direction": "short",
            "exit_reason": "stop_hit",
            "gross_usd": "-100",
            "net_usd": "-128.5",
            "holding_bars": "2",
        },
        {
            "entry_time": "2026-06-20 10:00:00",
            "direction": "short",
            "exit_reason": "end_of_session",
            "gross_usd": "-50",
            "net_usd": "-78.5",
            "holding_bars": "3",
        },
    ]

    daily_rows = summarize_trade_outcomes_by_day(outcomes)

    assert list(daily_rows[0].keys()) == TRADE_OUTCOME_DAILY_CSV_HEADER
    assert daily_rows[0]["trade_date"] == "2026-06-19"
    assert daily_rows[0]["trades"] == 2
    assert daily_rows[0]["target_hits"] == 1
    assert daily_rows[0]["losses"] == 1
    assert daily_rows[0]["other_exits"] == 0
    assert daily_rows[0]["net_usd"] == "43"
    assert daily_rows[0]["average_holding_bars"] == "1.5"
    assert daily_rows[0]["cumulative_net_usd"] == "43"
    assert daily_rows[0]["drawdown_usd"] == "0"
    assert daily_rows[1]["trade_date"] == "2026-06-20"
    assert daily_rows[1]["net_usd"] == "-78.5"
    assert daily_rows[1]["cumulative_net_usd"] == "-35.5"
    assert daily_rows[1]["drawdown_usd"] == "-78.5"


def test_rejects_negative_slippage_override() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=102, low=100, close=101),
        _bar(1, timestamp="2026-06-19 10:01:00", high=105, low=101, close=104),
    ]
    signals = [_signal(0, direction="long", entry=101, stop=99, target=105)]

    with pytest.raises(TradeOutcomeError, match="nonnegative"):
        evaluate_trade_outcomes(
            bars,
            signals,
            instrument_root="es",
            slippage_ticks_per_side=-1,
        )
