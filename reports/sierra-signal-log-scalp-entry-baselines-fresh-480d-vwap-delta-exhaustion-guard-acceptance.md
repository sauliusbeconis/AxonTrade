# Scaled Context Guard Acceptance Report

This report checks whether a fixed VWAP/delta context guard has enough
evidence to become a Sierra implementation candidate. It is research-only
and does not place, modify, cancel, or route orders.

## Decision

| Metric | Value |
| --- | --- |
| Overall status | FAIL |
| Gate profile | scaled_context_guard_acceptance_gates_v1 |
| Candidate guard | lookback_fade_push_session_range_30_risk_avg_2.5 |

## Sources

- config: `config/research/scaled_context_guard_acceptance_gates.yaml`
- fixed_guards: `reports/sierra-signal-log-scalp-entry-baselines-fresh-480d-vwap-delta-exhaustion-loss-attribution-fixed-guards.csv`
- robustness: `reports/sierra-signal-log-scalp-entry-baselines-fresh-480d-vwap-delta-exhaustion-guard-robustness.csv`

## Gates

| Status | Gate | Observed | Required | Notes |
| --- | --- | ---: | ---: | --- |
| PASS | minimum_fixed_guard_trades | 780 | >= 500 | Trades kept by the fixed guard over the full context sample. |
| PASS | minimum_fixed_guard_net_usd | 52052.50 | >= 50000.00 | Full-sample net USD for the fixed guard. |
| FAIL | minimum_fixed_guard_average_net_usd | 66.73 | >= 75.00 | Average net per kept trade for the fixed guard. |
| FAIL | minimum_fixed_guard_profit_factor | 1.2014 | >= 1.25 | Profit factor for fixed-guard kept trades. |
| FAIL | maximum_fixed_guard_drawdown_to_net_ratio | 0.3607 | <= 0.25 | Peak-to-trough drawdown relative to fixed-guard final net. |
| PASS | maximum_fixed_guard_worst_day_loss_usd | 5160.00 | <= 6500.00 | Largest fixed-guard losing day by absolute USD loss. |
| PASS | minimum_robustness_rows | 5 | >= 5 | Distinct chronological robustness window shapes evaluated. |
| PASS | all_robustness_guarded_net_positive | True | True | Every robustness window shape must have positive guarded net. |
| PASS | all_robustness_improved_vs_unguarded | True | True | Every robustness window shape must improve over unguarded rows. |
| PASS | minimum_worst_robustness_guarded_net_usd | 44320.50 | >= 10000.00 | Weakest guarded net across robustness window shapes. |
| PASS | minimum_worst_robustness_average_net_usd | 69.93 | >= 40.00 | Weakest guarded average net/trade across robustness shapes. |
| FAIL | maximum_robustness_negative_window_rate | 0.3571 | <= 0.35 | Highest negative holdout-window rate across robustness shapes. |
| FAIL | maximum_worst_guarded_window_loss_usd | 7446.00 | <= 7000.00 | Largest guarded losing holdout window by absolute USD loss. |

## Sample Coverage

| Metric | Value |
| --- | ---: |
| Fixed input trades | 1639 |
| Fixed kept trades | 780 |
| Fixed skipped trades | 859 |
| Fixed net USD | 52052.50 |
| Fixed average net USD | 66.73 |
| Fixed profit factor | 1.2014 |
| Fixed max drawdown USD | -18776.00 |
| Fixed drawdown to net ratio | 0.3607 |
| Fixed worst day | 2026-03-09 |
| Fixed worst day net USD | -5160.00 |
| Robustness rows | 5 |
| Worst robustness guarded net USD | 44320.50 |
| Worst robustness average net USD | 69.93 |
| Maximum robustness negative-window rate | 0.3571 |
| Worst guarded window loss USD | 7446.00 |
| Additional fixed guard trades required | 0 |
| Additional robustness rows required | 0 |

## Interpretation

At least one configured gate failed. Do not promote this guard into Sierra automation. Failed gates: minimum_fixed_guard_average_net_usd, minimum_fixed_guard_profit_factor, maximum_fixed_guard_drawdown_to_net_ratio, maximum_robustness_negative_window_rate, maximum_worst_guarded_window_loss_usd.
