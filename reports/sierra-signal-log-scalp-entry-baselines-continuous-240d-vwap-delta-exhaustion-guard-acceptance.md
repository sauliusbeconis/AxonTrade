# Scaled Context Guard Acceptance Report

This report checks whether a fixed VWAP/delta context guard has enough
evidence to become a Sierra implementation candidate. It is research-only
and does not place, modify, cancel, or route orders.

## Decision

| Metric | Value |
| --- | --- |
| Overall status | PASS |
| Gate profile | scaled_context_guard_acceptance_gates_v1 |
| Candidate guard | lookback_fade_push_session_range_30_risk_avg_2.5 |

## Sources

- config: `config/research/scaled_context_guard_acceptance_gates.yaml`
- fixed_guards: `reports/sierra-signal-log-scalp-entry-baselines-continuous-240d-vwap-delta-exhaustion-loss-attribution-fixed-guards.csv`
- robustness: `reports/sierra-signal-log-scalp-entry-baselines-continuous-240d-vwap-delta-exhaustion-guard-robustness.csv`

## Gates

| Status | Gate | Observed | Required | Notes |
| --- | --- | ---: | ---: | --- |
| PASS | minimum_fixed_guard_trades | 603 | >= 500 | Trades kept by the fixed guard over the full context sample. |
| PASS | minimum_fixed_guard_net_usd | 67241.50 | >= 50000.00 | Full-sample net USD for the fixed guard. |
| PASS | minimum_fixed_guard_average_net_usd | 111.51 | >= 75.00 | Average net per kept trade for the fixed guard. |
| PASS | minimum_fixed_guard_profit_factor | 1.3671 | >= 1.25 | Profit factor for fixed-guard kept trades. |
| PASS | maximum_fixed_guard_drawdown_to_net_ratio | 0.1528 | <= 0.25 | Peak-to-trough drawdown relative to fixed-guard final net. |
| PASS | maximum_fixed_guard_worst_day_loss_usd | 5160.00 | <= 6500.00 | Largest fixed-guard losing day by absolute USD loss. |
| PASS | minimum_robustness_rows | 5 | >= 5 | Distinct chronological robustness window shapes evaluated. |
| PASS | all_robustness_guarded_net_positive | True | True | Every robustness window shape must have positive guarded net. |
| PASS | all_robustness_improved_vs_unguarded | True | True | Every robustness window shape must improve over unguarded rows. |
| PASS | minimum_worst_robustness_guarded_net_usd | 13721.00 | >= 10000.00 | Weakest guarded net across robustness window shapes. |
| PASS | minimum_worst_robustness_average_net_usd | 42.61 | >= 40.00 | Weakest guarded average net/trade across robustness shapes. |
| PASS | maximum_robustness_negative_window_rate | 0.3333 | <= 0.35 | Highest negative holdout-window rate across robustness shapes. |
| PASS | maximum_worst_guarded_window_loss_usd | 6018.00 | <= 7000.00 | Largest guarded losing holdout window by absolute USD loss. |

## Sample Coverage

| Metric | Value |
| --- | ---: |
| Fixed input trades | 1298 |
| Fixed kept trades | 603 |
| Fixed skipped trades | 695 |
| Fixed net USD | 67241.50 |
| Fixed average net USD | 111.51 |
| Fixed profit factor | 1.3671 |
| Fixed max drawdown USD | -10274.00 |
| Fixed drawdown to net ratio | 0.1528 |
| Fixed worst day | 2026-03-09 |
| Fixed worst day net USD | -5160.00 |
| Robustness rows | 5 |
| Worst robustness guarded net USD | 13721.00 |
| Worst robustness average net USD | 42.61 |
| Maximum robustness negative-window rate | 0.3333 |
| Worst guarded window loss USD | 6018.00 |
| Additional fixed guard trades required | 0 |
| Additional robustness rows required | 0 |

## Interpretation

All configured gates passed. The guard is a research implementation candidate, but live routing remains disabled until a future explicit safety phase authorizes it.
