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
- train window: `8` trade dates
- holdout window: `2` trade dates
- minimum selected train trades: `12`
- window step: `1` trade date

## Result

- context rows: `78`
- trade dates: `13`
- all fixed-row net USD: `3104`
- holdout windows: `4`
- selected holdout trades: `19`
- selected holdout net USD: `6917`
- unfiltered same-window holdout trades: `48`
- unfiltered same-window holdout net USD: `8064`

## Selected Holdouts

| Window | Holdout Dates | Selected Trades | Selected Net USD | Unfiltered Trades | Unfiltered Net USD | Selected Direction |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `1` | `2026-06-22;2026-06-23` | `3` | `129` | `12` | `366` | `long` |
| `2` | `2026-06-23;2026-06-24` | `4` | `2372` | `12` | `2016` | `long` |
| `3` | `2026-06-24;2026-06-25` | `6` | `2658` | `12` | `2016` | `long` |
| `4` | `2026-06-25;2026-06-26` | `6` | `1758` | `12` | `3666` | `long` |

## Interpretation

The normalized context selector found a stable-looking long-only shape:
`minutes=0-120 or 0-180`, `max_risk_avg_range=4`,
`max_runner_avg_range=4`, and `signal_delta_avg=0-20`.

It did not improve over the unfiltered same-window holdout total. The result is
useful because it shows the current edge is concentrated in recent long trades,
but it is not enough to advance the setup toward live execution.
