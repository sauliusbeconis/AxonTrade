# Price-Only Outcome Report

This report evaluates the current price-only baseline outcomes.
It is research-only and does not imply a tradable strategy.

## Sources

- Signals: `data/processed/AxonTrade_ES_absorption_signals.csv`
- Outcomes: `data/processed/AxonTrade_ES_absorption_outcomes.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total signal rows | 5314 |
| Candidate signals | 5 |
| Rejected signals | 5309 |
| Evaluated trades | 5 |
| Target hits | 3 |
| Stop/ambiguous losses | 2 |
| Other exits | 0 |
| Win rate | 60.00% |
| Gross USD | 456.25 |
| Net USD | 313.75 |
| Average net USD | 62.75 |

## Strategy IDs

| Strategy ID | Count |
| --- | ---: |
| liquidity_sweep_absorption_reversal | 5314 |

## Exit Reasons

| Exit reason | Count |
| --- | ---: |
| stop_hit | 2 |
| target_hit | 3 |

## Candidate Direction

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| long | 2 | -244.50 |
| short | 3 | 558.25 |

## Rejected Signal Reasons

| Rejection reason | Count |
| --- | ---: |
| duplicate_signal | 2395 |
| insufficient_context | 102 |
| no_absorption | 24 |
| no_setup | 1836 |
| outside_session | 952 |

## Interpretation

This sample was positive after configured costs. Treat it as research evidence only.

## Model Notes

- Entry price is the signal price.
- Stop and target are evaluated only on later same-day bars.
- If stop and target are touched in the same later bar, stop is counted first.
- Costs use the configured commission and slippage assumptions.
