from __future__ import annotations

import pytest

from axontrade.research import (
    ABSORPTION_REWARD_RISK_SWEEP_HEADER,
    AbsorptionExperimentError,
    run_absorption_reward_risk_sweep,
    run_absorption_reward_risk_train_holdout_sweep,
)


def _outcome(
    index: int,
    *,
    trade_date: str,
    direction: str,
    entry: float,
    stop: float,
    target: float,
    exit_reason: str,
    net_usd: float,
) -> dict[str, object]:
    return {
        "entry_time": f"{trade_date} 10:{index:02d}:00",
        "direction": direction,
        "entry_price": entry,
        "stop_price": stop,
        "target_price": target,
        "exit_reason": exit_reason,
        "gross_usd": net_usd,
        "net_usd": net_usd,
    }


def test_runs_absorption_reward_risk_sweep() -> None:
    rows = [
        _outcome(0, trade_date="2026-06-10", direction="long", entry=100, stop=99, target=101, exit_reason="target_hit", net_usd=50),
        _outcome(1, trade_date="2026-06-10", direction="short", entry=100, stop=102, target=99, exit_reason="stop_hit", net_usd=-100),
    ]

    experiment_rows = run_absorption_reward_risk_sweep(
        rows,
        minimum_reward_risks=[0, 1],
        direction_filters=["all", "long"],
    )

    assert list(experiment_rows[0].keys()) == ABSORPTION_REWARD_RISK_SWEEP_HEADER
    assert len(experiment_rows) == 4
    by_experiment = {row["experiment_id"]: row for row in experiment_rows}
    assert by_experiment[
        "liquidity_sweep_absorption_reward_risk:direction=all:min_reward_risk=1"
    ]["evaluated_trades"] == 1
    assert by_experiment[
        "liquidity_sweep_absorption_reward_risk:direction=long:min_reward_risk=0"
    ]["net_usd"] == "50"


def test_runs_absorption_reward_risk_train_holdout_sweep() -> None:
    rows = [
        _outcome(0, trade_date="2026-06-10", direction="long", entry=100, stop=99, target=102, exit_reason="target_hit", net_usd=100),
        _outcome(1, trade_date="2026-06-11", direction="long", entry=100, stop=99, target=100.5, exit_reason="stop_hit", net_usd=-50),
        _outcome(2, trade_date="2026-06-12", direction="long", entry=100, stop=99, target=102, exit_reason="target_hit", net_usd=100),
    ]

    split_rows = run_absorption_reward_risk_train_holdout_sweep(
        rows,
        train_date_count=2,
        minimum_reward_risks=[0, 1],
        direction_filters=["all"],
    )

    assert len(split_rows) == 4
    assert {row["sample"] for row in split_rows} == {"train", "holdout"}
    selected_train = next(
        row for row in split_rows if row["sample"] == "train" and row["selected_on_train"] == "true"
    )
    selected_holdout = next(
        row for row in split_rows if row["sample"] == "holdout" and row["selected_on_train"] == "true"
    )
    assert selected_train["minimum_reward_risk"] == "1"
    assert selected_holdout["evaluated_trades"] == 1
    assert selected_holdout["net_usd"] == "100"


def test_rejects_invalid_absorption_reward_risk_sweep() -> None:
    with pytest.raises(AbsorptionExperimentError, match="nonnegative"):
        run_absorption_reward_risk_sweep(
            [],
            minimum_reward_risks=[-1],
        )
