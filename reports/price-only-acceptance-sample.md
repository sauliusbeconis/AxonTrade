# Price-Only Acceptance Report

This report checks whether the current price-only research outputs pass the
configured evidence gates. It is research-only and does not place, modify,
cancel, or route orders.

## Decision

| Metric | Value |
| --- | --- |
| Overall status | FAIL |
| Gate profile | price_only_acceptance_gates_v1 |

## Sources

- config: `config/research/price_only_acceptance_gates.yaml`
- daily: `reports/price-only-daily-outcome-sample.csv`
- outcomes: `data/processed/AxonTrade_ES_price_only_outcomes.csv`
- train_holdout: `reports/price-only-train-holdout-sweep-sample.csv`
- walk_forward: `reports/price-only-walk-forward-sweep-sample.csv`

## Gates

| Status | Gate | Observed | Required | Notes |
| --- | --- | ---: | ---: | --- |
| FAIL | minimum_total_outcome_trades | 47 | >= 100 | Total evaluated outcome trades in the baseline sample. |
| FAIL | minimum_trade_days | 7 | >= 20 | Distinct trade dates in the daily outcome summary. |
| FAIL | minimum_walk_forward_holdout_trades | 10 | >= 30 | Trades from selected rolling holdout windows only. |
| FAIL | positive_walk_forward_holdout_net | -847.50 | > 0.00 | Net USD from selected rolling holdout windows after configured costs. |
| FAIL | minimum_selected_train_holdout_trades | 0 | >= 10 | Trades for the single train-selected holdout parameter set. |
| FAIL | maximum_worst_day_loss_share | 43.20% | <= 40.00% | Worst losing day 2026-06-11 was -8881.00. |

## Interpretation

The current price-only baseline is rejected by the configured research gates. Failed gates: minimum_total_outcome_trades, minimum_trade_days, minimum_walk_forward_holdout_trades, positive_walk_forward_holdout_net, minimum_selected_train_holdout_trades, maximum_worst_day_loss_share.
