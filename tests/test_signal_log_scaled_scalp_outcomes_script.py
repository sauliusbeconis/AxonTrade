from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / (
        "run_signal_log_scaled_scalp_outcomes.py"
    )
    spec = importlib.util.spec_from_file_location("run_signal_log_scaled_scalp_outcomes", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runs_logged_scaled_scalp_outcomes(tmp_path, monkeypatch, capsys) -> None:
    module = _load_module()
    export_path = tmp_path / "bars.csv"
    signal_path = tmp_path / "signals.csv"
    output_path = tmp_path / "outcomes.csv"
    export_path.write_text(
        "\n".join(
            [
                "Date Time,Open,High,Low,Last",
                "2026-06-19 10:00:00,100,100,99.75,100",
                "2026-06-19 10:03:00,100,105.25,100.5,105",
                "2026-06-19 10:06:00,105,115.25,104,115",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    _write_signal_log(signal_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_signal_log_scaled_scalp_outcomes.py",
            str(export_path),
            str(signal_path),
            str(output_path),
            "--symbol",
            "ESU26-CME",
            "--chart-number",
            "2",
            "--first-target-points",
            "5",
            "--stop-points",
            "5",
            "--runner-target-points",
            "15",
            "--runner-stop-mode",
            "breakeven",
        ],
    )

    assert module.main() == 0

    rows = list(csv.DictReader(output_path.open(newline="", encoding="utf-8")))
    assert rows[0]["exit_reason"] == "runner_target_hit"
    assert rows[0]["first_target_hit"] == "true"
    assert rows[0]["gross_points"] == "20"
    assert "runner_targets=1" in capsys.readouterr().out


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
                "generated_at": "2026-06-19 10:00:00",
                "symbol": "ESU26-CME",
                "chart_number": 2,
                "bar_index": 0,
                "bar_start_time": "2026-06-19 10:00:00",
                "trade_mode": "replay",
                "strategy_id": "test",
                "signal_id": "test_ESU26-CME_0",
                "direction": "long",
                "action": "candidate",
                "signal_price": 100,
                "stop_price": 95,
                "target_price": 115,
                "invalidation_price": 95,
                "rejection_reason": "not_applicable",
                "confidence": 0.5,
                "notes": "test",
            },
        )
