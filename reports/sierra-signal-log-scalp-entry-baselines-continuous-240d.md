# Sierra Scalp Entry Baselines Continuous 240D

Status: **research lead, not live-ready**

## Source

- Bars export: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Continuous_240D.txt`
- Rows: `22212`
- Trade dates: `168`
- Date range: `2025-11-03` through `2026-06-29`

The export does not include a Sierra VWAP study column. The baseline generator
now preserves exported VWAP when present and otherwise computes an RTH-session
VWAP fallback from cumulative `HLC Avg * Volume` by trade date.

## Broad Sweep

Command shape:

```bash
.venv/bin/python scripts/run_signal_scalp_entry_baselines.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Continuous_240D.txt \
  reports/sierra-signal-log-scalp-entry-baselines-continuous-240d-sweep.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --entry-family-set all \
  --minimum-spacing-seconds 900 \
  --max-rule-entries-per-day 20 \
  --random-per-day 25 \
  --first-target-points 2,3,4,5 \
  --stop-points 4,5,6,8,10 \
  --runner-target-points 5,6,8,10,15,20 \
  --runner-stop-modes breakeven,initial
```

Regular default ES cost model, one tick per side:

| Metric | Value |
| --- | ---: |
| Strategy families | `33` |
| Positive best rows | `0` |
| Best family | `vwap_pullback_continue_8pt_pb2pt` |
| Best net | `-6795.00` |
| Best trades | `185` |

Zero-slippage sensitivity:

| Strategy | Trades | Net USD | Avg/trade | Exit |
| --- | ---: | ---: | ---: | --- |
| `vwap_extension_fade_4pt` | `3229` | `76772.00` | `23.78` | `3 / 10 / 10 / initial` |
| `impulse_fade_5bar_2pt` | `3253` | `70479.00` | `21.67` | `5 / 8 / 6 / initial` |
| `vwap_extension_fade_1pt` | `3306` | `69820.50` | `21.12` | `3 / 10 / 10 / initial` |
| `vwap_extension_fade_2pt` | `3290` | `68670.00` | `20.87` | `3 / 10 / 10 / initial` |
| `vwap_delta_exhaustion_fade_2pt_10d_cl0.5` | `1513` | `59234.00` | `39.15` | `5 / 10 / 10 / initial` |

Cost-threshold sensitivity on the top families:

| Slippage Model | Best Strategy | Trades | Net USD | Avg/trade | Exit |
| --- | --- | ---: | ---: | ---: | --- |
| `0.5` tick total/contract | `vwap_delta_exhaustion_fade_2pt_10d_cl0.5` | `1513` | `40321.50` | `26.65` | `5 / 10 / 10 / initial` |
| `1.0` tick total/contract | `vwap_delta_exhaustion_fade_2pt_10d_cl0.5` | `1513` | `21409.00` | `14.15` | `5 / 10 / 10 / initial` |
| default one tick/side | `vwap_pullback_continue_8pt_pb2pt` | `185` | `-6795.00` | `-36.73` | `2 / 10 / 20 / initial` |

## Walk-Forward

Top-family adaptive-exit walk-forward:

| Slippage Model | Best Strategy | Holdout Trades | Holdout Net USD | Avg/trade |
| --- | --- | ---: | ---: | ---: |
| `0.5` tick total/contract | `vwap_extension_fade_4pt` | `2798` | `18001.50` | `6.43` |
| `1.0` tick total/contract | `vwap_extension_fade_4pt` | `2798` | `-16973.50` | `-6.07` |

The adaptive selector is unstable. The aggregate `vwap_delta_exhaustion`
parameter row was then retested as a fixed rule with no exit optimization:

```bash
.venv/bin/python scripts/run_signal_scalp_entry_baselines.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Continuous_240D.txt \
  reports/sierra-signal-log-scalp-entry-baselines-continuous-240d-fixed-vwap-delta-exhaustion-slip1-walk-forward.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --entry-family-set all \
  --minimum-spacing-seconds 900 \
  --max-rule-entries-per-day 20 \
  --strategy-ids vwap_delta_exhaustion_fade_2pt_10d_cl0.5 \
  --first-target-points 5 \
  --stop-points 10 \
  --runner-target-points 10 \
  --runner-stop-modes initial \
  --output-mode walk_forward \
  --train-date-count 20 \
  --holdout-date-count 5 \
  --window-step-date-count 5 \
  --minimum-train-trades 20 \
  --slippage-ticks-per-contract 1
```

Fixed `vwap_delta_exhaustion_fade_2pt_10d_cl0.5`, `5 / 10 / 10 / initial`,
`1.0` tick total slippage per contract:

| Metric | Value |
| --- | ---: |
| Holdout windows | `29` |
| Positive windows | `14` |
| Negative windows | `15` |
| Holdout trades | `1298` |
| Net USD | `27101.50` |
| Average/trade | `20.88` |
| Win rate | `54.62%` |
| Profit factor | `1.061` |
| Max trade-sequence drawdown | `-23636.00` |
| Max daily-equity drawdown | `-23279.00` |
| Worst day | `2026-04-13`, `-12012.00` |

Monthly holdout net:

| Month | Net USD | Trades |
| --- | ---: | ---: |
| `2025-12` | `-7351.00` | `193` |
| `2026-01` | `6551.00` | `182` |
| `2026-02` | `10734.00` | `163` |
| `2026-03` | `3563.00` | `191` |
| `2026-04` | `2336.00` | `202` |
| `2026-05` | `219.50` | `199` |
| `2026-06` | `11049.00` | `168` |

Control fixed row:

| Strategy | Exit | Holdout Trades | Holdout Net USD |
| --- | --- | ---: | ---: |
| `opening_range_sweep_fade_30m_0.5pt` | `5 / 5 / 20 / initial` | `489` | `-3835.50` |

## Interpretation

The first useful 240D scalp lead is **VWAP + delta exhaustion fade**, not the
Delta Impulse continuation overlay. It is not a pure micro-scalp: entries are
spaced by `900` seconds and the fixed exit uses a `5` point first target, `10`
point stop, and `10` point runner target.

This is still not live-ready. The fixed row has real sample size and survives
one-tick total slippage per contract, but the edge is thin relative to drawdown:
profit factor is only `1.061`, fewer than half of the five-day windows are
positive, and the worst day is far too large for the current evaluation account.

Next useful work:

- add regime and daily health gates for `vwap_delta_exhaustion_fade_2pt_10d_cl0.5`;
- test whether the worst days cluster around trend days, news, opening-range
  expansion, or high directional VWAP stretch;
- only consider Sierra automation after drawdown control survives chronological
  validation and the execution model is confirmed at or below `1.0` tick total
  slippage per contract.

## First Risk-Control Pass

Status: **rejected as a rule change**

The first pass tested realized daily health gates and entry-known context
filters against the fixed `vwap_delta_exhaustion_fade_2pt_10d_cl0.5` row.

Code changes made for this pass:

- health-gate summaries now count scaled exits: `runner_target_hit` as a target
  and `full_stop_hit` / `ambiguous_full_stop_first` as losses;
- health-gate walk-forward supports `window_step_date_count`, allowing
  non-overlapping validation;
- scaled context diagnostics can read generated audit rows without a signal log
  and derive a stable `outcome_id`;
- synthetic scaled context diagnostics use entry-bar delta as the signal delta
  fallback when signal-log notes are unavailable;
- scaled context filters now include fade-edge and opening-range fade-edge
  thresholds.

Health-gate aggregate sweep:

| Metric | Value |
| --- | ---: |
| Sweep rows | `6000` |
| Best aggregate net | `72131.00` |
| Accepted trades | `642` |
| Skipped trades | `656` |
| Best aggregate gate | daily losses `3`, daily loss `1000`, consecutive losses `4`, max drawdown `6000`, drawdown pause `1` |

The aggregate result overfits. Non-overlapping `20x5` walk-forward on a
narrowed gate grid:

| Metric | Value |
| --- | ---: |
| Holdout windows | `25` |
| Accepted trades | `713` |
| Skipped trades | `398` |
| Accepted net USD | `18159.00` |
| Skipped net USD | `15351.50` |
| Same-window ungated net USD | `33510.50` |

Health gates improved the worst baseline block
`2026-04-10;2026-04-13;2026-04-14;2026-04-15;2026-04-16` from `-11323.50` to
`2415.50`, but they also skipped large positive blocks. The worst gated block
was `2026-01-22;2026-01-23;2026-01-26;2026-01-27;2026-01-28` at `-5538.00`,
while the skipped trades in that same block were `15504.50`.

Scaled context filter:

| Metric | Value |
| --- | ---: |
| Holdout windows | `25` |
| Holdout trades | `218` |
| Filtered net USD | `2499.00` |
| Same-window unfiltered net USD | `33510.50` |
| Filter improvement USD | `-31011.50` |
| Positive windows | `14` |
| Negative windows | `11` |

Interpretation: the current broad risk controls are not deployable. The base
VWAP/delta exhaustion entry remains the active research lead, but the first
daily-health and context-filter gates should not be applied to Sierra.

Next useful work is more targeted loss attribution: isolate the worst days and
blocks first, then test a veto designed from those failure modes rather than a
wide generic grid.
