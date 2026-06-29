# Sierra Delta Impulse 3-Min Replay Outcomes

This report evaluates the Sierra Chart overlay output from chart
`ESU26-CME[M] 3 Min #2`.

## Sources

- Signal log:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`
- Bar export:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min.txt`
- Candidate report:
  `reports/sierra-delta-impulse-signal-log-live.md`
- Scaled outcome CSV:
  `data/processed/AxonTrade_ES_delta_impulse_3min_scaled_outcomes.csv`
- Exit sweep:
  `reports/sierra-delta-impulse-3min-scaled-exit-sweep.csv`
- Thin walk-forward:
  `reports/sierra-delta-impulse-3min-scaled-exit-walk-forward.csv`

## Candidate Log

The overlay wrote a clean candidate-only log:

- rows: `30`
- candidates: `30`
- rejected rows: `0`
- dates: `2026-06-22` through `2026-06-26`
- max signals: `6` per day
- direction split: `13` long, `17` short

## Original Fixed Exit

The original overlay exit was:

- first target: `5` points
- stop: `5` points
- runner target: `15` points
- runner stop mode: `breakeven`

Result on the 3-minute replay export:

| Metric | Value |
| --- | ---: |
| Trades | 30 |
| First-target hits | 14 |
| Runner targets | 2 |
| Breakeven exits | 10 |
| Full stops | 14 |
| Net USD | -4710 |

This exit is too fragile on the 3-minute chart sample. The first target is hit
often enough to matter, but the breakeven runner converts many trades into
small wins while full stops remain large.

## Best In-Sample Exit Sweep

Best row from the local sweep:

- first target: `5`
- stop: `8`
- runner target: `10`
- runner stop mode: `initial`
- direction: `all`

Result:

| Metric | Value |
| --- | ---: |
| Trades | 30 |
| First-target hits | 24 |
| Runner targets | 17 |
| Full stops | 6 |
| Net USD | 5190 |
| Average net/trade | 173 |

The same family also preferred an `8` point stop in nearby top rows. This says
the 3-minute replay sample needs a wider stop and should not move the runner to
breakeven immediately after the first target.

## Thin Walk-Forward Check

Parameters:

- train dates per window: `2`
- holdout dates per window: `1`
- window step: `1`
- minimum train trades: `8`

Holdout result:

| Metric | Value |
| --- | ---: |
| Holdout windows | 3 |
| Holdout trades | 15 |
| Holdout net USD | 3545 |

Selected exits:

| Holdout date | Direction | First target | Stop | Runner target | Runner stop | Holdout net |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| 2026-06-24 | short | 5 | 8 | 15 | initial | -121 |
| 2026-06-25 | all | 5 | 8 | 8 | initial | 1308 |
| 2026-06-26 | all | 5 | 8 | 10 | initial | 2358 |

This is encouraging, but the sample is still only five trading days. Treat it
as a reason to continue collecting 3-minute overlay data, not as acceptance.

## Interpretation

The restored 3-minute chart changes the meaning of the research rule:
`10` bars now means about `30` minutes of impulse, not the lower-timeframe
export context used earlier. On this chart, the entry family may still have
signal, but the currently loaded `5 / 5 / 15 / breakeven` exit is not the right
version. The next candidate overlay configuration to test is:

`5 / 8 / 10 / initial`

Do not enable live order routing from this result. We need a larger same-chart
export before promoting it from research.
