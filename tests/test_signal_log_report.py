from __future__ import annotations

from axontrade.reports import render_signal_log_report, write_signal_log_report


def test_renders_signal_log_report() -> None:
    report = render_signal_log_report(
        [_candidate_row(), _rejected_row()],
        source="signals.csv",
    )

    assert "# Sierra Signal Log Report" in report
    assert "| Total rows | 2 |" in report
    assert "| Candidate signals | 1 |" in report
    assert "| Rejected signals | 1 |" in report
    assert "| Earliest bar time | 2026-06-17 10:42:28 |" in report
    assert "| 2026-06-17 | 2 |" in report
    assert "| long | 1 |" in report
    assert "long absorption reversal" in report


def test_writes_signal_log_report(tmp_path) -> None:
    report_path = tmp_path / "signal-report.md"

    report = write_signal_log_report(
        report_path,
        [_candidate_row()],
        source="signals.csv",
    )

    assert report_path.read_text(encoding="utf-8") == report
    assert "| Candidate signals | 1 |" in report


def _candidate_row() -> dict[str, object]:
    return {
        "schema_version": 1,
        "event_key": "ESU26-CME:2:2026-06-17:long:strategy:candidate_signal:100",
        "event_type": "candidate_signal",
        "generated_at": "2026-06-17 10:42:28",
        "symbol": "ESU26-CME",
        "chart_number": 2,
        "bar_index": 100,
        "bar_start_time": "2026-06-17 10:42:28",
        "trade_mode": "replay",
        "strategy_id": "liquidity_sweep_absorption_reversal",
        "signal_id": "liquidity_sweep_absorption_reversal_ESU26-CME_100",
        "direction": "long",
        "action": "candidate",
        "signal_price": "7581.25",
        "stop_price": "7579.25",
        "target_price": "7590.5",
        "invalidation_price": "7579.25",
        "rejection_reason": "not_applicable",
        "confidence": "0.55",
        "notes": "long absorption reversal",
    }


def _rejected_row() -> dict[str, object]:
    row = _candidate_row()
    row.update(
        {
            "event_key": "ESU26-CME:2:101:strategy:rejected_signal:none",
            "event_type": "rejected_signal",
            "bar_index": 101,
            "signal_id": "liquidity_sweep_absorption_reversal_ESU26-CME_101",
            "direction": "none",
            "action": "reject",
            "stop_price": "",
            "target_price": "",
            "invalidation_price": "",
            "rejection_reason": "no_setup",
            "notes": "no liquidity sweep reversal setup",
        },
    )
    return row
