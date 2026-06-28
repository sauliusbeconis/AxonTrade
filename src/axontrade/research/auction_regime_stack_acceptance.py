"""Acceptance gates for selected auction-regime stack audit rows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from axontrade.config import ConfigError, load_yaml, require_fields


DEFAULT_AUCTION_REGIME_STACK_ACCEPTANCE_CONFIG_PATH = (
    "config/research/auction_regime_stack_acceptance_gates.yaml"
)
_REQUIRED_CONFIG_FIELDS = [
    "schema_version",
    "profile_id",
    "gates.minimum_unique_holdout_evaluated_signals",
    "gates.minimum_unique_holdout_trade_dates",
    "gates.maximum_duplicate_holdout_evaluated_rows",
    "gates.require_positive_unique_holdout_net",
    "gates.maximum_single_signal_net_share",
]


class AuctionRegimeStackAcceptanceError(ValueError):
    """Raised when auction-regime stack acceptance inputs are invalid."""


@dataclass(frozen=True)
class AuctionRegimeStackAcceptanceFinding:
    """One auction-regime stack acceptance-gate evaluation result."""

    gate_id: str
    passed: bool
    observed: str
    threshold: str
    notes: str


@dataclass(frozen=True)
class AuctionRegimeStackSampleSummary:
    """Sample coverage metrics for an auction-regime stack audit."""

    holdout_evaluated_rows: int
    unique_holdout_evaluated_signals: int
    unique_holdout_trade_dates: int
    duplicate_holdout_evaluated_rows: int
    unique_holdout_net_usd: float
    positive_unique_holdout_net_usd: float
    largest_signal_net_usd: float
    largest_signal_net_share: float
    additional_unique_signals_required: int
    additional_trade_dates_required: int
    duplicate_rows_to_remove: int


def load_auction_regime_stack_acceptance_config(
    path: str | Path = DEFAULT_AUCTION_REGIME_STACK_ACCEPTANCE_CONFIG_PATH,
) -> dict[str, Any]:
    """Load and validate the auction-regime stack acceptance-gate config."""

    config = load_yaml(path)
    validate_auction_regime_stack_acceptance_config(config)
    return config


def validate_auction_regime_stack_acceptance_config(
    config: dict[str, Any],
) -> dict[str, Any]:
    """Validate an auction-regime stack acceptance-gate config mapping."""

    require_fields(
        config,
        _REQUIRED_CONFIG_FIELDS,
        context="auction-regime stack acceptance config",
    )
    if _config_int(config["schema_version"], "schema_version") != 1:
        raise ConfigError("auction-regime stack acceptance config schema_version must be 1")

    gates = config["gates"]
    _require_nonnegative_int(gates, "minimum_unique_holdout_evaluated_signals")
    _require_nonnegative_int(gates, "minimum_unique_holdout_trade_dates")
    _require_nonnegative_int(gates, "maximum_duplicate_holdout_evaluated_rows")
    if not isinstance(gates["require_positive_unique_holdout_net"], bool):
        raise ConfigError("require_positive_unique_holdout_net must be a boolean")
    max_share = _config_float(
        gates["maximum_single_signal_net_share"],
        "maximum_single_signal_net_share",
    )
    if max_share <= 0 or max_share > 1:
        raise ConfigError("maximum_single_signal_net_share must be greater than 0 and no more than 1")
    return config


def evaluate_auction_regime_stack_acceptance(
    audit_rows: Iterable[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
) -> list[AuctionRegimeStackAcceptanceFinding]:
    """Evaluate trade-level audit rows against configured evidence gates."""

    acceptance_config = (
        load_auction_regime_stack_acceptance_config() if config is None else config
    )
    validate_auction_regime_stack_acceptance_config(acceptance_config)
    gates = acceptance_config["gates"]
    holdout_evaluated = _holdout_evaluated_rows(list(audit_rows))

    findings = [
        _minimum_unique_holdout_evaluated_signals(
            holdout_evaluated,
            int(gates["minimum_unique_holdout_evaluated_signals"]),
        ),
        _minimum_unique_holdout_trade_dates(
            holdout_evaluated,
            int(gates["minimum_unique_holdout_trade_dates"]),
        ),
        _maximum_duplicate_holdout_evaluated_rows(
            holdout_evaluated,
            int(gates["maximum_duplicate_holdout_evaluated_rows"]),
        ),
    ]
    if gates["require_positive_unique_holdout_net"]:
        findings.append(_positive_unique_holdout_net(holdout_evaluated))
    findings.append(
        _maximum_single_signal_net_share(
            holdout_evaluated,
            float(gates["maximum_single_signal_net_share"]),
        ),
    )
    return findings


def summarize_auction_regime_stack_sample(
    audit_rows: Iterable[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
) -> AuctionRegimeStackSampleSummary:
    """Summarize sample coverage and remaining evidence gaps."""

    acceptance_config = (
        load_auction_regime_stack_acceptance_config() if config is None else config
    )
    validate_auction_regime_stack_acceptance_config(acceptance_config)
    gates = acceptance_config["gates"]
    holdout_evaluated = _holdout_evaluated_rows(list(audit_rows))
    unique_rows = _unique_signal_rows(holdout_evaluated)
    trade_dates = {
        str(row.get("trade_date", "")).strip()
        for row in unique_rows
        if str(row.get("trade_date", "")).strip()
    }
    duplicate_rows = _duplicate_holdout_evaluated_rows(holdout_evaluated)
    unique_net = _unique_holdout_net(holdout_evaluated)
    positive_unique_net = sum(
        max(0.0, _to_float(row.get("selected_net_usd", 0), "selected_net_usd"))
        for row in unique_rows
    )
    largest_signal_net = _largest_positive_signal_net(unique_rows)
    largest_share = (
        largest_signal_net / positive_unique_net
        if positive_unique_net > 0
        else 1.0
    )
    return AuctionRegimeStackSampleSummary(
        holdout_evaluated_rows=len(holdout_evaluated),
        unique_holdout_evaluated_signals=len(unique_rows),
        unique_holdout_trade_dates=len(trade_dates),
        duplicate_holdout_evaluated_rows=duplicate_rows,
        unique_holdout_net_usd=unique_net,
        positive_unique_holdout_net_usd=positive_unique_net,
        largest_signal_net_usd=largest_signal_net,
        largest_signal_net_share=largest_share,
        additional_unique_signals_required=max(
            0,
            int(gates["minimum_unique_holdout_evaluated_signals"]) - len(unique_rows),
        ),
        additional_trade_dates_required=max(
            0,
            int(gates["minimum_unique_holdout_trade_dates"]) - len(trade_dates),
        ),
        duplicate_rows_to_remove=max(
            0,
            duplicate_rows - int(gates["maximum_duplicate_holdout_evaluated_rows"]),
        ),
    )


def auction_regime_stack_acceptance_passed(
    findings: Iterable[AuctionRegimeStackAcceptanceFinding],
) -> bool:
    """Return true only when every acceptance gate passed."""

    return all(finding.passed for finding in findings)


def render_auction_regime_stack_acceptance_report(
    findings: Iterable[AuctionRegimeStackAcceptanceFinding],
    *,
    config: dict[str, Any],
    sources: dict[str, str],
    sample_summary: AuctionRegimeStackSampleSummary | None = None,
) -> str:
    """Render a deterministic Markdown acceptance report."""

    finding_rows = list(findings)
    status = "PASS" if auction_regime_stack_acceptance_passed(finding_rows) else "FAIL"
    lines = [
        "# Auction-Regime Stack Acceptance Report",
        "",
        "This report checks whether selected auction-regime stack audit rows pass",
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
                f"| Holdout evaluated rows | {sample_summary.holdout_evaluated_rows} |",
                (
                    "| Unique evaluated holdout signals | "
                    f"{sample_summary.unique_holdout_evaluated_signals} |"
                ),
                f"| Unique holdout trade dates | {sample_summary.unique_holdout_trade_dates} |",
                (
                    "| Duplicate evaluated holdout rows | "
                    f"{sample_summary.duplicate_holdout_evaluated_rows} |"
                ),
                f"| Unique holdout net USD | {_format_usd(sample_summary.unique_holdout_net_usd)} |",
                (
                    "| Positive unique holdout net USD | "
                    f"{_format_usd(sample_summary.positive_unique_holdout_net_usd)} |"
                ),
                f"| Largest signal net USD | {_format_usd(sample_summary.largest_signal_net_usd)} |",
                f"| Largest signal share | {_format_ratio(sample_summary.largest_signal_net_share)} |",
                (
                    "| Additional unique signals required | "
                    f"{sample_summary.additional_unique_signals_required} |"
                ),
                (
                    "| Additional trade dates required | "
                    f"{sample_summary.additional_trade_dates_required} |"
                ),
                f"| Duplicate rows to remove | {sample_summary.duplicate_rows_to_remove} |",
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


def write_auction_regime_stack_acceptance_report(
    path: str | Path,
    findings: Iterable[AuctionRegimeStackAcceptanceFinding],
    *,
    config: dict[str, Any],
    sources: dict[str, str],
    sample_summary: AuctionRegimeStackSampleSummary | None = None,
) -> str:
    """Render and write an auction-regime stack acceptance report."""

    report = render_auction_regime_stack_acceptance_report(
        findings,
        config=config,
        sources=sources,
        sample_summary=sample_summary,
    )
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report


def _minimum_unique_holdout_evaluated_signals(
    rows: list[dict[str, Any]],
    minimum_signals: int,
) -> AuctionRegimeStackAcceptanceFinding:
    observed = len(_unique_signal_rows(rows))
    return AuctionRegimeStackAcceptanceFinding(
        gate_id="minimum_unique_holdout_evaluated_signals",
        passed=observed >= minimum_signals,
        observed=str(observed),
        threshold=f">= {minimum_signals}",
        notes="Unique evaluated holdout signal IDs after selected auction and exit policies.",
    )


def _minimum_unique_holdout_trade_dates(
    rows: list[dict[str, Any]],
    minimum_dates: int,
) -> AuctionRegimeStackAcceptanceFinding:
    observed = len(
        {
            str(row.get("trade_date", "")).strip()
            for row in _unique_signal_rows(rows)
            if str(row.get("trade_date", "")).strip()
        },
    )
    return AuctionRegimeStackAcceptanceFinding(
        gate_id="minimum_unique_holdout_trade_dates",
        passed=observed >= minimum_dates,
        observed=str(observed),
        threshold=f">= {minimum_dates}",
        notes="Distinct trade dates represented by unique evaluated holdout signals.",
    )


def _maximum_duplicate_holdout_evaluated_rows(
    rows: list[dict[str, Any]],
    maximum_duplicates: int,
) -> AuctionRegimeStackAcceptanceFinding:
    duplicate_rows = _duplicate_holdout_evaluated_rows(rows)
    return AuctionRegimeStackAcceptanceFinding(
        gate_id="maximum_duplicate_holdout_evaluated_rows",
        passed=duplicate_rows <= maximum_duplicates,
        observed=str(duplicate_rows),
        threshold=f"<= {maximum_duplicates}",
        notes="Evaluated holdout rows whose signal ID appears more than once in the sample.",
    )


def _positive_unique_holdout_net(
    rows: list[dict[str, Any]],
) -> AuctionRegimeStackAcceptanceFinding:
    observed_net = _unique_holdout_net(rows)
    return AuctionRegimeStackAcceptanceFinding(
        gate_id="positive_unique_holdout_net",
        passed=observed_net > 0,
        observed=_format_usd(observed_net),
        threshold="> 0.00",
        notes="Net USD after de-duplicating evaluated holdout signals by first occurrence.",
    )


def _maximum_single_signal_net_share(
    rows: list[dict[str, Any]],
    maximum_share: float,
) -> AuctionRegimeStackAcceptanceFinding:
    unique_rows = _unique_signal_rows(rows)
    positive_net = sum(
        max(0.0, _to_float(row.get("selected_net_usd", 0), "selected_net_usd"))
        for row in unique_rows
    )
    largest_signal_net = _largest_positive_signal_net(unique_rows)
    observed_share = largest_signal_net / positive_net if positive_net > 0 else 1.0
    return AuctionRegimeStackAcceptanceFinding(
        gate_id="maximum_single_signal_net_share",
        passed=observed_share <= maximum_share,
        observed=_format_ratio(observed_share),
        threshold=f"<= {_format_ratio(maximum_share)}",
        notes="Largest unique winning signal as a share of total positive unique holdout net.",
    )


def _holdout_evaluated_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if str(row.get("sample", "")).lower() == "holdout"
        and str(row.get("decision", "")).lower() == "evaluated"
    ]


def _unique_signal_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        signal_id = str(row.get("signal_id", "")).strip()
        if not signal_id or signal_id in seen:
            continue
        seen.add(signal_id)
        unique_rows.append(row)
    return unique_rows


def _unique_holdout_net(rows: list[dict[str, Any]]) -> float:
    return sum(
        _to_float(row.get("selected_net_usd", 0), "selected_net_usd")
        for row in _unique_signal_rows(rows)
    )


def _duplicate_holdout_evaluated_rows(rows: list[dict[str, Any]]) -> int:
    return sum(_is_true(row.get("sample_duplicate_signal")) for row in rows)


def _largest_positive_signal_net(rows: list[dict[str, Any]]) -> float:
    return max(
        (
            max(0.0, _to_float(row.get("selected_net_usd", 0), "selected_net_usd"))
            for row in rows
        ),
        default=0.0,
    )


def _interpret_acceptance(findings: list[AuctionRegimeStackAcceptanceFinding]) -> str:
    if auction_regime_stack_acceptance_passed(findings):
        return (
            "All configured evidence gates passed. This still does not authorize live "
            "routing; it only means the selected stack is eligible for the next "
            "simulation-only review."
        )
    failed = [finding.gate_id for finding in findings if not finding.passed]
    return (
        "One or more evidence gates failed: "
        + ", ".join(failed)
        + ". Do not treat the selected auction-regime stack as automation-ready."
    )


def _require_nonnegative_int(config: dict[str, Any], field_name: str) -> None:
    value = _config_int(config[field_name], field_name)
    if value < 0:
        raise ConfigError(f"{field_name} must be nonnegative")


def _config_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value))
    except ValueError as exc:
        raise ConfigError(f"{field_name} must be an integer") from exc


def _config_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise ConfigError(f"{field_name} must be numeric") from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise AuctionRegimeStackAcceptanceError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _is_true(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _format_usd(value: float) -> str:
    return f"{value:.2f}"


def _format_ratio(value: float) -> str:
    return f"{value:.2%}"
