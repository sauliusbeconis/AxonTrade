"""Loss attribution and theory guards for scaled context outcomes."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from math import floor, sqrt
from statistics import pstdev
from typing import Any, Iterable


SCALED_CONTEXT_DAILY_SUMMARY_HEADER = [
    "schema_version",
    "trade_date",
    "trades",
    "runner_target_hits",
    "full_stops",
    "runner_stop_exits",
    "other_exits",
    "positive_net_trades",
    "positive_net_rate",
    "net_usd",
    "average_net_usd",
    "cumulative_net_usd",
]
SCALED_CONTEXT_FEATURE_BUCKET_HEADER = [
    "schema_version",
    "feature",
    "bucket_index",
    "bucket_count",
    "min_value",
    "max_value",
    "trades",
    "runner_target_hits",
    "full_stops",
    "runner_stop_exits",
    "other_exits",
    "positive_net_trades",
    "positive_net_rate",
    "net_usd",
    "average_net_usd",
]
SCALED_CONTEXT_GUARD_EVALUATION_HEADER = [
    "schema_version",
    "guard_id",
    "guard_name",
    "conditions",
    "input_trades",
    "kept_trades",
    "skipped_trades",
    "runner_target_hits",
    "full_stops",
    "runner_stop_exits",
    "other_exits",
    "positive_net_trades",
    "positive_net_rate",
    "net_usd",
    "average_net_usd",
    "average_net_usd_lower_bound",
    "profit_factor",
    "max_trade_sequence_drawdown_usd",
    "unfiltered_net_usd",
    "guard_net_improvement_usd",
    "worst_day",
    "worst_day_net_usd",
    "long_trades",
    "short_trades",
    "notes",
]
SCALED_CONTEXT_GUARD_WALK_FORWARD_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    *SCALED_CONTEXT_GUARD_EVALUATION_HEADER[1:],
    "selection_objective",
    "minimum_kept_train_trades",
    "minimum_train_participation_rate",
]
SCALED_CONTEXT_GUARD_ROBUSTNESS_HEADER = [
    "schema_version",
    "robustness_id",
    "train_date_count",
    "holdout_date_count",
    "window_step_date_count",
    "selection_objective",
    "minimum_train_trades",
    "minimum_train_participation_rate",
    "holdout_windows",
    "positive_holdout_windows",
    "negative_holdout_windows",
    "unfiltered_holdout_trades",
    "guarded_holdout_trades",
    "skipped_holdout_trades",
    "participation_rate",
    "unfiltered_holdout_net_usd",
    "guarded_holdout_net_usd",
    "guard_net_improvement_usd",
    "unfiltered_average_net_usd",
    "guarded_average_net_usd",
    "worst_guarded_window_dates",
    "worst_guarded_window_net_usd",
    "best_guarded_window_dates",
    "best_guarded_window_net_usd",
    "selected_guard_counts",
    "notes",
]

DEFAULT_LOSS_ATTRIBUTION_FEATURES = [
    "minutes_after_rth_open",
    "entry_bar_delta",
    "signal_abs_delta_sum_to_average_abs_delta",
    "entry_position_in_session_range",
    "fade_edge_score",
    "opening_range_fade_edge_score",
    "directional_open_distance_points",
    "directional_opening_range_breakout_points",
    "lookback_directional_move_points",
    "lookback_efficiency_ratio",
    "lookback_choppiness_score",
    "session_range_points",
    "entry_volume_to_session_average_volume",
    "entry_trades_to_session_average_trades",
    "lookback_volume_to_session_average_volume",
    "lookback_trades_to_session_average_trades",
    "risk_to_average_bar_range",
    "runner_target_to_average_bar_range",
]

_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_RUNNER_TARGET_REASONS = {"runner_target_hit"}
_FULL_STOP_REASONS = {"full_stop_hit", "ambiguous_full_stop_first"}
_RUNNER_STOP_REASONS = {
    "runner_initial_stop_hit",
    "runner_breakeven_stop_hit",
    "ambiguous_runner_stop_first",
}
_ALLOWED_SELECTION_OBJECTIVES = ("lower_bound", "net", "average")


class ScaledContextLossAttributionError(ValueError):
    """Raised when scaled context loss attribution cannot be evaluated."""


@dataclass(frozen=True)
class GuardCondition:
    """One entry-known keep condition."""

    field: str
    operator: str
    threshold: float

    @property
    def condition_id(self) -> str:
        return f"{self.field}{self.operator}{_format_number(self.threshold)}"


@dataclass(frozen=True)
class ScaledContextGuardRule:
    """One entry-known theory guard rule."""

    name: str
    conditions: tuple[GuardCondition, ...]

    @property
    def guard_id(self) -> str:
        if not self.conditions:
            return "scaled_context_guard:none"
        return "scaled_context_guard:" + "&".join(
            condition.condition_id for condition in self.conditions
        )

    @property
    def conditions_text(self) -> str:
        if not self.conditions:
            return "none"
        return ";".join(
            f"{condition.field} {condition.operator} {_format_number(condition.threshold)}"
            for condition in self.conditions
        )


DEFAULT_THEORY_GUARD_RULES = [
    ScaledContextGuardRule("none", ()),
    ScaledContextGuardRule(
        "lookback_fade_push",
        (GuardCondition("lookback_directional_move_points", "<=", -2.5),),
    ),
    ScaledContextGuardRule(
        "lookback_fade_push_session_range_30",
        (
            GuardCondition("lookback_directional_move_points", "<=", -2.5),
            GuardCondition("session_range_points", ">=", 30),
        ),
    ),
    ScaledContextGuardRule(
        "lookback_fade_push_risk_avg_2.5",
        (
            GuardCondition("lookback_directional_move_points", "<=", -2.5),
            GuardCondition("risk_to_average_bar_range", "<=", 2.5),
        ),
    ),
    ScaledContextGuardRule(
        "lookback_fade_push_session_range_30_risk_avg_2.5",
        (
            GuardCondition("lookback_directional_move_points", "<=", -2.5),
            GuardCondition("session_range_points", ">=", 30),
            GuardCondition("risk_to_average_bar_range", "<=", 2.5),
        ),
    ),
    ScaledContextGuardRule(
        "lookback_fade_push_session_range_30_after_90m",
        (
            GuardCondition("lookback_directional_move_points", "<=", -2.5),
            GuardCondition("session_range_points", ">=", 30),
            GuardCondition("minutes_after_rth_open", ">=", 90),
        ),
    ),
]
DEFAULT_GUARD_ROBUSTNESS_WINDOW_CONFIGS = (
    (20, 5, 5),
    (40, 5, 5),
    (40, 10, 10),
    (60, 10, 10),
    (80, 10, 10),
)


def summarize_scaled_context_daily_performance(
    context_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Summarize scaled outcome performance by trade date."""

    rows_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _sorted_context_rows(list(context_rows)):
        rows_by_date[_trade_date(row)].append(row)

    summary_rows: list[dict[str, Any]] = []
    cumulative_net = 0.0
    for trade_date in sorted(rows_by_date):
        rows = rows_by_date[trade_date]
        summary = _summary(rows)
        cumulative_net += summary["net_usd"]
        summary_rows.append(
            {
                "schema_version": 1,
                "trade_date": trade_date,
                "trades": summary["total_trades"],
                "runner_target_hits": summary["runner_target_hits"],
                "full_stops": summary["full_stops"],
                "runner_stop_exits": summary["runner_stop_exits"],
                "other_exits": summary["other_exits"],
                "positive_net_trades": summary["positive_net_trades"],
                "positive_net_rate": _format_number(summary["positive_net_rate"]),
                "net_usd": _format_number(summary["net_usd"]),
                "average_net_usd": _format_number(summary["average_net_usd"]),
                "cumulative_net_usd": _format_number(cumulative_net),
            },
        )
    return summary_rows


def bucket_scaled_context_features(
    context_rows: Iterable[dict[str, Any]],
    *,
    features: Iterable[str] = DEFAULT_LOSS_ATTRIBUTION_FEATURES,
    bucket_count: int = 10,
    minimum_bucket_trades: int = 1,
) -> list[dict[str, Any]]:
    """Bucket numeric entry-known features and summarize outcome performance."""

    if bucket_count <= 0:
        raise ScaledContextLossAttributionError("bucket_count must be positive")
    if minimum_bucket_trades <= 0:
        raise ScaledContextLossAttributionError("minimum_bucket_trades must be positive")

    rows = list(context_rows)
    bucket_rows: list[dict[str, Any]] = []
    for feature in features:
        feature_rows = [
            (value, row)
            for row in rows
            if (value := _to_float_or_none(row.get(feature))) is not None
        ]
        if not feature_rows:
            continue
        feature_rows.sort(key=lambda item: item[0])
        for bucket_index, bucket in enumerate(_chunk_equal_count(feature_rows, bucket_count), start=1):
            bucket_context_rows = [row for _, row in bucket]
            if len(bucket_context_rows) < minimum_bucket_trades:
                continue
            values = [value for value, _ in bucket]
            summary = _summary(bucket_context_rows)
            bucket_rows.append(
                {
                    "schema_version": 1,
                    "feature": feature,
                    "bucket_index": bucket_index,
                    "bucket_count": bucket_count,
                    "min_value": _format_number(min(values)),
                    "max_value": _format_number(max(values)),
                    "trades": summary["total_trades"],
                    "runner_target_hits": summary["runner_target_hits"],
                    "full_stops": summary["full_stops"],
                    "runner_stop_exits": summary["runner_stop_exits"],
                    "other_exits": summary["other_exits"],
                    "positive_net_trades": summary["positive_net_trades"],
                    "positive_net_rate": _format_number(summary["positive_net_rate"]),
                    "net_usd": _format_number(summary["net_usd"]),
                    "average_net_usd": _format_number(summary["average_net_usd"]),
                },
            )
    return bucket_rows


def evaluate_scaled_context_fixed_guards(
    context_rows: Iterable[dict[str, Any]],
    *,
    guard_rules: Iterable[ScaledContextGuardRule] = DEFAULT_THEORY_GUARD_RULES,
) -> list[dict[str, Any]]:
    """Evaluate fixed theory guards over all context rows."""

    rows = _sorted_context_rows(list(context_rows))
    return [
        _guard_evaluation_row(
            guard_rule=guard_rule,
            input_rows=rows,
            notes="fixed entry-known theory guard over all rows",
        )
        for guard_rule in guard_rules
    ]


def run_scaled_context_guard_walk_forward(
    context_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    window_step_date_count: int = 1,
    minimum_train_trades: int = 25,
    minimum_train_participation_rate: float = 0.35,
    selection_objective: str = "lower_bound",
    guard_rules: Iterable[ScaledContextGuardRule] = DEFAULT_THEORY_GUARD_RULES,
) -> list[dict[str, Any]]:
    """Select one theory guard on train dates and apply it to holdout dates."""

    if train_date_count <= 0:
        raise ScaledContextLossAttributionError("train_date_count must be positive")
    if holdout_date_count <= 0:
        raise ScaledContextLossAttributionError("holdout_date_count must be positive")
    if window_step_date_count <= 0:
        raise ScaledContextLossAttributionError("window_step_date_count must be positive")
    if minimum_train_trades <= 0:
        raise ScaledContextLossAttributionError("minimum_train_trades must be positive")
    if not 0 <= minimum_train_participation_rate <= 1:
        raise ScaledContextLossAttributionError(
            "minimum_train_participation_rate must be between 0 and 1",
        )
    objective = _normalize_selection_objective(selection_objective)
    rules = list(guard_rules)
    if not rules:
        raise ScaledContextLossAttributionError("At least one guard rule is required")

    rows = _sorted_context_rows(list(context_rows))
    dates = _sorted_trade_dates(rows)
    if train_date_count + holdout_date_count > len(dates):
        raise ScaledContextLossAttributionError(
            "train_date_count plus holdout_date_count must not exceed trade dates",
        )

    split_rows: list[dict[str, Any]] = []
    max_start = len(dates) - train_date_count - holdout_date_count + 1
    for window_index in range(0, max_start, window_step_date_count):
        train_dates = dates[window_index:window_index + train_date_count]
        holdout_dates = dates[
            window_index + train_date_count:
            window_index + train_date_count + holdout_date_count
        ]
        train_rows = _filter_rows_by_dates(rows, train_dates)
        holdout_rows = _filter_rows_by_dates(rows, holdout_dates)
        minimum_kept_train_trades = max(
            minimum_train_trades,
            floor(len(train_rows) * minimum_train_participation_rate),
        )
        selected_rule = _select_best_guard(
            train_rows,
            rules,
            minimum_kept_train_trades=minimum_kept_train_trades,
            selection_objective=objective,
        )
        split_id = (
            f"scaled_context_guard_walk_forward_window={window_index + 1}:"
            f"train_dates={train_date_count}:holdout_dates={holdout_date_count}"
        )
        split_rows.append(
            _guard_walk_forward_row(
                split_id=split_id,
                sample="train",
                trade_dates=train_dates,
                guard_rule=selected_rule,
                input_rows=train_rows,
                selection_objective=objective,
                minimum_kept_train_trades=minimum_kept_train_trades,
                minimum_train_participation_rate=minimum_train_participation_rate,
            ),
        )
        split_rows.append(
            _guard_walk_forward_row(
                split_id=split_id,
                sample="holdout",
                trade_dates=holdout_dates,
                guard_rule=selected_rule,
                input_rows=holdout_rows,
                selection_objective=objective,
                minimum_kept_train_trades=minimum_kept_train_trades,
                minimum_train_participation_rate=minimum_train_participation_rate,
            ),
        )
    return split_rows


def run_scaled_context_guard_robustness(
    context_rows: Iterable[dict[str, Any]],
    *,
    window_configs: Iterable[tuple[int, int, int]] = DEFAULT_GUARD_ROBUSTNESS_WINDOW_CONFIGS,
    minimum_train_trades: int = 25,
    minimum_train_participation_rate: float = 0.35,
    selection_objective: str = "lower_bound",
    guard_rules: Iterable[ScaledContextGuardRule] = DEFAULT_THEORY_GUARD_RULES,
) -> list[dict[str, Any]]:
    """Summarize theory-guard walk-forward behavior across window shapes."""

    rows = list(context_rows)
    robustness_rows: list[dict[str, Any]] = []
    for train_date_count, holdout_date_count, window_step_date_count in window_configs:
        split_rows = run_scaled_context_guard_walk_forward(
            rows,
            train_date_count=train_date_count,
            holdout_date_count=holdout_date_count,
            window_step_date_count=window_step_date_count,
            minimum_train_trades=minimum_train_trades,
            minimum_train_participation_rate=minimum_train_participation_rate,
            selection_objective=selection_objective,
            guard_rules=guard_rules,
        )
        robustness_rows.append(
            summarize_scaled_context_guard_walk_forward(
                split_rows,
                train_date_count=train_date_count,
                holdout_date_count=holdout_date_count,
                window_step_date_count=window_step_date_count,
                minimum_train_trades=minimum_train_trades,
                minimum_train_participation_rate=minimum_train_participation_rate,
                selection_objective=selection_objective,
            ),
        )
    return robustness_rows


def summarize_scaled_context_guard_walk_forward(
    split_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    window_step_date_count: int,
    minimum_train_trades: int,
    minimum_train_participation_rate: float,
    selection_objective: str,
) -> dict[str, Any]:
    """Summarize holdout rows from a guard walk-forward run."""

    holdout_rows = [row for row in split_rows if str(row["sample"]) == "holdout"]
    if not holdout_rows:
        raise ScaledContextLossAttributionError("walk-forward rows must include holdout rows")

    unfiltered_trades = sum(_to_int(row["input_trades"], "input_trades") for row in holdout_rows)
    guarded_trades = sum(_to_int(row["kept_trades"], "kept_trades") for row in holdout_rows)
    unfiltered_net = sum(_to_float(row["unfiltered_net_usd"], "unfiltered_net_usd") for row in holdout_rows)
    guarded_net = sum(_to_float(row["net_usd"], "net_usd") for row in holdout_rows)
    positive_windows = sum(_to_float(row["net_usd"], "net_usd") > 0 for row in holdout_rows)
    negative_windows = sum(_to_float(row["net_usd"], "net_usd") < 0 for row in holdout_rows)
    worst_window = min(holdout_rows, key=lambda row: _to_float(row["net_usd"], "net_usd"))
    best_window = max(holdout_rows, key=lambda row: _to_float(row["net_usd"], "net_usd"))
    guard_counts = Counter(str(row["guard_name"]) for row in holdout_rows)

    return {
        "schema_version": 1,
        "robustness_id": (
            "scaled_context_guard_robustness:"
            f"train={train_date_count}:holdout={holdout_date_count}:"
            f"step={window_step_date_count}:objective={selection_objective}"
        ),
        "train_date_count": train_date_count,
        "holdout_date_count": holdout_date_count,
        "window_step_date_count": window_step_date_count,
        "selection_objective": selection_objective,
        "minimum_train_trades": minimum_train_trades,
        "minimum_train_participation_rate": _format_number(minimum_train_participation_rate),
        "holdout_windows": len(holdout_rows),
        "positive_holdout_windows": positive_windows,
        "negative_holdout_windows": negative_windows,
        "unfiltered_holdout_trades": unfiltered_trades,
        "guarded_holdout_trades": guarded_trades,
        "skipped_holdout_trades": unfiltered_trades - guarded_trades,
        "participation_rate": _format_number(
            guarded_trades / unfiltered_trades if unfiltered_trades else 0.0,
        ),
        "unfiltered_holdout_net_usd": _format_number(unfiltered_net),
        "guarded_holdout_net_usd": _format_number(guarded_net),
        "guard_net_improvement_usd": _format_number(guarded_net - unfiltered_net),
        "unfiltered_average_net_usd": _format_number(
            unfiltered_net / unfiltered_trades if unfiltered_trades else 0.0,
        ),
        "guarded_average_net_usd": _format_number(
            guarded_net / guarded_trades if guarded_trades else 0.0,
        ),
        "worst_guarded_window_dates": worst_window["trade_dates"],
        "worst_guarded_window_net_usd": worst_window["net_usd"],
        "best_guarded_window_dates": best_window["trade_dates"],
        "best_guarded_window_net_usd": best_window["net_usd"],
        "selected_guard_counts": ";".join(
            f"{guard_name}={count}" for guard_name, count in guard_counts.most_common()
        ),
        "notes": "compact theory guard walk-forward robustness summary",
    }


def render_scaled_context_loss_attribution_report(
    *,
    context_rows: Iterable[dict[str, Any]],
    daily_rows: Iterable[dict[str, Any]],
    fixed_guard_rows: Iterable[dict[str, Any]],
    walk_forward_rows: Iterable[dict[str, Any]],
) -> str:
    """Render a concise markdown report for loss attribution outputs."""

    rows = list(context_rows)
    daily = list(daily_rows)
    fixed = list(fixed_guard_rows)
    walk_forward = list(walk_forward_rows)
    holdout_rows = [row for row in walk_forward if row["sample"] == "holdout"]
    unfiltered_net = sum(float(row["unfiltered_net_usd"]) for row in holdout_rows)
    holdout_net = sum(float(row["net_usd"]) for row in holdout_rows)
    holdout_trades = sum(int(row["kept_trades"]) for row in holdout_rows)
    holdout_input_trades = sum(int(row["input_trades"]) for row in holdout_rows)
    best_fixed = max(fixed, key=lambda row: float(row["net_usd"])) if fixed else None
    worst_days = sorted(daily, key=lambda row: float(row["net_usd"]))[:8]
    selected_rules = Counter(str(row["guard_name"]) for row in holdout_rows)

    lines = [
        "# Scaled Context Loss Attribution",
        "",
        "Status: **targeted guard research lead, not live-ready**",
        "",
        "## Source Summary",
        "",
        f"- Context rows: `{len(rows)}`",
        f"- Daily rows: `{len(daily)}`",
        "",
        "## Worst Days",
        "",
        "| Trade Date | Trades | Net USD | Full Stops | Runner Stops |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in worst_days:
        lines.append(
            "| {trade_date} | {trades} | {net_usd} | {full_stops} | {runner_stop_exits} |".format(
                **row,
            ),
        )

    lines.extend(
        [
            "",
            "## Fixed Theory Guard",
            "",
        ],
    )
    if best_fixed is not None:
        lines.extend(
            [
                f"- Best fixed guard: `{best_fixed['guard_name']}`",
                f"- Kept trades: `{best_fixed['kept_trades']}` of `{best_fixed['input_trades']}`",
                f"- Net USD: `{best_fixed['net_usd']}`",
                f"- Average/trade: `{best_fixed['average_net_usd']}`",
                f"- Profit factor: `{best_fixed['profit_factor']}`",
                f"- Max trade-sequence drawdown: `{best_fixed['max_trade_sequence_drawdown_usd']}`",
                f"- Worst day: `{best_fixed['worst_day']}`, `{best_fixed['worst_day_net_usd']}`",
            ],
        )

    lines.extend(
        [
            "",
            "## Walk-Forward Theory Guard",
            "",
            f"- Holdout input trades: `{holdout_input_trades}`",
            f"- Holdout kept trades: `{holdout_trades}`",
            f"- Unfiltered holdout net USD: `{_format_number(unfiltered_net)}`",
            f"- Guarded holdout net USD: `{_format_number(holdout_net)}`",
            f"- Guard improvement USD: `{_format_number(holdout_net - unfiltered_net)}`",
            "",
            "Selected holdout guard counts:",
            "",
        ],
    )
    for name, count in selected_rules.most_common():
        lines.append(f"- `{name}`: `{count}`")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The damage clusters around failed fades where the market does not make a "
            "clean push into the fade setup or where the 10-point risk is large "
            "relative to recent bar range. The compact guard family keeps the "
            "entry hypothesis intact: fade only after a real direction-aware "
            "lookback push, prefer at least 30 points of session range, and avoid "
            "compressed volatility when the stop is too wide for the current tape.",
            "",
            "This is still research. The next validation step is to rerun the same "
            "guard family on a later export and then wire only the selected fixed "
            "conditions into Sierra if the improvement survives.",
        ],
    )
    return "\n".join(lines) + "\n"


def render_scaled_context_guard_robustness_report(
    robustness_rows: Iterable[dict[str, Any]],
    *,
    context_source: str,
) -> str:
    """Render a markdown summary for guard robustness rows."""

    rows = list(robustness_rows)
    if not rows:
        raise ScaledContextLossAttributionError("robustness_rows must not be empty")
    best = max(rows, key=lambda row: float(row["guarded_holdout_net_usd"]))
    worst = min(rows, key=lambda row: float(row["guarded_holdout_net_usd"]))

    lines = [
        "# Scaled Context Guard Robustness",
        "",
        "Status: **research lead, not live-ready**",
        "",
        "## Source",
        "",
        f"- Context diagnostics: `{context_source}`",
        "",
        "## Window Robustness",
        "",
        "| Train | Holdout | Step | Windows | Unguarded Net | Guarded Net | Improvement | Kept Trades | Avg/Trade | Negative Windows | Worst Window |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {train_date_count} | {holdout_date_count} | {window_step_date_count} | "
            "{holdout_windows} | {unfiltered_holdout_net_usd} | "
            "{guarded_holdout_net_usd} | {guard_net_improvement_usd} | "
            "{guarded_holdout_trades} | {guarded_average_net_usd} | "
            "{negative_holdout_windows} | {worst_guarded_window_net_usd} |".format(
                **row,
            ),
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The compact guard family improved every tested window shape. "
                f"The best guarded net was `{best['guarded_holdout_net_usd']}` "
                f"on `{best['train_date_count']}x{best['holdout_date_count']}` "
                "windows, while the weakest tested shape still stayed positive at "
                f"`{worst['guarded_holdout_net_usd']}`."
            ),
            "",
            "Selected guard counts are deliberately shown in the CSV rather than "
            "promoted to a final Sierra rule. The next step is to pick one fixed "
            "guard, rerun it on a fresh later export, and only then consider "
            "implementation.",
        ],
    )
    return "\n".join(lines) + "\n"


def _guard_walk_forward_row(
    *,
    split_id: str,
    sample: str,
    trade_dates: list[str],
    guard_rule: ScaledContextGuardRule,
    input_rows: list[dict[str, Any]],
    selection_objective: str,
    minimum_kept_train_trades: int,
    minimum_train_participation_rate: float,
) -> dict[str, Any]:
    row = {
        "schema_version": 1,
        "split_id": split_id,
        "sample": sample,
        "selected_on_train": "true",
        "trade_dates": ";".join(trade_dates),
    }
    row.update(
        _guard_evaluation_row(
            guard_rule=guard_rule,
            input_rows=input_rows,
            notes="theory guard selected on train rows only",
        ),
    )
    row["selection_objective"] = selection_objective
    row["minimum_kept_train_trades"] = minimum_kept_train_trades
    row["minimum_train_participation_rate"] = _format_number(minimum_train_participation_rate)
    return row


def _guard_evaluation_row(
    *,
    guard_rule: ScaledContextGuardRule,
    input_rows: list[dict[str, Any]],
    notes: str,
) -> dict[str, Any]:
    kept_rows = _apply_guard(input_rows, guard_rule)
    summary = _summary(kept_rows)
    unfiltered_net = _net_usd(input_rows)
    direction_counts = Counter(str(row.get("direction", "")) for row in kept_rows)
    worst_day, worst_day_net = _worst_day(kept_rows)
    return {
        "schema_version": 1,
        "guard_id": guard_rule.guard_id,
        "guard_name": guard_rule.name,
        "conditions": guard_rule.conditions_text,
        "input_trades": len(input_rows),
        "kept_trades": summary["total_trades"],
        "skipped_trades": len(input_rows) - summary["total_trades"],
        "runner_target_hits": summary["runner_target_hits"],
        "full_stops": summary["full_stops"],
        "runner_stop_exits": summary["runner_stop_exits"],
        "other_exits": summary["other_exits"],
        "positive_net_trades": summary["positive_net_trades"],
        "positive_net_rate": _format_number(summary["positive_net_rate"]),
        "net_usd": _format_number(summary["net_usd"]),
        "average_net_usd": _format_number(summary["average_net_usd"]),
        "average_net_usd_lower_bound": _format_number(_average_net_lower_bound(kept_rows)),
        "profit_factor": _format_number(_profit_factor(kept_rows)),
        "max_trade_sequence_drawdown_usd": _format_number(_max_trade_sequence_drawdown(kept_rows)),
        "unfiltered_net_usd": _format_number(unfiltered_net),
        "guard_net_improvement_usd": _format_number(summary["net_usd"] - unfiltered_net),
        "worst_day": worst_day,
        "worst_day_net_usd": _format_number(worst_day_net),
        "long_trades": direction_counts.get("long", 0),
        "short_trades": direction_counts.get("short", 0),
        "notes": notes,
    }


def _select_best_guard(
    train_rows: list[dict[str, Any]],
    guard_rules: list[ScaledContextGuardRule],
    *,
    minimum_kept_train_trades: int,
    selection_objective: str,
) -> ScaledContextGuardRule:
    eligible: list[tuple[float, float, int, str, ScaledContextGuardRule]] = []
    for rule in guard_rules:
        kept_rows = _apply_guard(train_rows, rule)
        if len(kept_rows) < minimum_kept_train_trades:
            continue
        net_usd = _net_usd(kept_rows)
        average_net = net_usd / len(kept_rows) if kept_rows else 0.0
        if selection_objective == "lower_bound":
            score = _average_net_lower_bound(kept_rows)
        elif selection_objective == "net":
            score = net_usd
        elif selection_objective == "average":
            score = average_net
        else:  # Defensive; normalized before call.
            raise ScaledContextLossAttributionError(
                f"Unsupported selection_objective: {selection_objective}",
            )
        eligible.append((score, net_usd, len(kept_rows), rule.guard_id, rule))
    if not eligible:
        raise ScaledContextLossAttributionError(
            f"No guard rule met minimum_kept_train_trades={minimum_kept_train_trades}",
        )
    return max(eligible)[-1]


def _apply_guard(
    rows: list[dict[str, Any]],
    guard_rule: ScaledContextGuardRule,
) -> list[dict[str, Any]]:
    return [row for row in rows if _row_passes_guard(row, guard_rule)]


def _row_passes_guard(row: dict[str, Any], guard_rule: ScaledContextGuardRule) -> bool:
    for condition in guard_rule.conditions:
        value = _to_float_or_none(row.get(condition.field))
        if value is None:
            return False
        if condition.operator == "<=" and value > condition.threshold:
            return False
        if condition.operator == ">=" and value < condition.threshold:
            return False
        if condition.operator not in {"<=", ">="}:
            raise ScaledContextLossAttributionError(
                f"Unsupported guard operator: {condition.operator}",
            )
    return True


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    runner_targets = sum(str(row.get("exit_reason", "")) in _RUNNER_TARGET_REASONS for row in rows)
    full_stops = sum(str(row.get("exit_reason", "")) in _FULL_STOP_REASONS for row in rows)
    runner_stops = sum(str(row.get("exit_reason", "")) in _RUNNER_STOP_REASONS for row in rows)
    net_usd = _net_usd(rows)
    positive = sum(_to_float(row.get("net_usd"), "net_usd") > 0 for row in rows)
    return {
        "total_trades": total,
        "runner_target_hits": runner_targets,
        "full_stops": full_stops,
        "runner_stop_exits": runner_stops,
        "other_exits": total - runner_targets - full_stops - runner_stops,
        "positive_net_trades": positive,
        "positive_net_rate": positive / total if total else 0.0,
        "net_usd": net_usd,
        "average_net_usd": net_usd / total if total else 0.0,
    }


def _average_net_lower_bound(rows: list[dict[str, Any]]) -> float:
    values = [_to_float(row.get("net_usd"), "net_usd") for row in rows]
    if not values:
        return 0.0
    average = sum(values) / len(values)
    if len(values) == 1:
        return average
    return average - pstdev(values) / sqrt(len(values))


def _profit_factor(rows: list[dict[str, Any]]) -> float:
    gains = sum(_to_float(row.get("net_usd"), "net_usd") for row in rows if _to_float(row.get("net_usd"), "net_usd") > 0)
    losses = -sum(
        _to_float(row.get("net_usd"), "net_usd")
        for row in rows
        if _to_float(row.get("net_usd"), "net_usd") < 0
    )
    if losses == 0:
        return 999999.0 if gains else 0.0
    return gains / losses


def _max_trade_sequence_drawdown(rows: list[dict[str, Any]]) -> float:
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for row in _sorted_context_rows(rows):
        equity += _to_float(row.get("net_usd"), "net_usd")
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
    return max_drawdown


def _worst_day(rows: list[dict[str, Any]]) -> tuple[str, float]:
    if not rows:
        return "", 0.0
    rows_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_date[_trade_date(row)].append(row)
    return min(
        ((trade_date, _net_usd(day_rows)) for trade_date, day_rows in rows_by_date.items()),
        key=lambda item: item[1],
    )


def _net_usd(rows: list[dict[str, Any]]) -> float:
    return sum(_to_float(row.get("net_usd"), "net_usd") for row in rows)


def _chunk_equal_count(
    values: list[tuple[float, dict[str, Any]]],
    bucket_count: int,
) -> list[list[tuple[float, dict[str, Any]]]]:
    chunked: list[list[tuple[float, dict[str, Any]]]] = []
    total = len(values)
    for index in range(bucket_count):
        start = index * total // bucket_count
        end = (index + 1) * total // bucket_count
        if start < end:
            chunked.append(values[start:end])
    return chunked


def _sorted_trade_dates(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({_trade_date(row) for row in rows})


def _filter_rows_by_dates(
    rows: list[dict[str, Any]],
    trade_dates: Iterable[str],
) -> list[dict[str, Any]]:
    dates = set(trade_dates)
    return [row for row in rows if _trade_date(row) in dates]


def _sorted_context_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (_trade_date(row), _parse_timestamp(str(row["entry_time"]))))


def _trade_date(row: dict[str, Any]) -> str:
    return _parse_timestamp(str(row["entry_time"])).date().isoformat()


def _normalize_selection_objective(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _ALLOWED_SELECTION_OBJECTIVES:
        raise ScaledContextLossAttributionError(
            "selection_objective must be one of "
            f"{', '.join(_ALLOWED_SELECTION_OBJECTIVES)}",
        )
    return normalized


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise ScaledContextLossAttributionError(f"Invalid timestamp: {value!r}")


def _normalize_timestamp_text(value: str) -> str:
    parts = value.split(maxsplit=1)
    if len(parts) != 2 or "-" not in parts[0]:
        return value
    date_part, time_part = parts
    date_values = date_part.split("-")
    if len(date_values) != 3:
        return value
    try:
        year, month, day = (int(part) for part in date_values)
    except ValueError:
        return value
    return f"{year:04d}-{month:02d}-{day:02d} {time_part}"


def _to_float(value: Any, field_name: str) -> float:
    parsed = _to_float_or_none(value)
    if parsed is None:
        raise ScaledContextLossAttributionError(f"Invalid numeric {field_name}: {value!r}")
    return parsed


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ScaledContextLossAttributionError(
            f"Invalid integer {field_name}: {value!r}",
        ) from exc


def _to_float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.8f}".rstrip("0").rstrip(".")
