#!/usr/bin/env python3
"""Run the full auction-regime target/breakeven research stack."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.data import (
    SierraExportError,
    load_sierra_export_config,
    normalize_sierra_bar_study_file,
)
from axontrade.research import (
    DEFAULT_AUCTION_REGIME_STACK_ACCEPTANCE_CONFIG_PATH,
    SIGNAL_AUCTION_REGIME_BREAKEVEN_REPORT_HEADER,
    SIGNAL_AUCTION_REGIME_DIAGNOSTIC_HEADER,
    SIGNAL_AUCTION_REGIME_FILTER_SWEEP_HEADER,
    SIGNAL_AUCTION_REGIME_TARGET_R_REPORT_HEADER,
    SIGNAL_AUCTION_REGIME_TRADE_AUDIT_HEADER,
    AuctionRegimeStackAcceptanceError,
    SignalAuctionRegimeBreakevenReportError,
    SignalAuctionRegimeDiagnosticError,
    SignalAuctionRegimeFilterExperimentError,
    SignalAuctionRegimeTargetReportError,
    SignalAuctionRegimeTradeAuditError,
    SignalLogError,
    TradeOutcomeError,
    auction_regime_stack_acceptance_passed,
    audit_signal_auction_regime_trades,
    evaluate_auction_regime_stack_acceptance,
    load_auction_regime_stack_acceptance_config,
    load_signal_log_rows_csv,
    report_signal_auction_regime_breakeven,
    report_signal_auction_regime_target_r,
    run_signal_auction_regime_diagnostics,
    run_signal_auction_regime_filter_walk_forward_sweep,
    validate_signal_entries_against_bars,
    write_auction_regime_stack_acceptance_report,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_orderflow_bar_export.yaml"
DEFAULT_BARS_EXPORT = (
    "/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/"
    "AxonTrade_ES_OrderflowExport_NY_Large.txt"
)
DEFAULT_SIGNAL_LOG = "data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv"
DEFAULT_QUALITY_DIAGNOSTICS = "reports/sierra-signal-log-quality-diagnostics-large-sample.csv"
DEFAULT_REPORTS_DIR = "reports"
DEFAULT_OUTPUT_TAG = "large-sample"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate auction-regime diagnostics, selected target/breakeven "
            "stacks, trade audits, and acceptance reports."
        ),
    )
    parser.add_argument("--bars-export", default=DEFAULT_BARS_EXPORT)
    parser.add_argument("--signal-log", default=DEFAULT_SIGNAL_LOG)
    parser.add_argument("--quality-diagnostics", default=DEFAULT_QUALITY_DIAGNOSTICS)
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--output-tag", default=DEFAULT_OUTPUT_TAG)
    parser.add_argument(
        "--samples",
        choices=("all", "overlap", "holdout1"),
        default="all",
        help="Which rolling selections to regenerate.",
    )
    parser.add_argument(
        "--stacks",
        choices=("all", "target_r", "breakeven"),
        default="all",
        help="Which exit stacks to regenerate.",
    )
    parser.add_argument("--symbol", default="ESU26-CME")
    parser.add_argument("--chart-number", type=int, default=2)
    parser.add_argument("--session-phase", default="rth")
    parser.add_argument("--export-config", default=DEFAULT_EXPORT_CONFIG)
    parser.add_argument("--train-date-count", type=int, default=8)
    parser.add_argument("--holdout-date-count", type=int, default=2)
    parser.add_argument("--minimum-train-trades", type=int, default=4)
    parser.add_argument("--filter-max-original-reward-risks", default="2,2.5,3.5,999")
    parser.add_argument("--filter-min-minutes-after-rth-open", default="0,60")
    parser.add_argument("--filter-max-minutes-after-rth-open", default="120,240,390")
    parser.add_argument("--filter-max-session-range-points", default="20,35,50,999")
    parser.add_argument("--filter-max-fade-edge-scores", default="0.65,0.75,0.85,1")
    parser.add_argument("--filter-max-vwap-stretch-points", default="3,6,10,20,999")
    parser.add_argument("--filter-max-open-stretch-points", default="3,6,10,20,999")
    parser.add_argument("--direction-filters", default="all,long,short")
    parser.add_argument("--target-r-multiples", default="0.5,1,1.5,2,2.5,3,3.5,4,4.5,5")
    parser.add_argument(
        "--breakeven-target-r-multiples",
        default="0.5,1,1.25,1.5,2,2.5,3,3.5,4,4.5,5",
    )
    parser.add_argument(
        "--breakeven-trigger-r-multiples",
        default="0.5,0.75,1,1.25,1.5,2,2.5",
    )
    parser.add_argument(
        "--acceptance-config",
        default=DEFAULT_AUCTION_REGIME_STACK_ACCEPTANCE_CONFIG_PATH,
    )
    parser.add_argument("--instrument-root")
    parser.add_argument("--slippage-ticks-per-side", type=int)
    parser.add_argument(
        "--entry-match-mode",
        choices=("bar_index", "timestamp", "auto"),
        default="auto",
    )
    parser.add_argument(
        "--fail-on-reject",
        action="store_true",
        help="Return exit code 1 when any generated acceptance report fails.",
    )
    args = parser.parse_args()

    try:
        outputs = _output_paths(Path(args.reports_dir), args.output_tag)
        _log(f"loading Sierra export from {args.bars_export}")
        bars = normalize_sierra_bar_study_file(
            args.bars_export,
            symbol=args.symbol,
            chart_number=args.chart_number,
            session_phase=args.session_phase,
            config=load_sierra_export_config(args.export_config),
            compute_opening_range=True,
        )
        _log(f"loaded {len(bars)} normalized bars")
        signal_rows = load_signal_log_rows_csv(args.signal_log)
        validate_signal_entries_against_bars(bars, signal_rows)
        quality_rows = _read_csv(Path(args.quality_diagnostics))
        acceptance_config = load_auction_regime_stack_acceptance_config(args.acceptance_config)

        _log("computing auction-regime diagnostics")
        regime_rows = run_signal_auction_regime_diagnostics(
            bar_rows=bars,
            quality_diagnostic_rows=quality_rows,
        )
        _write_csv(outputs["diagnostics"], SIGNAL_AUCTION_REGIME_DIAGNOSTIC_HEADER, regime_rows)
        _log(f"wrote {len(regime_rows)} diagnostics to {outputs['diagnostics']}")

        selected_rules = _selected_rule_sets(args, regime_rows)
        for sample_key, rule_rows in selected_rules.items():
            _write_csv(
                outputs[f"filter_{sample_key}"],
                SIGNAL_AUCTION_REGIME_FILTER_SWEEP_HEADER,
                rule_rows,
            )
            _log(
                f"wrote {sample_key} selected auction-regime rules to "
                f"{outputs[f'filter_{sample_key}']}",
            )

        acceptance_passes = []
        for sample_key, rule_rows in selected_rules.items():
            acceptance_passes.extend(
                _run_stacks(
                    args=args,
                    bars=bars,
                    signal_rows=signal_rows,
                    regime_rows=regime_rows,
                    selection_rows=rule_rows,
                    outputs=outputs,
                    sample_key=sample_key,
                    acceptance_config=acceptance_config,
                    acceptance_config_path=args.acceptance_config,
                ),
            )
    except (
        AuctionRegimeStackAcceptanceError,
        SierraExportError,
        SignalAuctionRegimeBreakevenReportError,
        SignalAuctionRegimeDiagnosticError,
        SignalAuctionRegimeFilterExperimentError,
        SignalAuctionRegimeTargetReportError,
        SignalAuctionRegimeTradeAuditError,
        SignalLogError,
        TradeOutcomeError,
        OSError,
    ) as exc:
        _log(f"error: {exc}")
        return 2

    if args.fail_on_reject and not all(acceptance_passes):
        return 1
    return 0


def _walk_forward_rules(
    args: argparse.Namespace,
    regime_rows: list[dict[str, object]],
    *,
    holdout_date_count: int,
) -> list[dict[str, object]]:
    return run_signal_auction_regime_filter_walk_forward_sweep(
        regime_rows,
        train_date_count=args.train_date_count,
        holdout_date_count=holdout_date_count,
        minimum_train_trades=args.minimum_train_trades,
        max_original_reward_risks=_parse_float_list(args.filter_max_original_reward_risks),
        min_minutes_after_rth_open_values=_parse_float_list(args.filter_min_minutes_after_rth_open),
        max_minutes_after_rth_open_values=_parse_float_list(args.filter_max_minutes_after_rth_open),
        max_session_range_points_values=_parse_float_list(args.filter_max_session_range_points),
        max_fade_edge_scores=_parse_float_list(args.filter_max_fade_edge_scores),
        max_vwap_stretch_points_values=_parse_float_list(args.filter_max_vwap_stretch_points),
        max_open_stretch_points_values=_parse_float_list(args.filter_max_open_stretch_points),
        direction_filters=_parse_string_list(args.direction_filters),
    )


def _selected_rule_sets(
    args: argparse.Namespace,
    regime_rows: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    selected: dict[str, list[dict[str, object]]] = {}
    if args.samples in {"all", "overlap"}:
        selected["overlap"] = _walk_forward_rules(
            args,
            regime_rows,
            holdout_date_count=args.holdout_date_count,
        )
    if args.samples in {"all", "holdout1"}:
        selected["holdout1"] = _walk_forward_rules(
            args,
            regime_rows,
            holdout_date_count=1,
        )
    return selected


def _run_stacks(
    *,
    args: argparse.Namespace,
    bars: list[dict[str, object]],
    signal_rows: list[dict[str, object]],
    regime_rows: list[dict[str, object]],
    selection_rows: list[dict[str, object]],
    outputs: dict[str, Path],
    sample_key: str,
    acceptance_config: dict[str, object],
    acceptance_config_path: str,
) -> list[bool]:
    stack_results: dict[str, bool] = {}
    if args.stacks in {"all", "target_r"}:
        stack_results["target_r"] = _run_target_stack(
            args=args,
            bars=bars,
            signal_rows=signal_rows,
            regime_rows=regime_rows,
            selection_rows=selection_rows,
            outputs=outputs,
            sample_key=sample_key,
            acceptance_config=acceptance_config,
            acceptance_config_path=acceptance_config_path,
        )
    if args.stacks in {"all", "breakeven"}:
        stack_results["breakeven"] = _run_breakeven_stack(
            args=args,
            bars=bars,
            signal_rows=signal_rows,
            regime_rows=regime_rows,
            selection_rows=selection_rows,
            outputs=outputs,
            sample_key=sample_key,
            acceptance_config=acceptance_config,
            acceptance_config_path=acceptance_config_path,
        )
    _log(
        f"{sample_key}: "
        + ", ".join(
            f"{stack}_acceptance={'PASS' if passed else 'FAIL'}"
            for stack, passed in stack_results.items()
        ),
    )
    return list(stack_results.values())


def _run_target_stack(
    *,
    args: argparse.Namespace,
    bars: list[dict[str, object]],
    signal_rows: list[dict[str, object]],
    regime_rows: list[dict[str, object]],
    selection_rows: list[dict[str, object]],
    outputs: dict[str, Path],
    sample_key: str,
    acceptance_config: dict[str, object],
    acceptance_config_path: str,
) -> bool:
    _log(f"{sample_key}: running target-R stack")
    target_report_rows = report_signal_auction_regime_target_r(
        bars=bars,
        signal_rows=signal_rows,
        regime_rows=regime_rows,
        selection_rows=selection_rows,
        minimum_train_trades=args.minimum_train_trades,
        target_r_multiples=_parse_float_list(args.target_r_multiples),
        direction_filters=_parse_string_list(args.direction_filters),
        instrument_root=args.instrument_root,
        slippage_ticks_per_side=args.slippage_ticks_per_side,
        entry_match_mode=args.entry_match_mode,
    )
    _write_csv(
        outputs[f"target_report_{sample_key}"],
        SIGNAL_AUCTION_REGIME_TARGET_R_REPORT_HEADER,
        target_report_rows,
    )
    _log(f"{sample_key}: wrote target-R report to {outputs[f'target_report_{sample_key}']}")
    target_audit_rows = audit_signal_auction_regime_trades(
        bars=bars,
        signal_rows=signal_rows,
        regime_rows=regime_rows,
        selection_rows=selection_rows,
        stack_type="target_r",
        minimum_train_trades=args.minimum_train_trades,
        target_r_multiples=_parse_float_list(args.target_r_multiples),
        direction_filters=_parse_string_list(args.direction_filters),
        instrument_root=args.instrument_root,
        slippage_ticks_per_side=args.slippage_ticks_per_side,
        entry_match_mode=args.entry_match_mode,
    )
    return _write_audit_and_acceptance(
        audit_rows=target_audit_rows,
        audit_path=outputs[f"target_audit_{sample_key}"],
        acceptance_path=outputs[f"target_acceptance_{sample_key}"],
        acceptance_config=acceptance_config,
        acceptance_config_path=acceptance_config_path,
    )


def _run_breakeven_stack(
    *,
    args: argparse.Namespace,
    bars: list[dict[str, object]],
    signal_rows: list[dict[str, object]],
    regime_rows: list[dict[str, object]],
    selection_rows: list[dict[str, object]],
    outputs: dict[str, Path],
    sample_key: str,
    acceptance_config: dict[str, object],
    acceptance_config_path: str,
) -> bool:
    _log(f"{sample_key}: running breakeven stack")
    breakeven_report_rows = report_signal_auction_regime_breakeven(
        bars=bars,
        signal_rows=signal_rows,
        regime_rows=regime_rows,
        selection_rows=selection_rows,
        minimum_train_trades=args.minimum_train_trades,
        target_r_multiples=_parse_float_list(args.breakeven_target_r_multiples),
        breakeven_trigger_r_multiples=_parse_float_list(args.breakeven_trigger_r_multiples),
        direction_filters=_parse_string_list(args.direction_filters),
        instrument_root=args.instrument_root,
        slippage_ticks_per_side=args.slippage_ticks_per_side,
        entry_match_mode=args.entry_match_mode,
    )
    _write_csv(
        outputs[f"breakeven_report_{sample_key}"],
        SIGNAL_AUCTION_REGIME_BREAKEVEN_REPORT_HEADER,
        breakeven_report_rows,
    )
    _log(f"{sample_key}: wrote breakeven report to {outputs[f'breakeven_report_{sample_key}']}")
    breakeven_audit_rows = audit_signal_auction_regime_trades(
        bars=bars,
        signal_rows=signal_rows,
        regime_rows=regime_rows,
        selection_rows=selection_rows,
        stack_type="breakeven",
        minimum_train_trades=args.minimum_train_trades,
        target_r_multiples=_parse_float_list(args.breakeven_target_r_multiples),
        breakeven_trigger_r_multiples=_parse_float_list(args.breakeven_trigger_r_multiples),
        direction_filters=_parse_string_list(args.direction_filters),
        instrument_root=args.instrument_root,
        slippage_ticks_per_side=args.slippage_ticks_per_side,
        entry_match_mode=args.entry_match_mode,
    )
    return _write_audit_and_acceptance(
        audit_rows=breakeven_audit_rows,
        audit_path=outputs[f"breakeven_audit_{sample_key}"],
        acceptance_path=outputs[f"breakeven_acceptance_{sample_key}"],
        acceptance_config=acceptance_config,
        acceptance_config_path=acceptance_config_path,
    )


def _write_audit_and_acceptance(
    *,
    audit_rows: list[dict[str, object]],
    audit_path: Path,
    acceptance_path: Path,
    acceptance_config: dict[str, object],
    acceptance_config_path: str,
) -> bool:
    _write_csv(audit_path, SIGNAL_AUCTION_REGIME_TRADE_AUDIT_HEADER, audit_rows)
    findings = evaluate_auction_regime_stack_acceptance(
        audit_rows,
        config=acceptance_config,
    )
    write_auction_regime_stack_acceptance_report(
        acceptance_path,
        findings,
        config=acceptance_config,
        sources={
            "audit": str(audit_path),
            "config": acceptance_config_path,
        },
    )
    _log(f"wrote audit to {audit_path}")
    _log(f"wrote acceptance report to {acceptance_path}")
    return auction_regime_stack_acceptance_passed(findings)


def _output_paths(reports_dir: Path, tag: str) -> dict[str, Path]:
    suffix = _clean_tag(tag)
    return {
        "diagnostics": reports_dir / f"sierra-signal-log-auction-regime-diagnostics-{suffix}.csv",
        "filter_overlap": reports_dir / f"sierra-signal-log-auction-regime-filter-walk-forward-{suffix}.csv",
        "filter_holdout1": reports_dir
        / f"sierra-signal-log-auction-regime-filter-walk-forward-holdout1-{suffix}.csv",
        "target_report_overlap": reports_dir
        / f"sierra-signal-log-auction-regime-target-r-walk-forward-{suffix}.csv",
        "target_report_holdout1": reports_dir
        / f"sierra-signal-log-auction-regime-target-r-walk-forward-holdout1-{suffix}.csv",
        "breakeven_report_overlap": reports_dir
        / f"sierra-signal-log-auction-regime-breakeven-walk-forward-{suffix}.csv",
        "breakeven_report_holdout1": reports_dir
        / f"sierra-signal-log-auction-regime-breakeven-walk-forward-holdout1-{suffix}.csv",
        "target_audit_overlap": reports_dir
        / f"sierra-signal-log-auction-regime-target-r-trade-audit-{suffix}.csv",
        "target_audit_holdout1": reports_dir
        / f"sierra-signal-log-auction-regime-target-r-trade-audit-holdout1-{suffix}.csv",
        "breakeven_audit_overlap": reports_dir
        / f"sierra-signal-log-auction-regime-breakeven-trade-audit-{suffix}.csv",
        "breakeven_audit_holdout1": reports_dir
        / f"sierra-signal-log-auction-regime-breakeven-trade-audit-holdout1-{suffix}.csv",
        "target_acceptance_overlap": reports_dir
        / f"sierra-signal-log-auction-regime-target-r-acceptance-{suffix}.md",
        "target_acceptance_holdout1": reports_dir
        / f"sierra-signal-log-auction-regime-target-r-acceptance-holdout1-{suffix}.md",
        "breakeven_acceptance_overlap": reports_dir
        / f"sierra-signal-log-auction-regime-breakeven-acceptance-{suffix}.md",
        "breakeven_acceptance_holdout1": reports_dir
        / f"sierra-signal-log-auction-regime-breakeven-acceptance-holdout1-{suffix}.md",
    }


def _clean_tag(value: str) -> str:
    tag = value.strip()
    if not tag:
        raise ValueError("output tag must not be blank")
    return tag


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _log(message: str) -> None:
    print(message, flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
