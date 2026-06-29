from __future__ import annotations

from axontrade.reports import (
    ScaledScalpRobustnessReportError,
    load_holiday_calendar_dates,
    load_holiday_calendar_metadata,
    render_scaled_scalp_robustness_report,
    write_scaled_scalp_robustness_report,
)


def test_renders_scaled_scalp_robustness_report() -> None:
    report = render_scaled_scalp_robustness_report(
        _outcome_rows(),
        _sweep_rows(),
        title="Robustness",
        variant_label="5 / 10 / 8 / initial",
        outcome_source="outcomes.csv",
        sweep_source="sweep.csv",
        main_summary_source="summary.md",
        holiday_calendar_source="holidays.csv",
        holiday_dates=["2026-06-19"],
        holiday_source_url="https://example.com/hours",
        holiday_retrieved_date="2026-06-29",
        first_target_points=5,
        stop_points=10,
        runner_target_points=8,
    )

    assert "# Robustness" in report
    assert "`5 / 10 / 8 / initial`" in report
    assert "- Holiday calendar:\n  `holidays.csv`" in report
    assert "| Trades | 6 |" in report
    assert "| Net USD | 258 |" in report
    assert "| Long | 3 | 279 |" in report
    assert "| Short | 3 | -21 |" in report
    assert "| 2026-06-19 | 3 | -171 | 258 |" in report
    assert "| Exclude holidays | 3 | 429 | -164 | 593 |" in report
    assert "| 5 | 10 | 8 | 258 |" in report
    assert "Fixed-row rolling holdout total: `0` trades, `0` net USD." in report


def test_writes_scaled_scalp_robustness_report(tmp_path) -> None:
    report_path = tmp_path / "robustness.md"

    report = write_scaled_scalp_robustness_report(
        report_path,
        _outcome_rows(),
        _sweep_rows(),
        title="Robustness",
        variant_label="5 / 10 / 8 / initial",
        outcome_source="outcomes.csv",
        sweep_source="sweep.csv",
        holiday_dates=["2026-06-19"],
        first_target_points=5,
        stop_points=10,
        runner_target_points=8,
    )

    assert report_path.read_text(encoding="utf-8") == report


def test_scaled_scalp_robustness_report_rejects_bad_timestamp() -> None:
    rows = _outcome_rows()
    rows[0]["entry_time"] = "None"

    try:
        render_scaled_scalp_robustness_report(
            rows,
            _sweep_rows(),
            title="Robustness",
            variant_label="5 / 10 / 8 / initial",
            outcome_source="outcomes.csv",
            sweep_source="sweep.csv",
            first_target_points=5,
            stop_points=10,
            runner_target_points=8,
        )
    except ScaledScalpRobustnessReportError as exc:
        assert "Invalid timestamp" in str(exc)
    else:
        raise AssertionError("expected ScaledScalpRobustnessReportError")


def test_loads_holiday_calendar_dates_and_metadata(tmp_path) -> None:
    calendar = tmp_path / "holidays.csv"
    calendar.write_text(
        "\n".join(
            [
                "date,label,source_url,retrieved_date",
                "2026-06-19,Juneteenth,https://example.com/hours,2026-06-29",
                "2026-06-19,Duplicate,https://example.com/hours,2026-06-29",
            ],
        ),
        encoding="utf-8",
    )

    assert load_holiday_calendar_dates(calendar) == ["2026-06-19"]
    assert load_holiday_calendar_metadata(calendar) == {
        "source_url": "https://example.com/hours",
        "retrieved_date": "2026-06-29",
    }


def test_holiday_calendar_rejects_invalid_date(tmp_path) -> None:
    calendar = tmp_path / "holidays.csv"
    calendar.write_text("date,label\nNone,Bad\n", encoding="utf-8")

    try:
        load_holiday_calendar_dates(calendar)
    except ScaledScalpRobustnessReportError as exc:
        assert "Invalid holiday calendar date" in str(exc)
    else:
        raise AssertionError("expected ScaledScalpRobustnessReportError")


def _outcome_rows() -> list[dict[str, object]]:
    return [
        _outcome("2026-06-18 10:15:00", "long", "runner_target_hit", 593),
        _outcome("2026-06-18 10:45:00", "short", "runner_target_hit", 593),
        _outcome("2026-06-18 11:15:00", "long", "full_stop_hit", -757),
        _outcome("2026-06-19 10:15:00", "long", "runner_target_hit", 443),
        _outcome("2026-06-19 10:45:00", "short", "full_stop_hit", -757),
        _outcome("2026-06-19 11:15:00", "short", "no_following_bar", 143),
    ]


def _outcome(
    entry_time: str,
    direction: str,
    exit_reason: str,
    net_usd: float,
) -> dict[str, object]:
    return {
        "entry_time": entry_time,
        "direction": direction,
        "exit_reason": exit_reason,
        "net_usd": net_usd,
    }


def _sweep_rows() -> list[dict[str, object]]:
    return [
        _sweep(5, 10, 8, 258),
        _sweep(4, 10, 8, 100),
        _sweep(5, 8, 8, -50),
        _sweep(5, 10, 10, -100),
        _sweep(5, 10, 8, 999, direction_filter="long"),
        _sweep(5, 10, 8, 999, runner_stop_mode="breakeven"),
    ]


def _sweep(
    first_target: float,
    stop: float,
    runner_target: float,
    net_usd: float,
    *,
    direction_filter: str = "all",
    runner_stop_mode: str = "initial",
) -> dict[str, object]:
    return {
        "direction_filter": direction_filter,
        "first_target_points": first_target,
        "stop_points": stop,
        "runner_target_points": runner_target,
        "runner_stop_mode": runner_stop_mode,
        "net_usd": net_usd,
    }
