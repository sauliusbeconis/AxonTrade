from __future__ import annotations

from axontrade.research.delta_impulse_overlay_validation import (
    DeltaImpulseRuleConfig,
    compare_delta_impulse_overlay_log,
    generate_delta_impulse_overlay_candidates,
    render_delta_impulse_overlay_validation_report,
)


def _bar(
    index: int,
    *,
    close: float,
    delta: float,
    timestamp: str | None = None,
) -> dict[str, object]:
    timestamp_value = timestamp or f"2026-06-19 10:{index:02d}:00"
    ask_volume = 100 + max(delta, 0)
    bid_volume = 100 + max(-delta, 0)
    return {
        "timestamp": timestamp_value,
        "symbol": "ESU26-CME",
        "chart_number": 2,
        "bar_index": index,
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "bid_volume": bid_volume,
        "ask_volume": ask_volume,
        "session_phase": "rth",
    }


def test_generates_delta_impulse_candidate_from_current_plus_prior_lookback() -> None:
    bars = [_bar(index, close=100 + index * 0.25, delta=10) for index in range(12)]

    rows = generate_delta_impulse_overlay_candidates(
        bars,
        config=DeltaImpulseRuleConfig(minimum_spacing_seconds=0, max_signals_per_day=0),
    )

    assert len(rows) == 2
    assert rows[0]["event_key"] == (
        "ESU26-CME:2:10:delta_impulse_continue_10bar_2.5pt_50d:"
        "candidate_signal:long"
    )
    assert rows[0]["signal_price"] == "102.5"
    assert rows[0]["stop_price"] == "92.5"
    assert rows[0]["target_price"] == "110.5"
    assert "price_reference_bar_index=0" in rows[0]["notes"]
    assert "delta_sum=100" in rows[0]["notes"]


def test_applies_spacing_and_daily_cap_after_candidate_evaluation() -> None:
    bars = [_bar(index, close=100 + index * 0.25, delta=10) for index in range(30)]

    rows = generate_delta_impulse_overlay_candidates(
        bars,
        config=DeltaImpulseRuleConfig(minimum_spacing_seconds=900, max_signals_per_day=1),
    )

    assert [row["bar_index"] for row in rows] == [10]


def test_compares_matching_sierra_log_rows() -> None:
    bars = [_bar(index, close=100 + index * 0.25, delta=10) for index in range(12)]
    expected = generate_delta_impulse_overlay_candidates(
        bars,
        config=DeltaImpulseRuleConfig(minimum_spacing_seconds=0, max_signals_per_day=0),
    )
    actual = [{key: str(value) for key, value in row.items()} for row in expected]

    comparison = compare_delta_impulse_overlay_log(
        bars,
        actual,
        config=DeltaImpulseRuleConfig(minimum_spacing_seconds=0, max_signals_per_day=0),
    )

    assert comparison.passed is True
    assert len(comparison.matched_rows) == 2
    assert not comparison.missing_rows
    assert not comparison.unexpected_rows
    assert not comparison.mismatched_rows


def test_compares_missing_unexpected_and_mismatched_rows() -> None:
    bars = [_bar(index, close=100 + index * 0.25, delta=10) for index in range(12)]
    expected = generate_delta_impulse_overlay_candidates(
        bars,
        config=DeltaImpulseRuleConfig(minimum_spacing_seconds=0, max_signals_per_day=0),
    )
    actual = [{key: str(value) for key, value in expected[0].items()}]
    actual[0]["target_price"] = "999"
    actual.append({key: str(value) for key, value in expected[1].items()})
    actual[1]["bar_index"] = "99"
    actual[1]["event_key"] = actual[1]["event_key"].replace(":11:", ":99:")
    actual[1]["signal_id"] = actual[1]["signal_id"].replace("_11", "_99")

    comparison = compare_delta_impulse_overlay_log(
        bars,
        actual,
        config=DeltaImpulseRuleConfig(minimum_spacing_seconds=0, max_signals_per_day=0),
    )

    assert comparison.passed is False
    assert len(comparison.missing_rows) == 1
    assert len(comparison.unexpected_rows) == 1
    assert len(comparison.mismatched_rows) == 1
    assert "target_price" in comparison.mismatched_rows[0]["mismatches"]


def test_renders_validation_report() -> None:
    bars = [_bar(index, close=100 + index * 0.25, delta=10) for index in range(12)]
    expected = generate_delta_impulse_overlay_candidates(
        bars,
        config=DeltaImpulseRuleConfig(minimum_spacing_seconds=0, max_signals_per_day=0),
    )
    comparison = compare_delta_impulse_overlay_log(
        bars,
        expected,
        config=DeltaImpulseRuleConfig(minimum_spacing_seconds=0, max_signals_per_day=0),
    )

    report = render_delta_impulse_overlay_validation_report(
        comparison,
        bars_source="bars.txt",
        signal_log_source="signals.csv",
    )

    assert "Status: **PASS**" in report
    assert "expected candidates from bars: `2`" in report
    assert "Sierra candidate log rows: `2`" in report
