# Sierra Delta Impulse Fixed Row Context Filter

Status: **diagnostic only**

## Sources

- Bars export:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Large.txt`
- Signal log:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`
- Fixed-row outcomes:
  `data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv`
- Context diagnostics:
  `reports/sierra-delta-impulse-fixed-row-context-diagnostics.csv`
- Walk-forward output:
  `reports/sierra-delta-impulse-fixed-row-context-filter-walk-forward.csv`

## Method

- context lookback: `20` prior 3-minute bars
- features: normalized risk, normalized runner target, normalized signal delta
  sum, entry volume ratio, entry trade-count ratio
- train window: `20` trade dates
- holdout window: `5` trade dates
- minimum selected train trades: `20`
- window step: `5` trade dates

## Result

- context rows: `163`
- trade dates: `41`
- all fixed-row net USD: `-15716`
- holdout windows: `4`
- selected holdout trades: `20`
- selected holdout net USD: `-4640`
- unfiltered same-window holdout trades: `111`
- unfiltered same-window holdout net USD: `-7927`

## Selected Holdouts

| Window | Holdout Dates | Selected Trades | Selected Net USD | Unfiltered Trades | Unfiltered Net USD | Selected Direction |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `1` | `2026-05-29;2026-06-01;2026-06-02;2026-06-03;2026-06-04` | `9` | `-2913` | `21` | `-6597` | `long` |
| `6` | `2026-06-05;2026-06-08;2026-06-09;2026-06-10;2026-06-11` | `8` | `-3506` | `30` | `-2160` | `long` |
| `11` | `2026-06-12;2026-06-15;2026-06-16;2026-06-17;2026-06-18` | `1` | `593` | `30` | `240` | `all` |
| `16` | `2026-06-19;2026-06-22;2026-06-23;2026-06-24;2026-06-25` | `2` | `1186` | `30` | `590` | `long` |

## Interpretation

The normalized context selector reduced exposure and lost less than the
unfiltered same-window holdout total, but the selected result is still negative.
This is not a validated filter.

The main finding is negative: the older 78-trade long-only shape did not survive
the expanded March-June sample. Do not promote the fixed Delta Impulse row or
this context selector without a materially changed hypothesis and a new
walk-forward test.
