# Sierra Delta Impulse 3-Min Large Sample Outcomes

This report evaluates the larger Sierra Chart export from
`ESU26-CME[M] 3 Min #2`.

## Sources

- Signal log:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`
- Bar export:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Large.txt`
- Live signal report:
  `reports/sierra-delta-impulse-signal-log-live.md`
- Exit sweep:
  `reports/sierra-delta-impulse-3min-large-scaled-exit-sweep.csv`
- Walk-forward:
  `reports/sierra-delta-impulse-3min-large-scaled-exit-walk-forward.csv`

## Candidate Log

- dates: `2026-06-10` through `2026-06-26`
- RTH dates with candidates: `13`
- candidates: `78`
- rejected rows: `0`
- signals per day: `6`
- directions: `41` long, `37` short
- logged overlay variant: `5 / 8 / 10 / initial`

The logged variant means:

- first target: `5` points
- stop: `8` points
- runner target: `10` points
- runner stop: initial stop

## Logged Variant Result

| Metric | Value |
| --- | ---: |
| Trades | 78 |
| First-target hits | 50 |
| Runner targets | 34 |
| Full stops | 26 |
| Net USD | -2246 |

Direction split:

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| Long | 41 | 3263 |
| Short | 37 | -5509 |

The larger sample invalidates the `5 / 8 / 10 / initial` all-direction setting.
Shorts are the main drag.

## Larger-Sample Fixed Exit Lead

Best all-direction fixed row from the larger sweep:

- first target: `5`
- stop: `10`
- runner target: `8`
- runner stop: `initial`

| Metric | Value |
| --- | ---: |
| Trades | 78 |
| First-target hits | 56 |
| Runner targets | 47 |
| Full stops | 20 |
| Net USD | 3104 |

Direction split for this row:

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| Long | 41 | 4463 |
| Short | 37 | -1359 |

This is the next all-direction collection candidate because it improves the
larger sample without introducing a new direction filter.

## Long-Only Observation

Best larger-sample in-sample row:

- direction: `long`
- first target: `5`
- stop: `8`
- runner target: `8`
- runner stop: `initial`
- trades: `41`
- net USD: `5163`

However, long-only walk-forward selection was negative:

- overlapping holdout: `23` trades, `-3086`
- non-overlapping holdout: `19` trades, `-2558`

Do not promote long-only filtering from this result yet.

## Walk-Forward

The all-direction rolling selection was also weak:

- train dates per window: `4`
- holdout dates per window: `2`
- holdout windows: `4`
- holdout trades: `48`
- holdout net USD: `-1111`

This means the current family is still research-only. The fixed `5 / 10 / 8 /
initial` candidate is worth collecting next, but not accepted for live order
routing.

## Next Step

Set the Sierra overlay to:

`5 / 10 / 8 / initial`

Then collect another larger same-chart export. The key question is whether the
short side keeps improving with the wider stop or remains a persistent drag.
