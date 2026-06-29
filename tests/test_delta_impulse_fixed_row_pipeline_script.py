from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / (
        "run_delta_impulse_fixed_row_pipeline.py"
    )
    spec = importlib.util.spec_from_file_location("run_delta_impulse_fixed_row_pipeline", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runs_delta_impulse_fixed_row_pipeline(tmp_path, monkeypatch, capsys) -> None:
    module = _load_module()
    export_path = tmp_path / "bars.csv"
    signal_path = tmp_path / "signals.csv"
    holiday_path = tmp_path / "holidays.csv"
    outcomes_path = tmp_path / "outcomes.csv"
    sweep_path = tmp_path / "sweep.csv"
    signal_report_path = tmp_path / "signal.md"
    robustness_path = tmp_path / "robustness.md"
    acceptance_path = tmp_path / "acceptance.md"
    export_path.write_text(
        "\n".join(
            [
                "Date Time,Open,High,Low,Last",
                "2026-06-18 10:00:00,100,100,99.75,100",
                "2026-06-18 10:03:00,100,105.25,100.5,105",
                "2026-06-18 10:06:00,105,108.25,104,108",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    _write_signal_log(signal_path)
    holiday_path.write_text(
        "date,label,source_url,retrieved_date\n"
        "2026-06-19,Juneteenth,https://example.com/hours,2026-06-29\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_delta_impulse_fixed_row_pipeline.py",
            str(export_path),
            str(signal_path),
            "--symbol",
            "ESU26-CME",
            "--chart-number",
            "2",
            "--holiday-calendar",
            str(holiday_path),
            "--outcomes-output",
            str(outcomes_path),
            "--sweep-output",
            str(sweep_path),
            "--signal-report",
            str(signal_report_path),
            "--robustness-report",
            str(robustness_path),
            "--acceptance-report",
            str(acceptance_path),
            "--first-target-points",
            "5",
            "--stop-points",
            "10",
            "--runner-target-points",
            "8",
            "--sweep-first-target-points",
            "4,5",
            "--sweep-stop-points",
            "8,10",
            "--sweep-runner-target-points",
            "8,10",
            "--sweep-runner-stop-modes",
            "initial",
            "--sweep-direction-filters",
            "all",
        ],
    )

    assert module.main() == 0

    outcome_rows = list(csv.DictReader(outcomes_path.open(newline="", encoding="utf-8")))
    sweep_rows = list(csv.DictReader(sweep_path.open(newline="", encoding="utf-8")))
    assert outcome_rows[0]["exit_reason"] == "runner_target_hit"
    assert len(sweep_rows) == 8
    assert "| Overall status | FAIL |" in acceptance_path.read_text(encoding="utf-8")
    assert "Fixed Row Result" in robustness_path.read_text(encoding="utf-8")
    assert "Candidate signals" in signal_report_path.read_text(encoding="utf-8")
    assert "acceptance=FAIL" in capsys.readouterr().out


def _write_signal_log(path: Path) -> None:
    header = [
        "schema_version",
        "event_key",
        "event_type",
        "generated_at",
        "symbol",
        "chart_number",
        "bar_index",
        "bar_start_time",
        "trade_mode",
        "strategy_id",
        "signal_id",
        "direction",
        "action",
        "signal_price",
        "stop_price",
        "target_price",
        "invalidation_price",
        "rejection_reason",
        "confidence",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerow(
            {
                "schema_version": 1,
                "event_key": "ESU26-CME:2:0:test:candidate_signal:long",
                "event_type": "candidate_signal",
                "generated_at": "2026-06-18 10:00:00",
                "symbol": "ESU26-CME",
                "chart_number": 2,
                "bar_index": 0,
                "bar_start_time": "2026-06-18 10:00:00",
                "trade_mode": "replay",
                "strategy_id": "delta_impulse_continue_10bar_2.5pt_50d",
                "signal_id": "delta_impulse_continue_10bar_2.5pt_50d_ESU26-CME_0",
                "direction": "long",
                "action": "candidate",
                "signal_price": 100,
                "stop_price": 90,
                "target_price": 108,
                "invalidation_price": 90,
                "rejection_reason": "not_applicable",
                "confidence": 0.5,
                "notes": (
                    "long delta impulse continuation; first_target_points=5; "
                    "runner_target_points=8; runner_stop_mode=initial"
                ),
            },
        )
