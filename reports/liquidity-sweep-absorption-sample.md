# Price-Only Outcome Report

This report evaluates the current price-only baseline outcomes.
It is research-only and does not imply a tradable strategy.

## Sources

- Signals: `data/processed/AxonTrade_ES_absorption_signals.csv`
- Outcomes: `data/processed/AxonTrade_ES_absorption_outcomes.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total signal rows | 28158 |
| Candidate signals | 30 |
| Rejected signals | 28128 |
| Evaluated trades | 30 |
| Target hits | 15 |
| Stop/ambiguous losses | 15 |
| Other exits | 0 |
| Win rate | 50.00% |
| Gross USD | -168.75 |
| Net USD | -1023.75 |
| Average net USD | -34.12 |

## Strategy IDs

| Strategy ID | Count |
| --- | ---: |
| liquidity_sweep_absorption_reversal | 28158 |

## Exit Reasons

| Exit reason | Count |
| --- | ---: |
| stop_hit | 15 |
| target_hit | 15 |

## Candidate Direction

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| long | 15 | -465.00 |
| short | 15 | -558.75 |

## Rejected Signal Reasons

| Rejection reason | Count |
| --- | ---: |
| duplicate_signal | 16067 |
| insufficient_context | 475 |
| no_absorption | 111 |
| no_setup | 4924 |
| outside_session | 6531 |
| risk_limit | 20 |

## Interpretation

This sample was negative after configured costs. Treat the baseline as a control, not a tradable strategy.

## Model Notes

- Entry price is the signal price.
- Stop and target are evaluated only on later same-day bars.
- If stop and target are touched in the same later bar, stop is counted first.
- Costs use the configured commission and slippage assumptions.
