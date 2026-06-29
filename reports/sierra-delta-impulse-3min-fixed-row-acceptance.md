# Fixed Scaled-Scalp Acceptance Report

This report checks whether a fixed two-contract scaled-scalp row passes
minimum evidence gates. It is research-only and does not place, modify,
cancel, or route orders.

## Decision

| Metric | Value |
| --- | --- |
| Overall status | FAIL |
| Gate profile | scaled_scalp_fixed_row_acceptance_gates_v1 |

## Sources

- config: `config/research/scaled_scalp_fixed_row_acceptance_gates.yaml`
- holiday_calendar: `config/research/cme_equity_index_holidays_2026.csv`
- outcomes: `data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv`
- sweep: `reports/sierra-delta-impulse-3min-large-scaled-exit-sweep.csv`

## Gates

| Status | Gate | Observed | Required | Notes |
| --- | --- | ---: | ---: | --- |
| FAIL | minimum_outcome_trades | 78 | >= 100 | Total evaluated fixed-row outcome trades. |
| FAIL | minimum_trade_dates | 13 | >= 20 | Distinct trade dates represented by fixed-row outcomes. |
| PASS | positive_holiday_adjusted_net | 4896.00 | > 0.00 | Net USD after excluding supplied holiday/early-close dates. |
| PASS | positive_holiday_adjusted_fixed_rolling_holdout_net | 5664.00 | > 0.00 | Fixed-row rolling holdout net after excluding holidays. |
| FAIL | maximum_drawdown_to_net_ratio | 91.37% | <= 50.00% | Peak-to-trough drawdown relative to final net; high values imply unstable equity. |
| FAIL | maximum_last_n_positive_day_net_share | 56.90% | <= 40.00% | Share of all positive daily net contributed by the final configured dates. |
| FAIL | minimum_positive_nearby_parameter_rows | 3 | >= 4 | Positive nearby all-direction initial-stop parameter rows around the fixed row. |
| FAIL | nonnegative_holiday_adjusted_short_net | -1895.00 | >= 0.00 | Short-side net after excluding supplied holiday/early-close dates. |
| PASS | maximum_nonholiday_terminal_exits | 0 | <= 0 | End/no-following exits on nonholiday dates. |

## Sample Coverage

| Metric | Value |
| --- | ---: |
| Outcome trades | 78 |
| Trade dates | 13 |
| Holiday dates | 1 |
| Holiday-adjusted trades | 72 |
| Holiday-adjusted net USD | 4896.00 |
| Holiday-adjusted short net USD | -1895.00 |
| Holiday-adjusted fixed rolling holdout net USD | 5664.00 |
| Maximum drawdown USD | -2836.00 |
| Drawdown to net ratio | 91.37% |
| Last 3 positive day net share | 56.90% |
| Positive nearby parameter rows | 3 |
| Nonholiday terminal exits | 0 |
| Additional trades required | 22 |
| Additional trade dates required | 7 |

## Interpretation

At least one configured gate failed. Do not promote this fixed row to live routing. Failed gates: minimum_outcome_trades, minimum_trade_dates, maximum_drawdown_to_net_ratio, maximum_last_n_positive_day_net_share, minimum_positive_nearby_parameter_rows, nonnegative_holiday_adjusted_short_net.
