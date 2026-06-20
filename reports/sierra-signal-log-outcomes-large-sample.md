# Sierra Signal Log Outcome Report - Large Sample

This report evaluates the larger Sierra overlay candidate sample against a matching Sierra bar export.
It is research-only and does not imply a tradable strategy.

## Sources

- Signals: `data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv`
- Outcomes: `data/processed/AxonTrade_ES_overlay_signal_outcomes_large_sample.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total signal rows | 43048 |
| Candidate signals | 23 |
| Rejected signals | 43025 |
| Evaluated trades | 23 |
| Target hits | 7 |
| Stop/ambiguous losses | 16 |
| Other exits | 0 |
| Win rate | 30.43% |
| Gross USD | -225.00 |
| Net USD | -880.50 |
| Average net USD | -38.28 |

## Strategy IDs

| Strategy ID | Count |
| --- | ---: |
| liquidity_sweep_absorption_reversal | 43048 |

## Exit Reasons

| Exit reason | Count |
| --- | ---: |
| stop_hit | 16 |
| target_hit | 7 |

## Candidate Direction

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| long | 12 | -198.25 |
| short | 11 | -682.25 |

## Rejected Signal Reasons

| Rejection reason | Count |
| --- | ---: |
| duplicate_signal | 151 |
| insufficient_context | 5232 |
| no_absorption | 11532 |
| no_setup | 15845 |
| outside_session | 10264 |
| risk_limit | 1 |

## Interpretation

This sample was negative after configured costs. Treat the baseline as a control, not a tradable strategy.

## Model Notes

- Entry price is the signal price.
- Stop and target are evaluated only on later same-day bars.
- If stop and target are touched in the same later bar, stop is counted first.
- Costs use the configured commission and slippage assumptions.
