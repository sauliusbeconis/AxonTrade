from __future__ import annotations

import pytest

from axontrade.config import (
    ConfigError,
    load_yaml,
    require_fields,
    validate_firm_config,
    validate_instrument_config,
    validate_risk_config,
)


def test_loads_lucidflex_profile() -> None:
    config = load_yaml("config/firms/lucidflex_25k_evaluation.yaml")

    validate_firm_config(config)

    assert config["firm_name"] == "Lucid Trading"
    assert config["account_type"] == "LucidFlex"
    assert config["simulation_only"] is True
    assert config["live_automated_entries_enabled"] is False
    assert config["source_status"] == "official_sources_reviewed_recheck_before_live"
    assert config["source_reviewed_on"] == "2026-06-29"
    source_names = {source["name"] for source in config["sources"]}
    assert "Prohibited High Frequency Trading" in source_names
    assert "Prohibited Microscalping" in source_names


def test_loads_tradeify_50k_select_profile() -> None:
    config = load_yaml("config/firms/tradeify_50k_select.yaml")

    validate_firm_config(config)

    assert config["firm_name"] == "Tradeify"
    assert config["account_type"] == "Select"
    assert config["profit_target_usd"] == 3000
    assert config["max_loss_limit_usd"] == 2000
    assert config["consistency_max_percentage"] == 40
    assert config["minimum_trading_days"] == 3
    assert config["simulation_only"] is True
    assert config["live_automated_entries_enabled"] is False
    assert config["source_reviewed_on"] == "2026-08-05"


def test_loads_tradeify_mgc_select_strategy_snapshot() -> None:
    config = load_yaml("config/research/tradeify_mgc_select_v1.yaml")

    assert config["strategy_id"] == "tradeify_mgc_select_v1"
    assert config["status"] == "provisional_gates_pass_requires_independent_replay"
    assert config["implementation_present"] is False
    assert config["live_routing_approved"] is False
    assert config["quality_model"]["threshold"] == 0.70
    assert len(config["quality_model"]["features"]) == 14
    assert config["management"]["target_points"] == 8
    assert config["management"]["initial_stop_points"] == 15
    assert config["account_sizing"]["maximum_quantity"] == 3
    assert config["account_sizing"]["funded_post_drawdown_lock_quantity"] == 1


def test_loads_instrument_profiles() -> None:
    for symbol in ("ES", "MES", "NQ", "MNQ", "MGC"):
        config = load_yaml(f"config/instruments/{symbol}.yaml")
        validate_instrument_config(config)
        assert config["symbol"] == symbol
        assert config["tick_size"] > 0
        assert config["default_commission_per_side_usd"] >= 0


def test_loads_development_risk_profile() -> None:
    config = load_yaml("config/risk/development_safe.yaml")

    validate_risk_config(config)

    assert config["maximum_open_positions"] == 1
    assert config["averaging_down_allowed"] is False


def test_missing_required_field_raises_clear_error() -> None:
    with pytest.raises(ConfigError, match="Missing required fields"):
        require_fields({"profile_id": "incomplete"}, ["profile_id", "firm_name"])
