"""Research helpers for AxonTrade."""

from axontrade.research.absorption_experiments import (
    ABSORPTION_REWARD_RISK_SWEEP_HEADER,
    AbsorptionExperimentError,
    run_absorption_reward_risk_sweep,
    run_absorption_reward_risk_train_holdout_sweep,
    run_absorption_reward_risk_walk_forward_sweep,
)
from axontrade.research.acceptance import (
    DEFAULT_PRICE_ONLY_ACCEPTANCE_CONFIG_PATH,
    AcceptanceFinding,
    AcceptanceGateError,
    evaluate_price_only_acceptance,
    load_price_only_acceptance_config,
    price_only_acceptance_passed,
    render_price_only_acceptance_report,
    validate_price_only_acceptance_config,
    write_price_only_acceptance_report,
)
from axontrade.research.auction_regime_stack_acceptance import (
    DEFAULT_AUCTION_REGIME_STACK_ACCEPTANCE_CONFIG_PATH,
    AuctionRegimeStackAcceptanceError,
    AuctionRegimeStackAcceptanceFinding,
    AuctionRegimeStackSampleSummary,
    auction_regime_stack_acceptance_passed,
    evaluate_auction_regime_stack_acceptance,
    load_auction_regime_stack_acceptance_config,
    render_auction_regime_stack_acceptance_report,
    summarize_auction_regime_stack_sample,
    validate_auction_regime_stack_acceptance_config,
    write_auction_regime_stack_acceptance_report,
)
from axontrade.research.delta_impulse_overlay_validation import (
    DELTA_IMPULSE_STRATEGY_ID,
    DeltaImpulseOverlayComparison,
    DeltaImpulseOverlayValidationError,
    DeltaImpulseRuleConfig,
    compare_delta_impulse_overlay_log,
    generate_delta_impulse_overlay_candidates,
    render_delta_impulse_overlay_validation_report,
    write_delta_impulse_overlay_validation_report,
)
from axontrade.research.liquidity_sweep_absorption import (
    DEFAULT_LIQUIDITY_SWEEP_ABSORPTION_CONFIG,
    LiquiditySweepAbsorptionError,
    evaluate_liquidity_sweep_absorption_reversal,
    load_liquidity_sweep_absorption_config,
    validate_liquidity_sweep_absorption_config,
)
from axontrade.research.price_only_baseline import (
    BaselineError,
    evaluate_price_only_liquidity_sweep_reversal,
    evaluate_price_only_vwap_reclaim,
    load_price_only_bar_rows_csv,
    load_price_only_baseline_config,
    load_price_only_liquidity_sweep_config,
    validate_price_only_baseline_config,
    validate_price_only_liquidity_sweep_config,
)
from axontrade.research.price_only_experiments import (
    PRICE_ONLY_PARAMETER_SWEEP_HEADER,
    PRICE_ONLY_TRAIN_HOLDOUT_SWEEP_HEADER,
    PriceOnlyExperimentError,
    run_price_only_parameter_sweep,
    run_price_only_train_holdout_sweep,
    run_price_only_walk_forward_sweep,
)
from axontrade.research.rejection_reasons import (
    ALLOWED_REJECTION_REASON_CATEGORIES,
    DEFAULT_REJECTION_REASON_CATALOG,
    REJECTION_REASON_CATALOG_REQUIRED_FIELDS,
    REJECTION_REASON_DETAIL_REQUIRED_FIELDS,
    RejectionReasonCatalogError,
    load_rejection_reason_catalog,
    rejection_reason_codes,
    rejection_reason_logging_fields,
    validate_rejection_reason_catalog,
)
from axontrade.research.scaled_context_diagnostics import (
    SCALED_CONTEXT_DIAGNOSTIC_HEADER,
    ScaledContextDiagnosticError,
    run_scaled_outcome_context_diagnostics,
)
from axontrade.research.scaled_context_filter_experiments import (
    SCALED_CONTEXT_FILTER_SWEEP_HEADER,
    SCALED_CONTEXT_FILTER_WALK_FORWARD_HEADER,
    ScaledContextFilterExperimentError,
    run_scaled_context_filter_sweep,
    run_scaled_context_filter_walk_forward_sweep,
)
from axontrade.research.scaled_context_filter_experiments import (
    scaled_context_row_passes_filter as scaled_context_row_passes_filter,
)
from axontrade.research.scaled_context_guard_acceptance import (
    DEFAULT_SCALED_CONTEXT_GUARD_ACCEPTANCE_CONFIG_PATH as DEFAULT_SCALED_CONTEXT_GUARD_ACCEPTANCE_CONFIG_PATH,
)
from axontrade.research.scaled_context_guard_acceptance import (
    ScaledContextGuardAcceptanceError as ScaledContextGuardAcceptanceError,
)
from axontrade.research.scaled_context_guard_acceptance import (
    ScaledContextGuardAcceptanceFinding as ScaledContextGuardAcceptanceFinding,
)
from axontrade.research.scaled_context_guard_acceptance import (
    ScaledContextGuardAcceptanceSummary as ScaledContextGuardAcceptanceSummary,
)
from axontrade.research.scaled_context_guard_acceptance import (
    evaluate_scaled_context_guard_acceptance as evaluate_scaled_context_guard_acceptance,
)
from axontrade.research.scaled_context_guard_acceptance import (
    load_scaled_context_guard_acceptance_config as load_scaled_context_guard_acceptance_config,
)
from axontrade.research.scaled_context_guard_acceptance import (
    render_scaled_context_guard_acceptance_report as render_scaled_context_guard_acceptance_report,
)
from axontrade.research.scaled_context_guard_acceptance import (
    scaled_context_guard_acceptance_passed as scaled_context_guard_acceptance_passed,
)
from axontrade.research.scaled_context_guard_acceptance import (
    summarize_scaled_context_guard_acceptance_sample as summarize_scaled_context_guard_acceptance_sample,
)
from axontrade.research.scaled_context_guard_acceptance import (
    validate_scaled_context_guard_acceptance_config as validate_scaled_context_guard_acceptance_config,
)
from axontrade.research.scaled_context_guard_acceptance import (
    write_scaled_context_guard_acceptance_report as write_scaled_context_guard_acceptance_report,
)
from axontrade.research.scaled_context_loss_attribution import (
    DEFAULT_GUARD_ROBUSTNESS_WINDOW_CONFIGS as DEFAULT_GUARD_ROBUSTNESS_WINDOW_CONFIGS,
)
from axontrade.research.scaled_context_loss_attribution import (
    DEFAULT_THEORY_GUARD_RULES as DEFAULT_THEORY_GUARD_RULES,
)
from axontrade.research.scaled_context_loss_attribution import (
    SCALED_CONTEXT_DAILY_SUMMARY_HEADER as SCALED_CONTEXT_DAILY_SUMMARY_HEADER,
)
from axontrade.research.scaled_context_loss_attribution import (
    SCALED_CONTEXT_FEATURE_BUCKET_HEADER as SCALED_CONTEXT_FEATURE_BUCKET_HEADER,
)
from axontrade.research.scaled_context_loss_attribution import (
    SCALED_CONTEXT_GUARD_EVALUATION_HEADER as SCALED_CONTEXT_GUARD_EVALUATION_HEADER,
)
from axontrade.research.scaled_context_loss_attribution import (
    SCALED_CONTEXT_GUARD_ROBUSTNESS_HEADER as SCALED_CONTEXT_GUARD_ROBUSTNESS_HEADER,
)
from axontrade.research.scaled_context_loss_attribution import (
    SCALED_CONTEXT_GUARD_WALK_FORWARD_HEADER as SCALED_CONTEXT_GUARD_WALK_FORWARD_HEADER,
)
from axontrade.research.scaled_context_loss_attribution import (
    GuardCondition as GuardCondition,
)
from axontrade.research.scaled_context_loss_attribution import (
    ScaledContextGuardRule as ScaledContextGuardRule,
)
from axontrade.research.scaled_context_loss_attribution import (
    ScaledContextLossAttributionError as ScaledContextLossAttributionError,
)
from axontrade.research.scaled_context_loss_attribution import (
    bucket_scaled_context_features as bucket_scaled_context_features,
)
from axontrade.research.scaled_context_loss_attribution import (
    evaluate_scaled_context_fixed_guards as evaluate_scaled_context_fixed_guards,
)
from axontrade.research.scaled_context_loss_attribution import (
    render_scaled_context_guard_robustness_report as render_scaled_context_guard_robustness_report,
)
from axontrade.research.scaled_context_loss_attribution import (
    render_scaled_context_loss_attribution_report as render_scaled_context_loss_attribution_report,
)
from axontrade.research.scaled_context_loss_attribution import (
    run_scaled_context_guard_robustness as run_scaled_context_guard_robustness,
)
from axontrade.research.scaled_context_loss_attribution import (
    run_scaled_context_guard_walk_forward as run_scaled_context_guard_walk_forward,
)
from axontrade.research.scaled_context_loss_attribution import (
    summarize_scaled_context_daily_performance as summarize_scaled_context_daily_performance,
)
from axontrade.research.scaled_context_loss_attribution import (
    summarize_scaled_context_guard_walk_forward as summarize_scaled_context_guard_walk_forward,
)
from axontrade.research.scaled_context_selected_veto import (
    SCALED_CONTEXT_SELECTED_TRADE_AUDIT_HEADER as SCALED_CONTEXT_SELECTED_TRADE_AUDIT_HEADER,
)
from axontrade.research.scaled_context_selected_veto import (
    SCALED_CONTEXT_SELECTED_VETO_WALK_FORWARD_HEADER as SCALED_CONTEXT_SELECTED_VETO_WALK_FORWARD_HEADER,
)
from axontrade.research.scaled_context_selected_veto import (
    ScaledContextSelectedVetoError as ScaledContextSelectedVetoError,
)
from axontrade.research.scaled_context_selected_veto import (
    audit_scaled_context_selected_trades as audit_scaled_context_selected_trades,
)
from axontrade.research.scaled_context_selected_veto import (
    run_scaled_context_selected_veto_walk_forward as run_scaled_context_selected_veto_walk_forward,
)
from axontrade.research.scaled_scalp_acceptance import (
    DEFAULT_SCALED_SCALP_ACCEPTANCE_CONFIG_PATH,
    ScaledScalpAcceptanceError,
    ScaledScalpAcceptanceFinding,
    ScaledScalpAcceptanceSummary,
    evaluate_scaled_scalp_acceptance,
    load_scaled_scalp_acceptance_config,
    render_scaled_scalp_acceptance_report,
    scaled_scalp_acceptance_passed,
    summarize_scaled_scalp_acceptance_sample,
    validate_scaled_scalp_acceptance_config,
    write_scaled_scalp_acceptance_report,
)
from axontrade.research.session_clock_alignment import (
    SESSION_CLOCK_ALIGNMENT_HEADER,
    SessionClockAlignmentError,
    run_session_clock_alignment_diagnostics,
)
from axontrade.research.signal_auction_regime_breakeven_report import (
    SIGNAL_AUCTION_REGIME_BREAKEVEN_REPORT_HEADER,
    SignalAuctionRegimeBreakevenReportError,
    report_signal_auction_regime_breakeven,
)
from axontrade.research.signal_auction_regime_diagnostics import (
    SIGNAL_AUCTION_REGIME_DIAGNOSTIC_HEADER,
    SignalAuctionRegimeDiagnosticError,
    run_signal_auction_regime_diagnostics,
)
from axontrade.research.signal_auction_regime_filter_experiments import (
    SIGNAL_AUCTION_REGIME_FILTER_SWEEP_HEADER,
    SignalAuctionRegimeFilterExperimentError,
    run_signal_auction_regime_filter_sweep,
    run_signal_auction_regime_filter_train_holdout_sweep,
    run_signal_auction_regime_filter_walk_forward_sweep,
)
from axontrade.research.signal_auction_regime_guard_report import (
    SIGNAL_AUCTION_REGIME_GUARD_REPORT_HEADER,
    SignalAuctionRegimeGuardReportError,
    report_signal_auction_regime_guard,
)
from axontrade.research.signal_auction_regime_health_gate_report import (
    SIGNAL_AUCTION_REGIME_HEALTH_GATE_REPORT_HEADER,
    SignalAuctionRegimeHealthGateReportError,
    report_signal_auction_regime_health_gate,
)
from axontrade.research.signal_auction_regime_target_r_report import (
    SIGNAL_AUCTION_REGIME_TARGET_R_REPORT_HEADER,
    SignalAuctionRegimeTargetReportError,
    report_signal_auction_regime_target_r,
)
from axontrade.research.signal_auction_regime_trade_audit import (
    SIGNAL_AUCTION_REGIME_TRADE_AUDIT_HEADER,
    SignalAuctionRegimeTradeAuditError,
    audit_signal_auction_regime_trades,
)
from axontrade.research.signal_context_diagnostics import (
    SIGNAL_CONTEXT_DIAGNOSTIC_HEADER,
    SignalContextDiagnosticError,
    run_signal_context_diagnostics,
)
from axontrade.research.signal_context_filter_experiments import (
    SIGNAL_CONTEXT_FILTER_SWEEP_HEADER,
    SIGNAL_CONTEXT_FILTER_WALK_FORWARD_HEADER,
    SignalContextFilterExperimentError,
    run_signal_context_filter_sweep,
    run_signal_context_filter_walk_forward_sweep,
)
from axontrade.research.signal_dynamic_exit_experiments import (
    SIGNAL_BREAKEVEN_STOP_SWEEP_HEADER,
    SIGNAL_BREAKEVEN_STOP_WALK_FORWARD_HEADER,
    SignalDynamicExitExperimentError,
    evaluate_signal_breakeven_stop_outcomes,
    run_signal_breakeven_stop_sweep,
    run_signal_breakeven_stop_walk_forward_sweep,
)
from axontrade.research.signal_health_gate_experiments import (
    SIGNAL_HEALTH_GATE_SWEEP_HEADER,
    SIGNAL_HEALTH_GATE_WALK_FORWARD_HEADER,
    SignalHealthGateExperimentError,
    evaluate_signal_health_gate,
    run_signal_health_gate_sweep,
    run_signal_health_gate_walk_forward_sweep,
)
from axontrade.research.signal_log import (
    SignalLogError,
    load_signal_log_rows_csv,
    load_signal_log_schema,
    validate_signal_log_row,
    validate_signal_log_rows,
    validate_signal_log_schema,
)
from axontrade.research.signal_news_exclusion import (
    NEWS_ANNOTATION_FIELDS,
    NEWS_EVENT_CSV_HEADER,
    NewsExclusionError,
    annotate_rows_with_news_blackouts,
    filter_news_blackout_rows,
)
from axontrade.research.signal_quality_diagnostics import (
    SIGNAL_QUALITY_DIAGNOSTIC_HEADER,
    SignalQualityDiagnosticError,
    run_signal_quality_diagnostics,
)
from axontrade.research.signal_quality_filter_experiments import (
    SIGNAL_QUALITY_FILTER_SWEEP_HEADER,
    SIGNAL_QUALITY_FILTER_WALK_FORWARD_HEADER,
    SignalQualityFilterExperimentError,
    run_signal_quality_filter_sweep,
    run_signal_quality_filter_walk_forward_sweep,
)
from axontrade.research.signal_quality_health_gate_experiments import (
    SIGNAL_QUALITY_HEALTH_GATE_WALK_FORWARD_HEADER,
    SignalQualityHealthGateExperimentError,
    run_signal_quality_health_gate_walk_forward_sweep,
)
from axontrade.research.signal_scaled_scalp_experiments import (
    SIGNAL_SCALED_SCALP_SWEEP_HEADER,
    SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER,
    SignalScaledScalpExperimentError,
    evaluate_signal_scaled_scalp_outcomes,
    run_signal_scaled_scalp_sweep,
    run_signal_scaled_scalp_walk_forward_sweep,
)
from axontrade.research.signal_structure_filter_experiments import (
    SIGNAL_STRUCTURE_FILTER_SWEEP_HEADER,
    SIGNAL_STRUCTURE_FILTER_WALK_FORWARD_HEADER,
    SignalStructureFilterExperimentError,
    run_signal_structure_filter_sweep,
    run_signal_structure_filter_walk_forward_sweep,
)
from axontrade.research.signal_target_experiments import (
    SIGNAL_TARGET_R_SWEEP_HEADER,
    SIGNAL_TARGET_R_WALK_FORWARD_SWEEP_HEADER,
    SignalTargetExperimentError,
    run_signal_target_r_sweep,
    run_signal_target_r_walk_forward_sweep,
)
from axontrade.research.trade_outcomes import (
    TRADE_OUTCOME_CSV_HEADER,
    TRADE_OUTCOME_DAILY_CSV_HEADER,
    TRADE_PATH_DIAGNOSTIC_CSV_HEADER,
    TradeOutcomeError,
    diagnose_trade_paths,
    evaluate_trade_outcomes,
    load_signal_rows_csv,
    summarize_trade_outcomes,
    summarize_trade_outcomes_by_day,
    validate_signal_entries_against_bars,
)
from axontrade.research.volume_at_price_absorption import (
    VAP_ABSORPTION_DIAGNOSTIC_HEADER,
    VAP_ABSORPTION_THRESHOLD_SWEEP_HEADER,
    VAP_TRAP_FILTER_SWEEP_HEADER,
    VolumeAtPriceAbsorptionError,
    run_vap_absorption_diagnostics,
    run_vap_absorption_threshold_sweep,
    run_vap_absorption_threshold_train_holdout_sweep,
    run_vap_absorption_threshold_walk_forward_sweep,
    run_vap_trap_filter_sweep,
    run_vap_trap_filter_train_holdout_sweep,
    run_vap_trap_filter_walk_forward_sweep,
    summarize_vap_absorption_diagnostics,
)

__all__ = [
    "ABSORPTION_REWARD_RISK_SWEEP_HEADER",
    "ALLOWED_REJECTION_REASON_CATEGORIES",
    "DEFAULT_AUCTION_REGIME_STACK_ACCEPTANCE_CONFIG_PATH",
    "DEFAULT_LIQUIDITY_SWEEP_ABSORPTION_CONFIG",
    "DEFAULT_PRICE_ONLY_ACCEPTANCE_CONFIG_PATH",
    "DEFAULT_REJECTION_REASON_CATALOG",
    "DEFAULT_SCALED_SCALP_ACCEPTANCE_CONFIG_PATH",
    "DELTA_IMPULSE_STRATEGY_ID",
    "NEWS_ANNOTATION_FIELDS",
    "NEWS_EVENT_CSV_HEADER",
    "PRICE_ONLY_PARAMETER_SWEEP_HEADER",
    "PRICE_ONLY_TRAIN_HOLDOUT_SWEEP_HEADER",
    "REJECTION_REASON_CATALOG_REQUIRED_FIELDS",
    "REJECTION_REASON_DETAIL_REQUIRED_FIELDS",
    "SCALED_CONTEXT_DIAGNOSTIC_HEADER",
    "SCALED_CONTEXT_FILTER_SWEEP_HEADER",
    "SCALED_CONTEXT_FILTER_WALK_FORWARD_HEADER",
    "SESSION_CLOCK_ALIGNMENT_HEADER",
    "SIGNAL_AUCTION_REGIME_BREAKEVEN_REPORT_HEADER",
    "SIGNAL_AUCTION_REGIME_DIAGNOSTIC_HEADER",
    "SIGNAL_AUCTION_REGIME_FILTER_SWEEP_HEADER",
    "SIGNAL_AUCTION_REGIME_GUARD_REPORT_HEADER",
    "SIGNAL_AUCTION_REGIME_HEALTH_GATE_REPORT_HEADER",
    "SIGNAL_AUCTION_REGIME_TARGET_R_REPORT_HEADER",
    "SIGNAL_AUCTION_REGIME_TRADE_AUDIT_HEADER",
    "SIGNAL_BREAKEVEN_STOP_SWEEP_HEADER",
    "SIGNAL_BREAKEVEN_STOP_WALK_FORWARD_HEADER",
    "SIGNAL_CONTEXT_DIAGNOSTIC_HEADER",
    "SIGNAL_CONTEXT_FILTER_SWEEP_HEADER",
    "SIGNAL_CONTEXT_FILTER_WALK_FORWARD_HEADER",
    "SIGNAL_HEALTH_GATE_SWEEP_HEADER",
    "SIGNAL_HEALTH_GATE_WALK_FORWARD_HEADER",
    "SIGNAL_QUALITY_DIAGNOSTIC_HEADER",
    "SIGNAL_QUALITY_FILTER_SWEEP_HEADER",
    "SIGNAL_QUALITY_FILTER_WALK_FORWARD_HEADER",
    "SIGNAL_QUALITY_HEALTH_GATE_WALK_FORWARD_HEADER",
    "SIGNAL_SCALED_SCALP_SWEEP_HEADER",
    "SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER",
    "SIGNAL_STRUCTURE_FILTER_SWEEP_HEADER",
    "SIGNAL_STRUCTURE_FILTER_WALK_FORWARD_HEADER",
    "SIGNAL_TARGET_R_SWEEP_HEADER",
    "SIGNAL_TARGET_R_WALK_FORWARD_SWEEP_HEADER",
    "TRADE_OUTCOME_CSV_HEADER",
    "TRADE_OUTCOME_DAILY_CSV_HEADER",
    "TRADE_PATH_DIAGNOSTIC_CSV_HEADER",
    "VAP_ABSORPTION_DIAGNOSTIC_HEADER",
    "VAP_ABSORPTION_THRESHOLD_SWEEP_HEADER",
    "VAP_TRAP_FILTER_SWEEP_HEADER",
    "AbsorptionExperimentError",
    "AcceptanceFinding",
    "AcceptanceGateError",
    "AuctionRegimeStackAcceptanceError",
    "AuctionRegimeStackAcceptanceFinding",
    "AuctionRegimeStackSampleSummary",
    "BaselineError",
    "DeltaImpulseOverlayComparison",
    "DeltaImpulseOverlayValidationError",
    "DeltaImpulseRuleConfig",
    "LiquiditySweepAbsorptionError",
    "NewsExclusionError",
    "PriceOnlyExperimentError",
    "RejectionReasonCatalogError",
    "ScaledContextDiagnosticError",
    "ScaledContextFilterExperimentError",
    "ScaledScalpAcceptanceError",
    "ScaledScalpAcceptanceFinding",
    "ScaledScalpAcceptanceSummary",
    "SessionClockAlignmentError",
    "SignalAuctionRegimeBreakevenReportError",
    "SignalAuctionRegimeDiagnosticError",
    "SignalAuctionRegimeFilterExperimentError",
    "SignalAuctionRegimeGuardReportError",
    "SignalAuctionRegimeHealthGateReportError",
    "SignalAuctionRegimeTargetReportError",
    "SignalAuctionRegimeTradeAuditError",
    "SignalContextDiagnosticError",
    "SignalContextFilterExperimentError",
    "SignalDynamicExitExperimentError",
    "SignalHealthGateExperimentError",
    "SignalLogError",
    "SignalQualityDiagnosticError",
    "SignalQualityFilterExperimentError",
    "SignalQualityHealthGateExperimentError",
    "SignalScaledScalpExperimentError",
    "SignalStructureFilterExperimentError",
    "SignalTargetExperimentError",
    "TradeOutcomeError",
    "VolumeAtPriceAbsorptionError",
    "annotate_rows_with_news_blackouts",
    "auction_regime_stack_acceptance_passed",
    "audit_signal_auction_regime_trades",
    "compare_delta_impulse_overlay_log",
    "diagnose_trade_paths",
    "evaluate_auction_regime_stack_acceptance",
    "evaluate_liquidity_sweep_absorption_reversal",
    "evaluate_price_only_acceptance",
    "evaluate_price_only_liquidity_sweep_reversal",
    "evaluate_price_only_vwap_reclaim",
    "evaluate_scaled_scalp_acceptance",
    "evaluate_signal_breakeven_stop_outcomes",
    "evaluate_signal_health_gate",
    "evaluate_signal_scaled_scalp_outcomes",
    "evaluate_trade_outcomes",
    "filter_news_blackout_rows",
    "generate_delta_impulse_overlay_candidates",
    "load_auction_regime_stack_acceptance_config",
    "load_liquidity_sweep_absorption_config",
    "load_price_only_acceptance_config",
    "load_price_only_bar_rows_csv",
    "load_price_only_baseline_config",
    "load_price_only_liquidity_sweep_config",
    "load_rejection_reason_catalog",
    "load_scaled_scalp_acceptance_config",
    "load_signal_log_rows_csv",
    "load_signal_log_schema",
    "load_signal_rows_csv",
    "price_only_acceptance_passed",
    "rejection_reason_codes",
    "rejection_reason_logging_fields",
    "render_auction_regime_stack_acceptance_report",
    "render_delta_impulse_overlay_validation_report",
    "render_price_only_acceptance_report",
    "render_scaled_scalp_acceptance_report",
    "report_signal_auction_regime_breakeven",
    "report_signal_auction_regime_guard",
    "report_signal_auction_regime_health_gate",
    "report_signal_auction_regime_target_r",
    "run_absorption_reward_risk_sweep",
    "run_absorption_reward_risk_train_holdout_sweep",
    "run_absorption_reward_risk_walk_forward_sweep",
    "run_price_only_parameter_sweep",
    "run_price_only_train_holdout_sweep",
    "run_price_only_walk_forward_sweep",
    "run_scaled_context_filter_sweep",
    "run_scaled_context_filter_walk_forward_sweep",
    "run_scaled_outcome_context_diagnostics",
    "run_session_clock_alignment_diagnostics",
    "run_signal_auction_regime_diagnostics",
    "run_signal_auction_regime_filter_sweep",
    "run_signal_auction_regime_filter_train_holdout_sweep",
    "run_signal_auction_regime_filter_walk_forward_sweep",
    "run_signal_breakeven_stop_sweep",
    "run_signal_breakeven_stop_walk_forward_sweep",
    "run_signal_context_diagnostics",
    "run_signal_context_filter_sweep",
    "run_signal_context_filter_walk_forward_sweep",
    "run_signal_health_gate_sweep",
    "run_signal_health_gate_walk_forward_sweep",
    "run_signal_quality_diagnostics",
    "run_signal_quality_filter_sweep",
    "run_signal_quality_filter_walk_forward_sweep",
    "run_signal_quality_health_gate_walk_forward_sweep",
    "run_signal_scaled_scalp_sweep",
    "run_signal_scaled_scalp_walk_forward_sweep",
    "run_signal_structure_filter_sweep",
    "run_signal_structure_filter_walk_forward_sweep",
    "run_signal_target_r_sweep",
    "run_signal_target_r_walk_forward_sweep",
    "run_vap_absorption_diagnostics",
    "run_vap_absorption_threshold_sweep",
    "run_vap_absorption_threshold_train_holdout_sweep",
    "run_vap_absorption_threshold_walk_forward_sweep",
    "run_vap_trap_filter_sweep",
    "run_vap_trap_filter_train_holdout_sweep",
    "run_vap_trap_filter_walk_forward_sweep",
    "scaled_scalp_acceptance_passed",
    "summarize_auction_regime_stack_sample",
    "summarize_scaled_scalp_acceptance_sample",
    "summarize_trade_outcomes",
    "summarize_trade_outcomes_by_day",
    "summarize_vap_absorption_diagnostics",
    "validate_auction_regime_stack_acceptance_config",
    "validate_liquidity_sweep_absorption_config",
    "validate_price_only_acceptance_config",
    "validate_price_only_baseline_config",
    "validate_price_only_liquidity_sweep_config",
    "validate_rejection_reason_catalog",
    "validate_scaled_scalp_acceptance_config",
    "validate_signal_entries_against_bars",
    "validate_signal_log_row",
    "validate_signal_log_rows",
    "validate_signal_log_schema",
    "write_auction_regime_stack_acceptance_report",
    "write_delta_impulse_overlay_validation_report",
    "write_price_only_acceptance_report",
    "write_scaled_scalp_acceptance_report",
]
