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
| PASS | minimum_outcome_trades | 163 | >= 100 | Total evaluated fixed-row outcome trades. |
| PASS | minimum_trade_dates | 41 | >= 20 | Distinct trade dates represented by fixed-row outcomes. |
| FAIL | positive_holiday_adjusted_net | -13924.00 | > 0.00 | Net USD after excluding supplied holiday/early-close dates. |
| FAIL | positive_holiday_adjusted_fixed_rolling_holdout_net | -13718.00 | > 0.00 | Fixed-row rolling holdout net after excluding holidays. |
| FAIL | maximum_drawdown_to_net_ratio | 100.00% | <= 50.00% | Peak-to-trough drawdown relative to final net; high values imply unstable equity. |
| PASS | maximum_last_n_positive_day_net_share | 23.37% | <= 40.00% | Share of all positive daily net contributed by the final configured dates. |
| FAIL | minimum_positive_nearby_parameter_rows | 0 | >= 4 | Positive nearby all-direction initial-stop parameter rows around the fixed row. |
| FAIL | nonnegative_holiday_adjusted_short_net | -8562.00 | >= 0.00 | Short-side net after excluding supplied holiday/early-close dates. |
| FAIL | maximum_nonholiday_terminal_exits | 1 | <= 0 | End/no-following exits on nonholiday dates. |

## Sample Coverage

| Metric | Value |
| --- | ---: |
| Outcome trades | 163 |
| Trade dates | 41 |
| Holiday dates | 1 |
| Holiday-adjusted trades | 157 |
| Holiday-adjusted net USD | -13924.00 |
| Holiday-adjusted short net USD | -8562.00 |
| Holiday-adjusted fixed rolling holdout net USD | -13718.00 |
| Maximum drawdown USD | -21398.00 |
| Drawdown to net ratio | 100.00% |
| Last 3 positive day net share | 23.37% |
| Positive nearby parameter rows | 0 |
| Nonholiday terminal exits | 1 |
| Additional trades required | 0 |
| Additional trade dates required | 0 |

## Interpretation

At least one configured gate failed. Do not promote this fixed row to live routing. Failed gates: positive_holiday_adjusted_net, positive_holiday_adjusted_fixed_rolling_holdout_net, maximum_drawdown_to_net_ratio, minimum_positive_nearby_parameter_rows, nonnegative_holiday_adjusted_short_net, maximum_nonholiday_terminal_exits.
