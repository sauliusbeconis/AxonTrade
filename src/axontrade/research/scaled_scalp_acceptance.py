"""Acceptance gates for fixed scaled-scalp research rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from axontrade.config import ConfigError, load_yaml, require_fields


DEFAULT_SCALED_SCALP_ACCEPTANCE_CONFIG_PATH = (
    "config/research/scaled_scalp_fixed_row_acceptance_gates.yaml"
)
_REQUIRED_CONFIG_FIELDS = [
    "schema_version",
    "profile_id",
    "gates.minimum_outcome_trades",
    "gates.minimum_trade_dates",
    "gates.require_positive_holiday_adjusted_net",
    "gates.require_positive_holiday_adjusted_fixed_rolling_holdout_net",
    "gates.maximum_drawdown_to_net_ratio",
    "gates.last_n_dates",
    "gates.maximum_last_n_positive_day_net_share",
    "gates.minimum_positive_nearby_parameter_rows",
    "gates.require_nonnegative_holiday_adjusted_short_net",
    "gates.maximum_nonholiday_terminal_exits",
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_TERMINAL_EXIT_REASONS = {"end_of_session", "no_following_bar"}


class ScaledScalpAcceptanceError(ValueError):
    """Raised when fixed scaled-scalp acceptance inputs are invalid."""


@dataclass(frozen=True)
class ScaledScalpAcceptanceFinding:
    """One fixed scaled-scalp acceptance-gate evaluation result."""

    gate_id: str
    passed: bool
    observed: str
    threshold: str
    notes: str


@dataclass(frozen=True)
class ScaledScalpAcceptanceSummary:
    """Sample coverage metrics for a fixed scaled-scalp row."""

    outcome_trades: int
    trade_dates: int
    holiday_dates: int
    holiday_adjusted_trades: int
    holiday_adjusted_net_usd: float
    holiday_adjusted_short_net_usd: float
    holiday_adjusted_fixed_rolling_holdout_net_usd: float
    maximum_drawdown_usd: float
    drawdown_to_net_ratio: float
    last_n_dates: int
    last_n_positive_day_net_share: float
    positive_nearby_parameter_rows: int
    nonholiday_terminal_exits: int
    additional_trades_required: int
    additional_trade_dates_required: int


def load_scaled_scalp_acceptance_config(
    path: str | Path = DEFAULT_SCALED_SCALP_ACCEPTANCE_CONFIG_PATH,
) -> dict[str, Any]:
    """Load and validate the fixed scaled-scalp acceptance config."""

    config = load_yaml(path)
    validate_scaled_scalp_acceptance_config(config)
    return config


def validate_scaled_scalp_acceptance_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate a fixed scaled-scalp acceptance config mapping."""

    require_fields(config, _REQUIRED_CONFIG_FIELDS, context="scaled-scalp acceptance config")
    if _config_int(config["schema_version"], "schema_version") != 1:
        raise ConfigError("scaled-scalp acceptance config schema_version must be 1")

    gates = config["gates"]
    _require_positive_int(gates, "minimum_outcome_trades")
    _require_positive_int(gates, "minimum_trade_dates")
    _require_positive_int(gates, "last_n_dates")
    _require_nonnegative_int(gates, "minimum_positive_nearby_parameter_rows")
    _require_nonnegative_int(gates, "maximum_nonholiday_terminal_exits")
    for key in (
        "require_positive_holiday_adjusted_net",
        "require_positive_holiday_adjusted_fixed_rolling_holdout_net",
        "require_nonnegative_holiday_adjusted_short_net",
    ):
        if not isinstance(gates[key], bool):
            raise ConfigError(f"{key} must be a boolean")
    _require_ratio(gates, "maximum_drawdown_to_net_ratio")
    _require_ratio(gates, "maximum_last_n_positive_day_net_share")
    return config


def evaluate_scaled_scalp_acceptance(
    outcome_rows: Iterable[dict[str, Any]],
    sweep_rows: Iterable[dict[str, Any]],
    *,
    holiday_dates: Iterable[str] = (),
    config: dict[str, Any] | None = None,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
) -> list[ScaledScalpAcceptanceFinding]:
    """Evaluate a fixed scaled-scalp row against configured evidence gates."""

    acceptance_config = (
        load_scaled_scalp_acceptance_config() if config is None else config
    )
    validate_scaled_scalp_acceptance_config(acceptance_config)
    gates = acceptance_config["gates"]
    summary = summarize_scaled_scalp_acceptance_sample(
        outcome_rows,
        sweep_rows,
        holiday_dates=holiday_dates,
        config=acceptance_config,
        first_target_points=first_target_points,
        stop_points=stop_points,
        runner_target_points=runner_target_points,
    )
    findings = [
        _minimum_outcome_trades(summary, int(gates["minimum_outcome_trades"])),
        _minimum_trade_dates(summary, int(gates["minimum_trade_dates"])),
    ]
    if gates["require_positive_holiday_adjusted_net"]:
        findings.append(_positive_holiday_adjusted_net(summary))
    if gates["require_positive_holiday_adjusted_fixed_rolling_holdout_net"]:
        findings.append(_positive_fixed_rolling_holdout_net(summary))
    findings.extend(
        [
            _maximum_drawdown_to_net_ratio(
                summary,
                float(gates["maximum_drawdown_to_net_ratio"]),
            ),
            _maximum_last_n_positive_day_net_share(
                summary,
                float(gates["maximum_last_n_positive_day_net_share"]),
            ),
            _minimum_positive_nearby_parameter_rows(
                summary,
                int(gates["minimum_positive_nearby_parameter_rows"]),
            ),
        ],
    )
    if gates["require_nonnegative_holiday_adjusted_short_net"]:
        findings.append(_nonnegative_holiday_adjusted_short_net(summary))
    findings.append(
        _maximum_nonholiday_terminal_exits(
            summary,
            int(gates["maximum_nonholiday_terminal_exits"]),
        ),
    )
    return findings


def summarize_scaled_scalp_acceptance_sample(
    outcome_rows: Iterable[dict[str, Any]],
    sweep_rows: Iterable[dict[str, Any]],
    *,
    holiday_dates: Iterable[str] = (),
    config: dict[str, Any] | None = None,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
) -> ScaledScalpAcceptanceSummary:
    """Summarize fixed scaled-scalp acceptance metrics and evidence gaps."""

    acceptance_config = (
        load_scaled_scalp_acceptance_config() if config is None else config
    )
    validate_scaled_scalp_acceptance_config(acceptance_config)
    gates = acceptance_config["gates"]
    holidays = set(holiday_dates)
    outcomes = _prepare_outcomes(outcome_rows)
    holiday_adjusted = [
        outcome for outcome in outcomes if outcome["trade_date"] not in holidays
    ]
    daily_rows = _daily_rows(outcomes)
    fixed_windows = _fixed_window_rows(holiday_adjusted)
    drawdown = _maximum_drawdown(daily_rows)
    net = sum(float(outcome["net_usd"]) for outcome in outcomes)
    drawdown_to_net = abs(drawdown) / net if net > 0 else 1.0
    last_n_dates = int(gates["last_n_dates"])
    positive_day_net = sum(max(0.0, float(row["net_usd"])) for row in daily_rows)
    last_n_net = sum(
        max(0.0, float(row["net_usd"]))
        for row in daily_rows[-last_n_dates:]
    )
    last_n_share = last_n_net / positive_day_net if positive_day_net > 0 else 1.0
    positive_nearby = _positive_nearby_parameter_rows(
        sweep_rows,
        first_target_points=first_target_points,
        stop_points=stop_points,
        runner_target_points=runner_target_points,
    )
    trade_dates = {str(outcome["trade_date"]) for outcome in outcomes}
    nonholiday_terminal_exits = sum(
        1
        for outcome in outcomes
        if outcome["trade_date"] not in holidays
        and outcome["exit_reason"] in _TERMINAL_EXIT_REASONS
    )
    return ScaledScalpAcceptanceSummary(
        outcome_trades=len(outcomes),
        trade_dates=len(trade_dates),
        holiday_dates=len(holidays),
        holiday_adjusted_trades=len(holiday_adjusted),
        holiday_adjusted_net_usd=sum(float(outcome["net_usd"]) for outcome in holiday_adjusted),
        holiday_adjusted_short_net_usd=sum(
            float(outcome["net_usd"])
            for outcome in holiday_adjusted
            if outcome["direction"] == "short"
        ),
        holiday_adjusted_fixed_rolling_holdout_net_usd=sum(
            float(row["holdout_net_usd"]) for row in fixed_windows
        ),
        maximum_drawdown_usd=drawdown,
        drawdown_to_net_ratio=drawdown_to_net,
        last_n_dates=last_n_dates,
        last_n_positive_day_net_share=last_n_share,
        positive_nearby_parameter_rows=positive_nearby,
        nonholiday_terminal_exits=nonholiday_terminal_exits,
        additional_trades_required=max(
            0,
            int(gates["minimum_outcome_trades"]) - len(outcomes),
        ),
        additional_trade_dates_required=max(
            0,
            int(gates["minimum_trade_dates"]) - len(trade_dates),
        ),
    )


def scaled_scalp_acceptance_passed(
    findings: Iterable[ScaledScalpAcceptanceFinding],
) -> bool:
    """Return true only when every fixed scaled-scalp acceptance gate passed."""

    return all(finding.passed for finding in findings)


def render_scaled_scalp_acceptance_report(
    findings: Iterable[ScaledScalpAcceptanceFinding],
    *,
    config: dict[str, Any],
    sources: dict[str, str],
    sample_summary: ScaledScalpAcceptanceSummary | None = None,
) -> str:
    """Render a deterministic fixed scaled-scalp acceptance report."""

    finding_rows = list(findings)
    status = "PASS" if scaled_scalp_acceptance_passed(finding_rows) else "FAIL"
    lines = [
        "# Fixed Scaled-Scalp Acceptance Report",
        "",
        "This report checks whether a fixed two-contract scaled-scalp row passes",
        "minimum evidence gates. It is research-only and does not place, modify,",
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

    if sample_summary is not None:
        lines.extend(
            [
                "",
                "## Sample Coverage",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Outcome trades | {sample_summary.outcome_trades} |",
                f"| Trade dates | {sample_summary.trade_dates} |",
                f"| Holiday dates | {sample_summary.holiday_dates} |",
                f"| Holiday-adjusted trades | {sample_summary.holiday_adjusted_trades} |",
                (
                    "| Holiday-adjusted net USD | "
                    f"{_format_usd(sample_summary.holiday_adjusted_net_usd)} |"
                ),
                (
                    "| Holiday-adjusted short net USD | "
                    f"{_format_usd(sample_summary.holiday_adjusted_short_net_usd)} |"
                ),
                (
                    "| Holiday-adjusted fixed rolling holdout net USD | "
                    f"{_format_usd(sample_summary.holiday_adjusted_fixed_rolling_holdout_net_usd)} |"
                ),
                f"| Maximum drawdown USD | {_format_usd(sample_summary.maximum_drawdown_usd)} |",
                f"| Drawdown to net ratio | {_format_ratio(sample_summary.drawdown_to_net_ratio)} |",
                (
                    f"| Last {sample_summary.last_n_dates} positive day net share | "
                    f"{_format_ratio(sample_summary.last_n_positive_day_net_share)} |"
                ),
                (
                    "| Positive nearby parameter rows | "
                    f"{sample_summary.positive_nearby_parameter_rows} |"
                ),
                f"| Nonholiday terminal exits | {sample_summary.nonholiday_terminal_exits} |",
                f"| Additional trades required | {sample_summary.additional_trades_required} |",
                (
                    "| Additional trade dates required | "
                    f"{sample_summary.additional_trade_dates_required} |"
                ),
            ],
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


def write_scaled_scalp_acceptance_report(
    path: str | Path,
    findings: Iterable[ScaledScalpAcceptanceFinding],
    *,
    config: dict[str, Any],
    sources: dict[str, str],
    sample_summary: ScaledScalpAcceptanceSummary | None = None,
) -> str:
    """Render and write a fixed scaled-scalp acceptance report."""

    report = render_scaled_scalp_acceptance_report(
        findings,
        config=config,
        sources=sources,
        sample_summary=sample_summary,
    )
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report


def _minimum_outcome_trades(
    summary: ScaledScalpAcceptanceSummary,
    minimum_trades: int,
) -> ScaledScalpAcceptanceFinding:
    return ScaledScalpAcceptanceFinding(
        gate_id="minimum_outcome_trades",
        passed=summary.outcome_trades >= minimum_trades,
        observed=str(summary.outcome_trades),
        threshold=f">= {minimum_trades}",
        notes="Total evaluated fixed-row outcome trades.",
    )


def _minimum_trade_dates(
    summary: ScaledScalpAcceptanceSummary,
    minimum_dates: int,
) -> ScaledScalpAcceptanceFinding:
    return ScaledScalpAcceptanceFinding(
        gate_id="minimum_trade_dates",
        passed=summary.trade_dates >= minimum_dates,
        observed=str(summary.trade_dates),
        threshold=f">= {minimum_dates}",
        notes="Distinct trade dates represented by fixed-row outcomes.",
    )


def _positive_holiday_adjusted_net(
    summary: ScaledScalpAcceptanceSummary,
) -> ScaledScalpAcceptanceFinding:
    return ScaledScalpAcceptanceFinding(
        gate_id="positive_holiday_adjusted_net",
        passed=summary.holiday_adjusted_net_usd > 0,
        observed=_format_usd(summary.holiday_adjusted_net_usd),
        threshold="> 0.00",
        notes="Net USD after excluding supplied holiday/early-close dates.",
    )


def _positive_fixed_rolling_holdout_net(
    summary: ScaledScalpAcceptanceSummary,
) -> ScaledScalpAcceptanceFinding:
    return ScaledScalpAcceptanceFinding(
        gate_id="positive_holiday_adjusted_fixed_rolling_holdout_net",
        passed=summary.holiday_adjusted_fixed_rolling_holdout_net_usd > 0,
        observed=_format_usd(summary.holiday_adjusted_fixed_rolling_holdout_net_usd),
        threshold="> 0.00",
        notes="Fixed-row rolling holdout net after excluding holidays.",
    )


def _maximum_drawdown_to_net_ratio(
    summary: ScaledScalpAcceptanceSummary,
    maximum_ratio: float,
) -> ScaledScalpAcceptanceFinding:
    return ScaledScalpAcceptanceFinding(
        gate_id="maximum_drawdown_to_net_ratio",
        passed=summary.drawdown_to_net_ratio <= maximum_ratio,
        observed=_format_ratio(summary.drawdown_to_net_ratio),
        threshold=f"<= {_format_ratio(maximum_ratio)}",
        notes="Peak-to-trough drawdown relative to final net; high values imply unstable equity.",
    )


def _maximum_last_n_positive_day_net_share(
    summary: ScaledScalpAcceptanceSummary,
    maximum_share: float,
) -> ScaledScalpAcceptanceFinding:
    return ScaledScalpAcceptanceFinding(
        gate_id="maximum_last_n_positive_day_net_share",
        passed=summary.last_n_positive_day_net_share <= maximum_share,
        observed=_format_ratio(summary.last_n_positive_day_net_share),
        threshold=f"<= {_format_ratio(maximum_share)}",
        notes="Share of all positive daily net contributed by the final configured dates.",
    )


def _minimum_positive_nearby_parameter_rows(
    summary: ScaledScalpAcceptanceSummary,
    minimum_rows: int,
) -> ScaledScalpAcceptanceFinding:
    return ScaledScalpAcceptanceFinding(
        gate_id="minimum_positive_nearby_parameter_rows",
        passed=summary.positive_nearby_parameter_rows >= minimum_rows,
        observed=str(summary.positive_nearby_parameter_rows),
        threshold=f">= {minimum_rows}",
        notes="Positive nearby all-direction initial-stop parameter rows around the fixed row.",
    )


def _nonnegative_holiday_adjusted_short_net(
    summary: ScaledScalpAcceptanceSummary,
) -> ScaledScalpAcceptanceFinding:
    return ScaledScalpAcceptanceFinding(
        gate_id="nonnegative_holiday_adjusted_short_net",
        passed=summary.holiday_adjusted_short_net_usd >= 0,
        observed=_format_usd(summary.holiday_adjusted_short_net_usd),
        threshold=">= 0.00",
        notes="Short-side net after excluding supplied holiday/early-close dates.",
    )


def _maximum_nonholiday_terminal_exits(
    summary: ScaledScalpAcceptanceSummary,
    maximum_exits: int,
) -> ScaledScalpAcceptanceFinding:
    return ScaledScalpAcceptanceFinding(
        gate_id="maximum_nonholiday_terminal_exits",
        passed=summary.nonholiday_terminal_exits <= maximum_exits,
        observed=str(summary.nonholiday_terminal_exits),
        threshold=f"<= {maximum_exits}",
        notes="End/no-following exits on nonholiday dates.",
    )


def _prepare_outcomes(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    outcomes = []
    for row in rows:
        entry_timestamp = _parse_timestamp(str(row.get("entry_time", "")))
        outcomes.append(
            {
                "entry_timestamp": entry_timestamp,
                "trade_date": entry_timestamp.date().isoformat(),
                "direction": str(row.get("direction", "")),
                "exit_reason": str(row.get("exit_reason", "")),
                "net_usd": _to_float(row.get("net_usd"), "net_usd"),
            },
        )
    return sorted(outcomes, key=lambda row: row["entry_timestamp"])


def _parse_timestamp(value: str) -> datetime:
    normalized = " ".join(value.split())
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    raise ScaledScalpAcceptanceError(f"Invalid timestamp: {value!r}")


def _daily_rows(outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    cumulative = 0.0
    for trade_date in sorted({str(outcome["trade_date"]) for outcome in outcomes}):
        selected = [outcome for outcome in outcomes if outcome["trade_date"] == trade_date]
        net = sum(float(outcome["net_usd"]) for outcome in selected)
        cumulative += net
        rows.append(
            {
                "trade_date": trade_date,
                "net_usd": net,
                "cumulative_net_usd": cumulative,
            },
        )
    return rows


def _maximum_drawdown(daily_rows: list[dict[str, Any]]) -> float:
    peak = 0.0
    max_drawdown = 0.0
    for row in daily_rows:
        cumulative = float(row["cumulative_net_usd"])
        peak = max(peak, cumulative)
        max_drawdown = min(max_drawdown, cumulative - peak)
    return max_drawdown


def _fixed_window_rows(
    outcomes: list[dict[str, Any]],
    *,
    train_date_count: int = 4,
    holdout_date_count: int = 2,
    step_date_count: int = 2,
) -> list[dict[str, Any]]:
    dates = sorted({str(outcome["trade_date"]) for outcome in outcomes})
    max_start = len(dates) - train_date_count - holdout_date_count + 1
    if max_start <= 0:
        return []
    rows = []
    for start_index in range(0, max_start, step_date_count):
        holdout_dates = dates[
            start_index + train_date_count:
            start_index + train_date_count + holdout_date_count
        ]
        holdout = [outcome for outcome in outcomes if outcome["trade_date"] in set(holdout_dates)]
        rows.append(
            {
                "holdout_trades": len(holdout),
                "holdout_net_usd": sum(float(outcome["net_usd"]) for outcome in holdout),
            },
        )
    return rows


def _positive_nearby_parameter_rows(
    rows: Iterable[dict[str, Any]],
    *,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
) -> int:
    count = 0
    for row in rows:
        if str(row.get("direction_filter")) != "all":
            continue
        if str(row.get("runner_stop_mode")) != "initial":
            continue
        first_target = _to_float(row.get("first_target_points"), "first_target_points")
        stop = _to_float(row.get("stop_points"), "stop_points")
        runner_target = _to_float(row.get("runner_target_points"), "runner_target_points")
        net_usd = _to_float(row.get("net_usd"), "net_usd")
        if (
            abs(first_target - first_target_points) <= 1
            and abs(stop - stop_points) <= 2
            and abs(runner_target - runner_target_points) <= 2
            and net_usd > 0
        ):
            count += 1
    return count


def _interpret_acceptance(findings: list[ScaledScalpAcceptanceFinding]) -> str:
    if scaled_scalp_acceptance_passed(findings):
        return (
            "All configured gates passed. This is still research-only and does "
            "not authorize live routing."
        )
    failed = ", ".join(finding.gate_id for finding in findings if not finding.passed)
    return (
        "At least one configured gate failed. Do not promote this fixed row to "
        f"live routing. Failed gates: {failed}."
    )


def _config_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{field_name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be an integer") from exc


def _config_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ConfigError(f"{field_name} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be a number") from exc


def _require_positive_int(mapping: dict[str, Any], key: str) -> None:
    value = _config_int(mapping.get(key), key)
    if value <= 0:
        raise ConfigError(f"{key} must be positive")


def _require_nonnegative_int(mapping: dict[str, Any], key: str) -> None:
    value = _config_int(mapping.get(key), key)
    if value < 0:
        raise ConfigError(f"{key} must be nonnegative")


def _require_ratio(mapping: dict[str, Any], key: str) -> None:
    value = _config_float(mapping.get(key), key)
    if value <= 0 or value > 1:
        raise ConfigError(f"{key} must be greater than 0 and no more than 1")


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ScaledScalpAcceptanceError(f"Invalid {field_name}: {value!r}") from exc


def _format_usd(value: float) -> str:
    return f"{value:.2f}"


def _format_ratio(value: float) -> str:
    return f"{value:.2%}"
