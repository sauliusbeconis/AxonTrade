# Sierra Session-Structure Entry Baselines

Manual help needed: **No**.

## Purpose

The fast passive scalp tests were too execution-sensitive, so this branch tested
less frequent entries and larger exits:

- existing high-threshold synthetic entries spaced at least `900` seconds apart
- new time-based session-structure entries: opening-range breakouts, opening
  range sweep fades, VWAP reclaims, and VWAP pullback continuations
- wider two-contract exits: first target `2,3,4,5` points; stop
  `3,4,5,6,8` points; runner target `6,8,10,12,15,20` points

## Commands

Session-structure walk-forward:

```bash
.venv/bin/python scripts/run_signal_scalp_entry_baselines.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  reports/sierra-signal-log-scalp-entry-baselines-session-structure-defaultcost-walk-forward-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --entry-family-set session \
  --max-rule-entries-per-day 6 \
  --minimum-spacing-seconds 900 \
  --strategy-ids vwap_reclaim_continue_60m_4pt,opening_range_sweep_fade_30m_0.5pt,vwap_reclaim_continue_15m_2pt,vwap_reclaim_continue_30m_3pt,opening_range_sweep_fade_30m_1pt,opening_range_breakout_continue_30m_0.5pt \
  --output-mode walk_forward \
  --train-date-count 8 \
  --holdout-date-count 1 \
  --minimum-train-trades 4 \
  --first-target-points 2,3,4,5 \
  --stop-points 3,4,5,6,8 \
  --runner-target-points 6,8,10,12,15,20 \
  --runner-stop-modes breakeven,initial
```

Non-overlapping lead check:

```bash
.venv/bin/python scripts/run_signal_scalp_entry_baselines.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  reports/sierra-signal-log-scalp-entry-baselines-spaced-leads-defaultcost-walk-forward-holdout2-step2-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --max-rule-entries-per-day 6 \
  --minimum-spacing-seconds 900 \
  --strategy-ids vwap_delta_exhaustion_fade_4pt_30d_cl0.55,delta_impulse_continue_10bar_2.5pt_50d \
  --output-mode walk_forward \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --window-step-date-count 2 \
  --minimum-train-trades 4 \
  --first-target-points 2,3,4,5 \
  --stop-points 3,4,5,6,8 \
  --runner-target-points 6,8,10,12,15,20 \
  --runner-stop-modes breakeven,initial
```

## Results

Broad high-threshold entries with `900` second spacing:

| Slippage model | Holdout windows | Holdout trades | Holdout net USD | Avg/trade | Read |
| --- | ---: | ---: | ---: | ---: | --- |
| zero | `70` | `414` | `-1435.50` | `-3.47` | failed |
| half tick total/contract | `70` | `414` | `-6610.50` | `-15.97` | failed |
| default one tick/side | `70` | `414` | `-22135.50` | `-53.47` | failed |

New session-structure entries:

| Slippage model | Holdout windows | Holdout trades | Holdout net USD | Avg/trade | Read |
| --- | ---: | ---: | ---: | ---: | --- |
| zero | `68` | `244` | `367.00` | `1.50` | too thin |
| half tick total/contract | `68` | `244` | `-2683.00` | `-11.00` | failed |
| default one tick/side | `68` | `244` | `-11833.00` | `-48.50` | failed |

Non-overlapping two-day holdout check on the two lead families:

| Slippage model | Holdout windows | Holdout trades | Holdout net USD | Avg/trade | Read |
| --- | ---: | ---: | ---: | ---: | --- |
| zero | `6` | `68` | `5924.00` | `87.12` | positive |
| half tick total/contract | `6` | `68` | `5074.00` | `74.62` | positive |
| default one tick/side | `6` | `68` | `2524.00` | `37.12` | positive |

Default-cost non-overlapping lead breakdown:

| Entry family | Holdout trades | Net USD | Avg/trade | Full stops | First target hits | Runner targets | Runner stops | Positive trades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `delta_impulse_continue_10bar_2.5pt_50d` | `56` | `2608.00` | `46.57` | `18` | `38` | `18` | `20` | `32` |
| `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `12` | `-84.00` | `-7.00` | `2` | `10` | `2` | `8` | `10` |

Default-cost non-overlapping holdout windows:

| Holdout dates | Entry family | Trades | Net USD | Selected exit |
| --- | --- | ---: | ---: | --- |
| `2026-06-05;2026-06-08` | `delta_impulse_continue_10bar_2.5pt_50d` | `8` | `594.00` | `5 / 6 / 8 / breakeven` |
| `2026-06-09;2026-06-10` | `delta_impulse_continue_10bar_2.5pt_50d` | `12` | `1716.00` | `3 / 8 / 10 / initial` |
| `2026-06-11;2026-06-12` | `delta_impulse_continue_10bar_2.5pt_50d` | `12` | `1416.00` | `5 / 6 / 10 / breakeven` |
| `2026-06-15;2026-06-16` | `delta_impulse_continue_10bar_2.5pt_50d` | `12` | `-1434.00` | `5 / 5 / 15 / breakeven` |
| `2026-06-17;2026-06-18` | `delta_impulse_continue_10bar_2.5pt_50d` | `12` | `316.00` | `5 / 5 / 20 / breakeven` |
| `2026-06-17;2026-06-18` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `12` | `-84.00` | `2 / 5 / 6 / breakeven` |

## Read

The new opening-range and VWAP session-structure entries did not produce a
tradeable edge. They were barely positive with perfect fills and failed after
costs.

The useful lead is not the new session generator. It is the existing
`delta_impulse_continue_10bar_2.5pt_50d` family when entries are forced to be
less frequent with `900` second spacing and tested with larger exits. That lead
survived a non-overlapping two-day holdout check after default ES costs:
`$2608.00` over `56` holdout trades.

This is still not ready for automation. The sample is only `22` trade dates,
one non-overlapping holdout block lost `-$1434.00`, and the selected exit
parameters still move between windows. The next step is a trade-level audit of
the `delta_impulse_continue_10bar_2.5pt_50d` lead and then a dedicated overlay
rule, not broker work or live execution.
