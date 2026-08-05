from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_research_module() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_tradeify_50k_mgc_strategy_research.py"
    )
    spec = importlib.util.spec_from_file_location("tradeify_mgc_research_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixed_one_policy(module: ModuleType):
    return module.SizingPolicy("fixed_1", 1, 1, -999999.0, -999999.0)


def test_tradeify_attempt_requires_three_trade_days() -> None:
    module = _load_research_module()
    start = date(2030, 1, 1)
    dates = [start + timedelta(days=index) for index in range(3)]
    outcomes = {trade_date: SimpleNamespace(gross_points=4.0) for trade_date in dates}

    result = module._simulate_attempt(
        dates,
        outcomes,
        _fixed_one_policy(module),
        total_slippage_ticks=module.BASE_TOTAL_SLIPPAGE_TICKS,
        profit_target_usd=100.0,
        consistency_fraction=1.0,
    )

    assert result.status == "pass"
    assert result.trade_days == 3


def test_tradeify_attempt_risk_locks_before_stop_no_longer_fits() -> None:
    module = _load_research_module()
    start = date(2030, 1, 1)
    dates = [start, start + timedelta(days=1)]
    outcomes = {
        dates[0]: SimpleNamespace(gross_points=-179.6),
        dates[1]: SimpleNamespace(gross_points=25.0),
    }

    result = module._simulate_attempt(
        dates,
        outcomes,
        _fixed_one_policy(module),
        total_slippage_ticks=module.BASE_TOTAL_SLIPPAGE_TICKS,
    )

    assert result.status == "risk_lock"
    assert result.trade_days == 1
    assert result.end_equity_usd < -1800.0


def test_tradeify_attempt_detects_drawdown_breach() -> None:
    module = _load_research_module()
    trade_date = date(2030, 1, 1)

    result = module._simulate_attempt(
        [trade_date],
        {trade_date: SimpleNamespace(gross_points=-210.0)},
        _fixed_one_policy(module),
        total_slippage_ticks=module.BASE_TOTAL_SLIPPAGE_TICKS,
    )

    assert result.status == "fail"
    assert result.end_equity_usd < -module.MAX_DRAWDOWN_USD
