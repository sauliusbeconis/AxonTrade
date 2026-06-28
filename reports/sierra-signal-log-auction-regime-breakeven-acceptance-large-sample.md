# Auction-Regime Stack Acceptance Report

This report checks whether selected auction-regime stack audit rows pass
minimum evidence gates. It is research-only and does not place, modify,
cancel, or route orders.

## Decision

| Metric | Value |
| --- | --- |
| Overall status | FAIL |
| Gate profile | auction_regime_stack_acceptance_gates_v1 |

## Sources

- audit: `reports/sierra-signal-log-auction-regime-breakeven-trade-audit-large-sample.csv`
- config: `config/research/auction_regime_stack_acceptance_gates.yaml`

## Gates

| Status | Gate | Observed | Required | Notes |
| --- | --- | ---: | ---: | --- |
| FAIL | minimum_unique_holdout_evaluated_signals | 1 | >= 30 | Unique evaluated holdout signal IDs after selected auction and exit policies. |
| FAIL | minimum_unique_holdout_trade_dates | 1 | >= 15 | Distinct trade dates represented by unique evaluated holdout signals. |
| FAIL | maximum_duplicate_holdout_evaluated_rows | 2 | <= 0 | Evaluated holdout rows whose signal ID appears more than once in the sample. |
| PASS | positive_unique_holdout_net | 171.50 | > 0.00 | Net USD after de-duplicating evaluated holdout signals by first occurrence. |
| FAIL | maximum_single_signal_net_share | 100.00% | <= 25.00% | Largest unique winning signal as a share of total positive unique holdout net. |

## Sample Coverage

| Metric | Value |
| --- | ---: |
| Holdout evaluated rows | 2 |
| Unique evaluated holdout signals | 1 |
| Unique holdout trade dates | 1 |
| Duplicate evaluated holdout rows | 2 |
| Unique holdout net USD | 171.50 |
| Positive unique holdout net USD | 171.50 |
| Largest signal net USD | 171.50 |
| Largest signal share | 100.00% |
| Additional unique signals required | 29 |
| Additional trade dates required | 14 |
| Duplicate rows to remove | 2 |

## Interpretation

One or more evidence gates failed: minimum_unique_holdout_evaluated_signals, minimum_unique_holdout_trade_dates, maximum_duplicate_holdout_evaluated_rows, maximum_single_signal_net_share. Do not treat the selected auction-regime stack as automation-ready.
