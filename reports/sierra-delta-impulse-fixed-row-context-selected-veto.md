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

## Interpretation

This is the first positive chronological holdout result in the Delta Impulse
path after the expanded export. The improvement is structurally meaningful
because the second stage is selected on train rows only and then applied to
holdout rows.

Do not treat it as deployable yet. It is still only `53` kept holdout trades,
selected through two stages, and several windows have zero or one kept holdout
trade. The finding is strong enough to justify another export and a larger
out-of-sample check, not strong enough for live routing.

Current status:

- raw Delta Impulse continuation: rejected;
- first-stage normalized context filter: active research direction;
- second-stage selected veto: promising diagnostic, needs larger-sample
  validation.
