# Sierra Signal Log Outcome Report

This report evaluates Sierra overlay candidate rows against a matching Sierra bar export.
It is research-only and does not imply a tradable strategy.

## Sources

- Signals: `data/processed/AxonTrade_ES_overlay_signal_log_replay_sample.csv`
- Outcomes: `data/processed/AxonTrade_ES_overlay_signal_outcomes.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total signal rows | 808 |
| Candidate signals | 2 |
| Rejected signals | 806 |
| Evaluated trades | 2 |
| Target hits | 0 |
| Stop/ambiguous losses | 1 |
| Other exits | 1 |
| Win rate | 0.00% |
| Gross USD | -125.00 |
| Net USD | -182.00 |
| Average net USD | -91.00 |

## Strategy IDs

| Strategy ID | Count |
| --- | ---: |
| liquidity_sweep_absorption_reversal | 808 |

## Exit Reasons

| Exit reason | Count |
| --- | ---: |
| end_of_session | 1 |
| stop_hit | 1 |

## Candidate Direction

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| long | 2 | -182.00 |

## Rejected Signal Reasons

| Rejection reason | Count |
| --- | ---: |
| duplicate_signal | 3 |
| insufficient_context | 241 |
| no_absorption | 105 |
| no_setup | 220 |
| outside_session | 237 |

## Interpretation

This sample was negative after configured costs. Treat the baseline as a control, not a tradable strategy.

## Model Notes

- Entry price is the signal price.
- Stop and target are evaluated only on later same-day bars.
- If stop and target are touched in the same later bar, stop is counted first.
- Costs use the configured commission and slippage assumptions.
