# Price-Only Outcome Report

This report evaluates the current price-only baseline outcomes.
It is research-only and does not imply a tradable strategy.

## Sources

- Signals: `data/processed/AxonTrade_ES_liquidity_sweep_signals.csv`
- Outcomes: `data/processed/AxonTrade_ES_liquidity_sweep_outcomes.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total signal rows | 3030 |
| Candidate signals | 11 |
| Rejected signals | 3019 |
| Evaluated trades | 11 |
| Target hits | 2 |
| Stop/ambiguous losses | 9 |
| Other exits | 0 |
| Win rate | 18.18% |
| Gross USD | -743.75 |
| Net USD | -1057.25 |
| Average net USD | -96.11 |

## Strategy IDs

| Strategy ID | Count |
| --- | ---: |
| price_only_opening_range_liquidity_sweep_reversal | 3030 |

## Exit Reasons

| Exit reason | Count |
| --- | ---: |
| stop_hit | 9 |
| target_hit | 2 |

## Candidate Direction

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| long | 6 | -1058.50 |
| short | 5 | 1.25 |

## Rejected Signal Reasons

| Rejection reason | Count |
| --- | ---: |
| duplicate_signal | 48 |
| insufficient_context | 240 |
| no_setup | 2078 |
| outside_session | 653 |

## Interpretation

This sample was negative after configured costs. Treat the baseline as a control, not a tradable strategy.

## Model Notes

- Entry price is the signal price.
- Stop and target are evaluated only on later same-day bars.
- If stop and target are touched in the same later bar, stop is counted first.
- Costs use the configured commission and slippage assumptions.
