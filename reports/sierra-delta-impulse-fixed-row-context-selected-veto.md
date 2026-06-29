# Sierra Delta Impulse Selected Context Veto

Status: **diagnostic only**

## Sources

- Context diagnostics:
  `reports/sierra-delta-impulse-fixed-row-context-diagnostics.csv`
- First-stage selected context rules:
  `reports/sierra-delta-impulse-fixed-row-context-filter-oldshape-nonoverlap-walk-forward.csv`
- Selected trade audit:
  `reports/sierra-delta-impulse-fixed-row-context-selected-trade-audit.csv`
- Second-stage veto walk-forward:
  `reports/sierra-delta-impulse-fixed-row-context-selected-veto-walk-forward.csv`

## Method

- First stage: old-shape `8` train dates, `2` holdout dates, non-overlapping
  window step.
- First-stage selected holdout baseline: `64` trades, `-1198` net USD.
- Second stage: select one simple veto rule on each split's selected train
  trades, then apply that one rule to the selected holdout trades.
- Minimum kept train trades: `10`.
- Selection objective: best train-side lower-bound average net, then train
  improvement versus unvetoed selected trades.
- Veto features tested:
  directional open distance, directional opening-range breakout, continuation
  edge, opening-range continuation edge, lookback directional move, lookback
  efficiency, signal-delta ratio, entry-volume ratio, session-volume ratio, and
  risk-to-average-range.

## Result

| Stage | Holdout Trades | Holdout Net USD | Avg USD/Trade |
| --- | ---: | ---: | ---: |
| Raw fixed row, all expanded candidates | 163 | -15716 | -96.42 |
| First-stage selected context | 64 | -1198 | -18.72 |
| Second-stage selected veto | 53 | 3979 | 75.08 |

The second-stage veto removed `11` selected holdout trades and improved net by
`5177` USD versus the first-stage selected context baseline.

## Selected Veto Families

| Veto Family | Holdout Windows |
| --- | ---: |
| opening-range continuation edge minimum | 7 |
| signal-delta ratio maximum | 5 |
| no veto | 2 |
| risk-to-average-range maximum | 2 |

## Larger Export Sanity Check

The `2026-06-29` larger export did not materially increase the sample. It added
only `6` validated candidates:

- prior validated overlay candidates: `163`
- larger export validated overlay candidates: `169`
- first-stage selected context on larger export: `72` holdout trades, `-1554`
  net USD
- second-stage selected veto on larger export: `60` kept holdout trades,
  `3930` net USD
- veto improvement versus first-stage selected context: `5484` USD

The selected-veto idea survived this small extension, but this is not a true
large-sample validation. The next meaningful test still requires substantially
more trade dates and candidate signals.

## Continuous 240D Validation

The continuous-contract 240D export is the first materially larger validation
set:

- validated overlay candidates: `1003`
- trade dates in signal log: `168`
- raw fixed row: `1003` trades, `-72508.50` net USD
- first-stage selected context: `364` holdout trades, `-45648` net USD
- unfiltered same-window holdout baseline: `955` trades, `-74122.50` net USD
- second-stage selected veto: `227` kept holdout trades, `-22339` net USD
- veto improvement versus first-stage selected context: `23309` USD

This invalidates the positive small-sample result. The selected-veto stack still
removes a lot of bad exposure, but it does not produce a positive strategy on
the first true large sample.

## Interpretation

The original `53`-trade positive result was too thin. The continuous 240D
validation shows the context/veto stack is a loss-avoidance mechanism, not a
profitable strategy.

Current status:

- raw Delta Impulse continuation: rejected;
- first-stage normalized context filter: rejected as a standalone selector;
- second-stage selected veto: rejected as a standalone selector;
- the remaining useful information is diagnostic: these filters identify bad
  exposure, but they do not define an executable edge.
