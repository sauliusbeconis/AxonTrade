"""Acceptance gates for scaled context guard candidates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from axontrade.config import ConfigError, load_yaml, require_fields


DEFAULT_SCALED_CONTEXT_GUARD_ACCEPTANCE_CONFIG_PATH = (
    "config/research/scaled_context_guard_acceptance_gates.yaml"
)
_REQUIRED_CONFIG_FIELDS = [
    "schema_version",
    "profile_id",
    "candidate.guard_name",
    "candidate.conditions",
    "gates.minimum_fixed_guard_trades",
    "gates.minimum_fixed_guard_net_usd",
    "gates.minimum_fixed_guard_average_net_usd",
    "gates.minimum_fixed_guard_profit_factor",
    "gates.maximum_fixed_guard_drawdown_to_net_ratio",
    "gates.maximum_fixed_guard_worst_day_loss_usd",
    "gates.minimum_robustness_rows",
    "gates.require_all_robustness_guarded_net_positive",
    "gates.require_all_robustness_improved_vs_unguarded",
    "gates.minimum_worst_robustness_guarded_net_usd",
    "gates.minimum_worst_robustness_average_net_usd",
    "gates.maximum_robustness_negative_window_rate",
    "gates.maximum_worst_guarded_window_loss_usd",
]


class ScaledContextGuardAcceptanceError(ValueError):
    """Raised when scaled context guard acceptance inputs are invalid."""


@dataclass(frozen=True)
class ScaledContextGuardAcceptanceFinding:
    """One guard-candidate acceptance result."""

    gate_id: str
    passed: bool
    observed: str
    threshold: str
    notes: str


@dataclass(frozen=True)
class ScaledContextGuardAcceptanceSummary:
    """Coverage and stability metrics for a fixed context guard candidate."""

    guard_name: str
    conditions: str
    fixed_input_trades: int
    fixed_kept_trades: int
    fixed_skipped_trades: int
    fixed_net_usd: float
    fixed_average_net_usd: float
    fixed_profit_factor: float
    fixed_max_drawdown_usd: float
    fixed_drawdown_to_net_ratio: float
    fixed_worst_day: str
    fixed_worst_day_net_usd: float
    robustness_rows: int
    robustness_all_guarded_net_positive: bool
    robustness_all_improved_vs_unguarded: bool
    robustness_worst_guarded_net_usd: float
    robustness_worst_average_net_usd: float
    robustness_max_negative_window_rate: float
    robustness_worst_window_loss_usd: float
    additional_fixed_guard_trades_required: int
    additional_robustness_rows_required: int


def load_scaled_context_guard_acceptance_config(
    path: str | Path = DEFAULT_SCALED_CONTEXT_GUARD_ACCEPTANCE_CONFIG_PATH,
) -> dict[str, Any]:
    """Load and validate the scaled context guard acceptance config."""

    config = load_yaml(path)
    validate_scaled_context_guard_acceptance_config(config)
    return config


def validate_scaled_context_guard_acceptance_config(
    config: dict[str, Any],
) -> dict[str, Any]:
    """Validate a scaled context guard acceptance config mapping."""

    require_fields(
        config,
        _REQUIRED_CONFIG_FIELDS,
        context="scaled context guard acceptance config",
    )
    if _config_int(config["schema_version"], "schema_version") != 1:
        raise ConfigError("scaled context guard acceptance config schema_version must be 1")
    candidate = config["candidate"]
    if not str(candidate["guard_name"]).strip():
        raise ConfigError("candidate.guard_name must not be empty")
    conditions = candidate["conditions"]
    if not isinstance(conditions, list) or not conditions:
        raise ConfigError("candidate.conditions must be a non-empty list")
    gates = config["gates"]
    _require_positive_int(gates, "minimum_fixed_guard_trades")
    _require_positive_float(gates, "minimum_fixed_guard_net_usd")
    _require_positive_float(gates, "minimum_fixed_guard_average_net_usd")
    _require_positive_float(gates, "minimum_fixed_guard_profit_factor")
    _require_ratio(gates, "maximum_fixed_guard_drawdown_to_net_ratio")
    _require_positive_float(gates, "maximum_fixed_guard_worst_day_loss_usd")
    _require_positive_int(gates, "minimum_robustness_rows")
    for key in (
        "require_all_robustness_guarded_net_positive",
        "require_all_robustness_improved_vs_unguarded",
    ):
        if not isinstance(gates[key], bool):
            raise ConfigError(f"{key} must be a boolean")
    _require_positive_float(gates, "minimum_worst_robustness_guarded_net_usd")
    _require_positive_float(gates, "minimum_worst_robustness_average_net_usd")
    _require_ratio(gates, "maximum_robustness_negative_window_rate")
    _require_positive_float(gates, "maximum_worst_guarded_window_loss_usd")
    return config


def evaluate_scaled_context_guard_acceptance(
    fixed_guard_rows: Iterable[dict[str, Any]],
    robustness_rows: Iterable[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
) -> list[ScaledContextGuardAcceptanceFinding]:
    """Evaluate a fixed context guard candidate against configured gates."""

    acceptance_config = (
        load_scaled_context_guard_acceptance_config() if config is None else config
    )
    validate_scaled_context_guard_acceptance_config(acceptance_config)
    gates = acceptance_config["gates"]
    summary = summarize_scaled_context_guard_acceptance_sample(
        fixed_guard_rows,
        robustness_rows,
        config=acceptance_config,
    )
    findings = [
        _minimum_fixed_guard_trades(
            summary,
            int(gates["minimum_fixed_guard_trades"]),
        ),
        _minimum_fixed_guard_net_usd(
            summary,
            float(gates["minimum_fixed_guard_net_usd"]),
        ),
        _minimum_fixed_guard_average_net_usd(
            summary,
            float(gates["minimum_fixed_guard_average_net_usd"]),
        ),
        _minimum_fixed_guard_profit_factor(
            summary,
            float(gates["minimum_fixed_guard_profit_factor"]),
        ),
        _maximum_fixed_guard_drawdown_to_net_ratio(
            summary,
            float(gates["maximum_fixed_guard_drawdown_to_net_ratio"]),
        ),
        _maximum_fixed_guard_worst_day_loss(
            summary,
            float(gates["maximum_fixed_guard_worst_day_loss_usd"]),
        ),
        _minimum_robustness_rows(
            summary,
            int(gates["minimum_robustness_rows"]),
        ),
    ]
    if gates["require_all_robustness_guarded_net_positive"]:
        findings.append(_all_robustness_guarded_net_positive(summary))
    if gates["require_all_robustness_improved_vs_unguarded"]:
        findings.append(_all_robustness_improved_vs_unguarded(summary))
    findings.extend(
        [
            _minimum_worst_robustness_guarded_net(
                summary,
                float(gates["minimum_worst_robustness_guarded_net_usd"]),
            ),
            _minimum_worst_robustness_average_net(
                summary,
                float(gates["minimum_worst_robustness_average_net_usd"]),
            ),
            _maximum_robustness_negative_window_rate(
                summary,
                float(gates["maximum_robustness_negative_window_rate"]),
            ),
            _maximum_worst_guarded_window_loss(
                summary,
                float(gates["maximum_worst_guarded_window_loss_usd"]),
            ),
        ],
    )
    return findings


def summarize_scaled_context_guard_acceptance_sample(
    fixed_guard_rows: Iterable[dict[str, Any]],
    robustness_rows: Iterable[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
) -> ScaledContextGuardAcceptanceSummary:
    """Summarize fixed guard and robustness metrics for acceptance gates."""

    acceptance_config = (
        load_scaled_context_guard_acceptance_config() if config is None else config
    )
    validate_scaled_context_guard_acceptance_config(acceptance_config)
    candidate = acceptance_config["candidate"]
    gates = acceptance_config["gates"]
    fixed_row = _select_guard_row(fixed_guard_rows, str(candidate["guard_name"]))
    robustness = list(robustness_rows)
    if not robustness:
        raise ScaledContextGuardAcceptanceError("robustness_rows must not be empty")

    fixed_net = _to_float(fixed_row["net_usd"], "net_usd")
    fixed_drawdown = _to_float(
        fixed_row["max_trade_sequence_drawdown_usd"],
        "max_trade_sequence_drawdown_usd",
    )
    guarded_nets = [
        _to_float(row["guarded_holdout_net_usd"], "guarded_holdout_net_usd")
        for row in robustness
    ]
    improvements = [
        _to_float(row["guard_net_improvement_usd"], "guard_net_improvement_usd")
        for row in robustness
    ]
    average_nets = [
        _to_float(row["guarded_average_net_usd"], "guarded_average_net_usd")
        for row in robustness
    ]
    negative_window_rates = [
        _to_int(row["negative_holdout_windows"], "negative_holdout_windows")
        / _to_int(row["holdout_windows"], "holdout_windows")
        for row in robustness
    ]
    worst_window_losses = [
        abs(min(0.0, _to_float(row["worst_guarded_window_net_usd"], "worst_guarded_window_net_usd")))
        for row in robustness
    ]
    fixed_kept_trades = _to_int(fixed_row["kept_trades"], "kept_trades")
    return ScaledContextGuardAcceptanceSummary(
        guard_name=str(fixed_row["guard_name"]),
        conditions=str(fixed_row["conditions"]),
        fixed_input_trades=_to_int(fixed_row["input_trades"], "input_trades"),
        fixed_kept_trades=fixed_kept_trades,
        fixed_skipped_trades=_to_int(fixed_row["skipped_trades"], "skipped_trades"),
        fixed_net_usd=fixed_net,
        fixed_average_net_usd=_to_float(fixed_row["average_net_usd"], "average_net_usd"),
        fixed_profit_factor=_to_float(fixed_row["profit_factor"], "profit_factor"),
        fixed_max_drawdown_usd=fixed_drawdown,
        fixed_drawdown_to_net_ratio=abs(fixed_drawdown) / fixed_net if fixed_net > 0 else 1.0,
        fixed_worst_day=str(fixed_row["worst_day"]),
        fixed_worst_day_net_usd=_to_float(fixed_row["worst_day_net_usd"], "worst_day_net_usd"),
        robustness_rows=len(robustness),
        robustness_all_guarded_net_positive=all(net > 0 for net in guarded_nets),
        robustness_all_improved_vs_unguarded=all(improvement > 0 for improvement in improvements),
        robustness_worst_guarded_net_usd=min(guarded_nets),
        robustness_worst_average_net_usd=min(average_nets),
        robustness_max_negative_window_rate=max(negative_window_rates),
        robustness_worst_window_loss_usd=max(worst_window_losses),
        additional_fixed_guard_trades_required=max(
            0,
            int(gates["minimum_fixed_guard_trades"]) - fixed_kept_trades,
        ),
        additional_robustness_rows_required=max(
            0,
            int(gates["minimum_robustness_rows"]) - len(robustness),
        ),
    )


def scaled_context_guard_acceptance_passed(
    findings: Iterable[ScaledContextGuardAcceptanceFinding],
) -> bool:
    """Return true only when every guard acceptance gate passed."""

    return all(finding.passed for finding in findings)


def render_scaled_context_guard_acceptance_report(
    findings: Iterable[ScaledContextGuardAcceptanceFinding],
    *,
    config: dict[str, Any],
    sources: dict[str, str],
    sample_summary: ScaledContextGuardAcceptanceSummary | None = None,
) -> str:
    """Render a deterministic scaled context guard acceptance report."""

    finding_rows = list(findings)
    status = "PASS" if scaled_context_guard_acceptance_passed(finding_rows) else "FAIL"
    lines = [
        "# Scaled Context Guard Acceptance Report",
        "",
        "This report checks whether a fixed VWAP/delta context guard has enough",
        "evidence to become a Sierra implementation candidate. It is research-only",
        "and does not place, modify, cancel, or route orders.",
        "",
        "## Decision",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Overall status | {status} |",
        f"| Gate profile | {config['profile_id']} |",
        f"| Candidate guard | {config['candidate']['guard_name']} |",
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
                f"| Fixed input trades | {sample_summary.fixed_input_trades} |",
                f"| Fixed kept trades | {sample_summary.fixed_kept_trades} |",
                f"| Fixed skipped trades | {sample_summary.fixed_skipped_trades} |",
                f"| Fixed net USD | {_format_usd(sample_summary.fixed_net_usd)} |",
                (
                    "| Fixed average net USD | "
                    f"{_format_usd(sample_summary.fixed_average_net_usd)} |"
                ),
                f"| Fixed profit factor | {_format_ratio(sample_summary.fixed_profit_factor)} |",
                f"| Fixed max drawdown USD | {_format_usd(sample_summary.fixed_max_drawdown_usd)} |",
                (
                    "| Fixed drawdown to net ratio | "
                    f"{_format_ratio(sample_summary.fixed_drawdown_to_net_ratio)} |"
                ),
                f"| Fixed worst day | {sample_summary.fixed_worst_day} |",
                f"| Fixed worst day net USD | {_format_usd(sample_summary.fixed_worst_day_net_usd)} |",
                f"| Robustness rows | {sample_summary.robustness_rows} |",
                (
                    "| Worst robustness guarded net USD | "
                    f"{_format_usd(sample_summary.robustness_worst_guarded_net_usd)} |"
                ),
                (
                    "| Worst robustness average net USD | "
                    f"{_format_usd(sample_summary.robustness_worst_average_net_usd)} |"
                ),
                (
                    "| Maximum robustness negative-window rate | "
                    f"{_format_ratio(sample_summary.robustness_max_negative_window_rate)} |"
                ),
                (
                    "| Worst guarded window loss USD | "
                    f"{_format_usd(sample_summary.robustness_worst_window_loss_usd)} |"
                ),
                (
                    "| Additional fixed guard trades required | "
                    f"{sample_summary.additional_fixed_guard_trades_required} |"
                ),
                (
                    "| Additional robustness rows required | "
                    f"{sample_summary.additional_robustness_rows_required} |"
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


def write_scaled_context_guard_acceptance_report(
    path: str | Path,
    findings: Iterable[ScaledContextGuardAcceptanceFinding],
    *,
    config: dict[str, Any],
    sources: dict[str, str],
    sample_summary: ScaledContextGuardAcceptanceSummary | None = None,
) -> str:
    """Render and write a scaled context guard acceptance report."""

    report = render_scaled_context_guard_acceptance_report(
        findings,
        config=config,
        sources=sources,
        sample_summary=sample_summary,
    )
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report


def _minimum_fixed_guard_trades(
    summary: ScaledContextGuardAcceptanceSummary,
    minimum_trades: int,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="minimum_fixed_guard_trades",
        passed=summary.fixed_kept_trades >= minimum_trades,
        observed=str(summary.fixed_kept_trades),
        threshold=f">= {minimum_trades}",
        notes="Trades kept by the fixed guard over the full context sample.",
    )


def _minimum_fixed_guard_net_usd(
    summary: ScaledContextGuardAcceptanceSummary,
    minimum_net_usd: float,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="minimum_fixed_guard_net_usd",
        passed=summary.fixed_net_usd >= minimum_net_usd,
        observed=_format_usd(summary.fixed_net_usd),
        threshold=f">= {_format_usd(minimum_net_usd)}",
        notes="Full-sample net USD for the fixed guard.",
    )


def _minimum_fixed_guard_average_net_usd(
    summary: ScaledContextGuardAcceptanceSummary,
    minimum_average_net_usd: float,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="minimum_fixed_guard_average_net_usd",
        passed=summary.fixed_average_net_usd >= minimum_average_net_usd,
        observed=_format_usd(summary.fixed_average_net_usd),
        threshold=f">= {_format_usd(minimum_average_net_usd)}",
        notes="Average net per kept trade for the fixed guard.",
    )


def _minimum_fixed_guard_profit_factor(
    summary: ScaledContextGuardAcceptanceSummary,
    minimum_profit_factor: float,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="minimum_fixed_guard_profit_factor",
        passed=summary.fixed_profit_factor >= minimum_profit_factor,
        observed=_format_ratio(summary.fixed_profit_factor),
        threshold=f">= {_format_ratio(minimum_profit_factor)}",
        notes="Profit factor for fixed-guard kept trades.",
    )


def _maximum_fixed_guard_drawdown_to_net_ratio(
    summary: ScaledContextGuardAcceptanceSummary,
    maximum_ratio: float,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="maximum_fixed_guard_drawdown_to_net_ratio",
        passed=summary.fixed_drawdown_to_net_ratio <= maximum_ratio,
        observed=_format_ratio(summary.fixed_drawdown_to_net_ratio),
        threshold=f"<= {_format_ratio(maximum_ratio)}",
        notes="Peak-to-trough drawdown relative to fixed-guard final net.",
    )


def _maximum_fixed_guard_worst_day_loss(
    summary: ScaledContextGuardAcceptanceSummary,
    maximum_loss_usd: float,
) -> ScaledContextGuardAcceptanceFinding:
    worst_day_loss = abs(min(0.0, summary.fixed_worst_day_net_usd))
    return ScaledContextGuardAcceptanceFinding(
        gate_id="maximum_fixed_guard_worst_day_loss_usd",
        passed=worst_day_loss <= maximum_loss_usd,
        observed=_format_usd(worst_day_loss),
        threshold=f"<= {_format_usd(maximum_loss_usd)}",
        notes="Largest fixed-guard losing day by absolute USD loss.",
    )


def _minimum_robustness_rows(
    summary: ScaledContextGuardAcceptanceSummary,
    minimum_rows: int,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="minimum_robustness_rows",
        passed=summary.robustness_rows >= minimum_rows,
        observed=str(summary.robustness_rows),
        threshold=f">= {minimum_rows}",
        notes="Distinct chronological robustness window shapes evaluated.",
    )


def _all_robustness_guarded_net_positive(
    summary: ScaledContextGuardAcceptanceSummary,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="all_robustness_guarded_net_positive",
        passed=summary.robustness_all_guarded_net_positive,
        observed=str(summary.robustness_all_guarded_net_positive),
        threshold="True",
        notes="Every robustness window shape must have positive guarded net.",
    )


def _all_robustness_improved_vs_unguarded(
    summary: ScaledContextGuardAcceptanceSummary,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="all_robustness_improved_vs_unguarded",
        passed=summary.robustness_all_improved_vs_unguarded,
        observed=str(summary.robustness_all_improved_vs_unguarded),
        threshold="True",
        notes="Every robustness window shape must improve over unguarded rows.",
    )


def _minimum_worst_robustness_guarded_net(
    summary: ScaledContextGuardAcceptanceSummary,
    minimum_net_usd: float,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="minimum_worst_robustness_guarded_net_usd",
        passed=summary.robustness_worst_guarded_net_usd >= minimum_net_usd,
        observed=_format_usd(summary.robustness_worst_guarded_net_usd),
        threshold=f">= {_format_usd(minimum_net_usd)}",
        notes="Weakest guarded net across robustness window shapes.",
    )


def _minimum_worst_robustness_average_net(
    summary: ScaledContextGuardAcceptanceSummary,
    minimum_average_net_usd: float,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="minimum_worst_robustness_average_net_usd",
        passed=summary.robustness_worst_average_net_usd >= minimum_average_net_usd,
        observed=_format_usd(summary.robustness_worst_average_net_usd),
        threshold=f">= {_format_usd(minimum_average_net_usd)}",
        notes="Weakest guarded average net/trade across robustness shapes.",
    )


def _maximum_robustness_negative_window_rate(
    summary: ScaledContextGuardAcceptanceSummary,
    maximum_rate: float,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="maximum_robustness_negative_window_rate",
        passed=summary.robustness_max_negative_window_rate <= maximum_rate,
        observed=_format_ratio(summary.robustness_max_negative_window_rate),
        threshold=f"<= {_format_ratio(maximum_rate)}",
        notes="Highest negative holdout-window rate across robustness shapes.",
    )


def _maximum_worst_guarded_window_loss(
    summary: ScaledContextGuardAcceptanceSummary,
    maximum_loss_usd: float,
) -> ScaledContextGuardAcceptanceFinding:
    return ScaledContextGuardAcceptanceFinding(
        gate_id="maximum_worst_guarded_window_loss_usd",
        passed=summary.robustness_worst_window_loss_usd <= maximum_loss_usd,
        observed=_format_usd(summary.robustness_worst_window_loss_usd),
        threshold=f"<= {_format_usd(maximum_loss_usd)}",
        notes="Largest guarded losing holdout window by absolute USD loss.",
    )


def _select_guard_row(
    rows: Iterable[dict[str, Any]],
    guard_name: str,
) -> dict[str, Any]:
    matches = [row for row in rows if str(row.get("guard_name", "")) == guard_name]
    if len(matches) != 1:
        raise ScaledContextGuardAcceptanceError(
            f"Expected exactly one fixed guard row named {guard_name!r}; found {len(matches)}",
        )
    return matches[0]


def _interpret_acceptance(
    findings: list[ScaledContextGuardAcceptanceFinding],
) -> str:
    if scaled_context_guard_acceptance_passed(findings):
        return (
            "All configured gates passed. The guard is a research implementation "
            "candidate, but live routing remains disabled until a future explicit "
            "safety phase authorizes it."
        )
    failed = ", ".join(finding.gate_id for finding in findings if not finding.passed)
    return (
        "At least one configured gate failed. Do not promote this guard into "
        f"Sierra automation. Failed gates: {failed}."
    )


def _require_positive_int(values: dict[str, Any], key: str) -> None:
    if _config_int(values[key], key) <= 0:
        raise ConfigError(f"{key} must be a positive integer")


def _require_positive_float(values: dict[str, Any], key: str) -> None:
    if _config_float(values[key], key) <= 0:
        raise ConfigError(f"{key} must be positive")


def _require_ratio(values: dict[str, Any], key: str) -> None:
    value = _config_float(values[key], key)
    if not 0 <= value <= 1:
        raise ConfigError(f"{key} must be between 0 and 1")


def _config_int(value: Any, key: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{key} must be an integer") from exc


def _config_float(value: Any, key: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{key} must be numeric") from exc


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ScaledContextGuardAcceptanceError(
            f"Invalid integer {field_name}: {value!r}",
        ) from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ScaledContextGuardAcceptanceError(
            f"Invalid numeric {field_name}: {value!r}",
        ) from exc


def _format_usd(value: float) -> str:
    return f"{value:.2f}"


def _format_ratio(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")
