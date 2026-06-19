"""Acceptance-gate checks for price-only research outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from axontrade.config import ConfigError, load_yaml, require_fields


DEFAULT_PRICE_ONLY_ACCEPTANCE_CONFIG_PATH = "config/research/price_only_acceptance_gates.yaml"

_REQUIRED_CONFIG_FIELDS = [
    "schema_version",
    "profile_id",
    "gates.minimum_total_outcome_trades",
    "gates.minimum_trade_days",
    "gates.minimum_walk_forward_holdout_trades",
    "gates.require_positive_walk_forward_holdout_net",
    "gates.minimum_selected_train_holdout_trades",
    "gates.maximum_worst_day_loss_share",
]


class AcceptanceGateError(ValueError):
    """Raised when acceptance-gate inputs are invalid."""


@dataclass(frozen=True)
class AcceptanceFinding:
    """One acceptance-gate evaluation result."""

    gate_id: str
    passed: bool
    observed: str
    threshold: str
    notes: str


def load_price_only_acceptance_config(
    path: str | Path = DEFAULT_PRICE_ONLY_ACCEPTANCE_CONFIG_PATH,
) -> dict[str, Any]:
    """Load and validate the price-only acceptance-gate config."""

    config = load_yaml(path)
    validate_price_only_acceptance_config(config)
    return config


def validate_price_only_acceptance_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate a price-only acceptance-gate config mapping."""

    require_fields(config, _REQUIRED_CONFIG_FIELDS, context="price-only acceptance config")
    if _config_int(config["schema_version"], "schema_version") != 1:
        raise ConfigError("price-only acceptance config schema_version must be 1")

    gates = config["gates"]
    _require_positive_int(gates, "minimum_total_outcome_trades")
    _require_positive_int(gates, "minimum_trade_days")
    _require_positive_int(gates, "minimum_walk_forward_holdout_trades")
    _require_positive_int(gates, "minimum_selected_train_holdout_trades")
    if not isinstance(gates["require_positive_walk_forward_holdout_net"], bool):
        raise ConfigError("require_positive_walk_forward_holdout_net must be a boolean")
    max_loss_share = _config_float(
        gates["maximum_worst_day_loss_share"],
        "maximum_worst_day_loss_share",
    )
    if max_loss_share <= 0 or max_loss_share > 1:
        raise ConfigError("maximum_worst_day_loss_share must be greater than 0 and no more than 1")
    return config


def evaluate_price_only_acceptance(
    outcome_rows: Iterable[dict[str, Any]],
    daily_rows: Iterable[dict[str, Any]],
    train_holdout_rows: Iterable[dict[str, Any]],
    walk_forward_rows: Iterable[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
) -> list[AcceptanceFinding]:
    """Evaluate price-only research CSV rows against configured gates."""

    acceptance_config = load_price_only_acceptance_config() if config is None else config
    validate_price_only_acceptance_config(acceptance_config)
    gates = acceptance_config["gates"]
    outcomes = list(outcome_rows)
    daily = list(daily_rows)
    train_holdout = list(train_holdout_rows)
    walk_forward = list(walk_forward_rows)

    findings = [
        _minimum_total_outcome_trades(outcomes, int(gates["minimum_total_outcome_trades"])),
        _minimum_trade_days(daily, int(gates["minimum_trade_days"])),
        _minimum_walk_forward_holdout_trades(
            walk_forward,
            int(gates["minimum_walk_forward_holdout_trades"]),
        ),
    ]
    if gates["require_positive_walk_forward_holdout_net"]:
        findings.append(_positive_walk_forward_holdout_net(walk_forward))
    findings.extend(
        [
            _minimum_selected_train_holdout_trades(
                train_holdout,
                int(gates["minimum_selected_train_holdout_trades"]),
            ),
            _maximum_worst_day_loss_share(
                daily,
                float(gates["maximum_worst_day_loss_share"]),
            ),
        ],
    )
    return findings


def price_only_acceptance_passed(findings: Iterable[AcceptanceFinding]) -> bool:
    """Return true only when every acceptance gate passed."""

    return all(finding.passed for finding in findings)


def render_price_only_acceptance_report(
    findings: Iterable[AcceptanceFinding],
    *,
    config: dict[str, Any],
    sources: dict[str, str],
) -> str:
    """Render a deterministic Markdown acceptance report."""

    finding_rows = list(findings)
    status = "PASS" if price_only_acceptance_passed(finding_rows) else "FAIL"
    lines = [
        "# Price-Only Acceptance Report",
        "",
        "This report checks whether the current price-only research outputs pass the",
        "configured evidence gates. It is research-only and does not place, modify,",
        "cancel, or route orders.",
        "",
        "## Decision",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Overall status | {status} |",
        f"| Gate profile | {config['profile_id']} |",
        "",
        "## Sources",
        "",
    ]
    for label, source in sorted(sources.items()):
        lines.append(f"- {label}: `{source}`")

    lines.extend(
        [
            "",
            "## Gates",
            "",
            "| Status | Gate | Observed | Required | Notes |",
            "| --- | --- | ---: | ---: | --- |",
        ],
    )
    for finding in finding_rows:
        gate_status = "PASS" if finding.passed else "FAIL"
        lines.append(
            "| "
            + " | ".join(
                [
                    gate_status,
                    finding.gate_id,
                    finding.observed,
                    finding.threshold,
                    finding.notes,
                ],
            )
            + " |",
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            _interpret_acceptance(finding_rows),
            "",
        ],
    )
    return "\n".join(lines)


def write_price_only_acceptance_report(
    path: str | Path,
    findings: Iterable[AcceptanceFinding],
    *,
    config: dict[str, Any],
    sources: dict[str, str],
) -> str:
    """Render and write a price-only acceptance report."""

    report = render_price_only_acceptance_report(findings, config=config, sources=sources)
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report


def _minimum_total_outcome_trades(
    outcome_rows: list[dict[str, Any]],
    minimum_trades: int,
) -> AcceptanceFinding:
    observed_trades = len(outcome_rows)
    return AcceptanceFinding(
        gate_id="minimum_total_outcome_trades",
        passed=observed_trades >= minimum_trades,
        observed=str(observed_trades),
        threshold=f">= {minimum_trades}",
        notes="Total evaluated outcome trades in the baseline sample.",
    )


def _minimum_trade_days(daily_rows: list[dict[str, Any]], minimum_days: int) -> AcceptanceFinding:
    observed_days = len(
        {str(row.get("trade_date", "")).strip() for row in daily_rows if row.get("trade_date")},
    )
    return AcceptanceFinding(
        gate_id="minimum_trade_days",
        passed=observed_days >= minimum_days,
        observed=str(observed_days),
        threshold=f">= {minimum_days}",
        notes="Distinct trade dates in the daily outcome summary.",
    )


def _minimum_walk_forward_holdout_trades(
    walk_forward_rows: list[dict[str, Any]],
    minimum_trades: int,
) -> AcceptanceFinding:
    holdout_rows = _selected_holdout_rows(walk_forward_rows)
    observed_trades = sum(
        _to_int(row.get("evaluated_trades", 0), "evaluated_trades")
        for row in holdout_rows
    )
    return AcceptanceFinding(
        gate_id="minimum_walk_forward_holdout_trades",
        passed=observed_trades >= minimum_trades,
        observed=str(observed_trades),
        threshold=f">= {minimum_trades}",
        notes="Trades from selected rolling holdout windows only.",
    )


def _positive_walk_forward_holdout_net(
    walk_forward_rows: list[dict[str, Any]],
) -> AcceptanceFinding:
    holdout_rows = _selected_holdout_rows(walk_forward_rows)
    observed_net_usd = sum(_to_float(row.get("net_usd", 0), "net_usd") for row in holdout_rows)
    return AcceptanceFinding(
        gate_id="positive_walk_forward_holdout_net",
        passed=observed_net_usd > 0,
        observed=_format_usd(observed_net_usd),
        threshold="> 0.00",
        notes="Net USD from selected rolling holdout windows after configured costs.",
    )


def _minimum_selected_train_holdout_trades(
    train_holdout_rows: list[dict[str, Any]],
    minimum_trades: int,
) -> AcceptanceFinding:
    holdout_rows = _selected_holdout_rows(train_holdout_rows)
    observed_trades = sum(
        _to_int(row.get("evaluated_trades", 0), "evaluated_trades")
        for row in holdout_rows
    )
    return AcceptanceFinding(
        gate_id="minimum_selected_train_holdout_trades",
        passed=observed_trades >= minimum_trades,
        observed=str(observed_trades),
        threshold=f">= {minimum_trades}",
        notes="Trades for the single train-selected holdout parameter set.",
    )


def _maximum_worst_day_loss_share(
    daily_rows: list[dict[str, Any]],
    maximum_loss_share: float,
) -> AcceptanceFinding:
    loss_days = [
        (str(row.get("trade_date", "")).strip(), _to_float(row.get("net_usd", 0), "net_usd"))
        for row in daily_rows
        if _to_float(row.get("net_usd", 0), "net_usd") < 0
    ]
    if not loss_days:
        return AcceptanceFinding(
            gate_id="maximum_worst_day_loss_share",
            passed=True,
            observed="0.00%",
            threshold=f"<= {_format_percent(maximum_loss_share)}",
            notes="No losing days in the daily outcome summary.",
        )

    total_loss_usd = sum(abs(net_usd) for _, net_usd in loss_days)
    worst_date, worst_net_usd = min(loss_days, key=lambda item: item[1])
    observed_share = abs(worst_net_usd) / total_loss_usd if total_loss_usd else 0.0
    return AcceptanceFinding(
        gate_id="maximum_worst_day_loss_share",
        passed=observed_share <= maximum_loss_share,
        observed=_format_percent(observed_share),
        threshold=f"<= {_format_percent(maximum_loss_share)}",
        notes=f"Worst losing day {worst_date} was {_format_usd(worst_net_usd)}.",
    )


def _selected_holdout_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if str(row.get("sample", "")).strip().lower() == "holdout"
        and str(row.get("selected_on_train", "")).strip().lower() == "true"
    ]


def _interpret_acceptance(findings: list[AcceptanceFinding]) -> str:
    failed = [finding for finding in findings if not finding.passed]
    if not failed:
        return (
            "All configured price-only research gates passed. This allows the "
            "research thread to advance to the next validation phase, not to live routing."
        )
    failed_ids = ", ".join(finding.gate_id for finding in failed)
    return (
        "The current price-only baseline is rejected by the configured research gates. "
        f"Failed gates: {failed_ids}."
    )


def _require_positive_int(data: dict[str, Any], field_name: str) -> None:
    value = _config_int(data[field_name], field_name)
    if value <= 0:
        raise ConfigError(f"{field_name} must be positive")


def _config_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value))
    except ValueError as exc:
        raise ConfigError(f"{field_name} must be an integer: {value!r}") from exc


def _config_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise ConfigError(f"{field_name} must be numeric: {value!r}") from exc


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value))
    except ValueError as exc:
        raise AcceptanceGateError(f"{field_name} must be an integer: {value!r}") from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise AcceptanceGateError(f"{field_name} must be numeric: {value!r}") from exc


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _format_usd(value: float) -> str:
    return f"{value:.2f}"
