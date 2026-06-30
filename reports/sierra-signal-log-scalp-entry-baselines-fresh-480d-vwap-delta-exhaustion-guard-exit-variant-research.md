# Fresh 480D VWAP Delta Guard/Exit Variant Research

Status: **research candidate preserved, implementation rejected**

## Scope

This pass used the fresh historical export produced on `2026-06-30`, but the
file contains bars only from `2025-09-15 09:30:00` through
`2026-06-29 16:12:00`. This is not a current-session or live validation sample.

Fixed entry lead:

`vwap_delta_exhaustion_fade_2pt_10d_cl0.5`

Evaluation shape:

- holdout dates from the same `20` train date, `5` holdout date, `5` date step
  construction used by the fresh 480D fixed-row audit;
- `1.0` total slippage tick per contract;
- exit grid: first target `3,4,5,6`, stop `6,8,10,12`, runner target
  `8,10,12,15,20`, runner stop mode `initial,breakeven`;
- guard grid: the accepted theory guard plus stricter time, tape activity,
  session range, and compression variants.

Generated output:

- `reports/sierra-signal-log-scalp-entry-baselines-fresh-480d-vwap-delta-exhaustion-guard-exit-variant-sweep.csv`

## Result

No tested row passed all `12` promotion gates.

| Result | Rows |
| --- | ---: |
| Tested exit/guard rows | `800` |
| Full promotion passes | `0` |
| Rows passing `11` of `12` gates | `8` |
| Rows passing `10` of `12` gates | `21` |

Best structural row:

| Metric | Value |
| --- | ---: |
| Exit | `6 / 12 / 15 / initial` |
| Guard | `lookback_directional_move_points <= -2.5; session_range_points >= 30; risk_to_average_bar_range <= 1.75` |
| Kept trades | `414` |
| Net USD | `60277.00` |
| Average/trade | `145.60` |
| Profit factor | `1.3807` |
| Max drawdown USD | `-8794.00` |
| Drawdown/net | `0.1459` |
| Worst day | `2025-10-14`, `-4928.00` |
| Failed gate | `minimum_fixed_guard_trades` |

Robustness for the best structural row:

| Train | Holdout | Step | Kept Trades | Guarded Net | Avg/Trade | Negative Window Rate | Worst Window | Unguarded Same Windows |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `20` | `5` | `5` | `368` | `58899.00` | `160.05` | `0.250` | `-5290.00` | `36493.00` |
| `40` | `5` | `5` | `307` | `54851.00` | `178.67` | `0.214` | `-5290.00` | `34856.50` |
| `40` | `10` | `10` | `307` | `54851.00` | `178.67` | `0.214` | `-4272.00` | `34856.50` |
| `60` | `10` | `10` | `285` | `50455.00` | `177.04` | `0.167` | `-4272.00` | `32447.50` |
| `80` | `10` | `10` | `256` | `49283.00` | `192.51` | `0.100` | `-1262.00` | `20584.50` |

Best row that keeps at least `500` trades:

| Metric | Value |
| --- | ---: |
| Exit | `6 / 10 / 12 / initial` |
| Guard | `lookback_directional_move_points <= -2.5; session_range_points >= 30; risk_to_average_bar_range <= 1.75` |
| Kept trades | `550` |
| Net USD | `55112.50` |
| Average/trade | `100.20` |
| Profit factor | `1.2786` |
| Max drawdown USD | `-17420.00` |
| Drawdown/net | `0.3161` |
| Worst day | `2025-10-14`, `-5324.00` |
| Failed gate | `maximum_fixed_guard_drawdown_to_net_ratio` |

## Interpretation

The 480D tests did not destroy the VWAP/delta exhaustion idea. They rejected the
current implementation candidate because the fixed `5 / 10 / 10 / initial`
exit with the looser `risk_to_average_bar_range <= 2.5` guard is too noisy.

The stricter compression guard, `risk_to_average_bar_range <= 1.75`, materially
improves trade quality. The cleanest row is high quality but too selective for
the current minimum-trade gate. The best sample-size-compliant row still fails
drawdown discipline, so it needs a separate daily or sequence-risk veto before
it can be reconsidered.

Do not wire this into Sierra automation yet. The next research step is not a
broader random parameter search. It is a focused drawdown-control pass over the
`6 / 10 / 12 / initial` and `6 / 12 / 15 / initial` candidates.
