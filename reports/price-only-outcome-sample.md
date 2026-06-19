# Price-Only Outcome Report

This report evaluates the current price-only VWAP/opening-range baseline.
It is research-only and does not imply a tradable strategy.

## Sources

- Signals: `data/processed/AxonTrade_ES_price_only_signals.csv`
- Outcomes: `data/processed/AxonTrade_ES_price_only_outcomes.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total signal rows | 3030 |
| Candidate signals | 47 |
| Rejected signals | 2983 |
| Evaluated trades | 47 |
| Target hits | 8 |
| Stop/ambiguous losses | 30 |
| Other exits | 9 |
| Win rate | 17.02% |
| Gross USD | -16812.50 |
| Net USD | -18152.00 |
| Average net USD | -386.21 |

## Exit Reasons

| Exit reason | Count |
| --- | ---: |
| end_of_session | 9 |
| stop_hit | 30 |
| target_hit | 8 |

## Candidate Direction

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| long | 11 | 211.50 |
| short | 36 | -18363.50 |

## Rejected Signal Reasons

| Rejection reason | Count |
| --- | ---: |
| insufficient_context | 240 |
| no_setup | 2743 |

## Interpretation

This sample was negative after configured costs. Treat the baseline as a control, not a tradable strategy.

## Model Notes

- Entry price is the signal price.
- Stop and target are evaluated only on later same-day bars.
- If stop and target are touched in the same later bar, stop is counted first.
- Costs use the configured commission and slippage assumptions.
