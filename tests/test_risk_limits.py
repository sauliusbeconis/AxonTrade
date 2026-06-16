from __future__ import annotations

from axontrade.config import load_yaml, validate_risk_config
from axontrade.risk import check_development_risk_limits


def _risk_limits() -> dict:
    config = load_yaml("config/risk/development_safe.yaml")
    return validate_risk_config(config)


def test_allows_session_inside_development_limits() -> None:
    decision = check_development_risk_limits(
        {
            "open_positions": 0,
            "trades_this_session": 0,
            "losing_trades_this_session": 0,
            "daily_pnl_usd": 0,
            "minutes_since_last_loss": 30,
            "is_averaging_down": False,
            "is_major_news_blackout": False,
        },
        _risk_limits(),
    )

    assert decision.allowed is True
    assert decision.reasons == ()


def test_blocks_common_development_limit_violations() -> None:
    decision = check_development_risk_limits(
        {
            "open_positions": 1,
            "trades_this_session": 3,
            "losing_trades_this_session": 2,
            "daily_pnl_usd": -150,
            "minutes_since_last_loss": 5,
            "is_averaging_down": True,
            "is_major_news_blackout": True,
        },
        _risk_limits(),
    )

    assert decision.allowed is False
    assert "maximum open positions reached" in decision.reasons
    assert "maximum trades per session reached" in decision.reasons
    assert "maximum losing trades per session reached" in decision.reasons
    assert "personal daily stop reached" in decision.reasons
    assert "cooldown after loss is active" in decision.reasons
    assert "averaging down is not allowed" in decision.reasons
    assert "major news blackout is active" in decision.reasons
