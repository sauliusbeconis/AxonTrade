# Sierra Delta Impulse Direction Variant Diagnostics

Status: **diagnostic only**

## Sources

- Bars export: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Large.txt`
- Signal log: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`
- Logged-direction sweep: `reports/sierra-delta-impulse-direction-variant-sweep-logged.csv`
- Inverted-direction sweep: `reports/sierra-delta-impulse-direction-variant-sweep-inverted.csv`
- Logged-direction walk-forward: `reports/sierra-delta-impulse-direction-variant-walk-forward-logged.csv`
- Inverted-direction walk-forward: `reports/sierra-delta-impulse-direction-variant-walk-forward-inverted.csv`

## Method

- `logged`: uses Sierra's original Delta Impulse continuation direction.
- `inverted`: flips every candidate direction and tests the same entry bar as a fade.
- train dates per walk-forward window: `20`
- holdout dates per walk-forward window: `5`
- minimum selected train trades: `20`
- window step: `5` trade dates

## Best In-Sample Sweep Rows

Logged direction:

| Direction | First Target | Stop | Runner Target | Runner Stop | Trades | Net USD |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| long | 4 | 8 | 8 | initial | 95 | -2090 |
| long | 4 | 2 | 8 | initial | 95 | -2815 |
| long | 4 | 2 | 10 | initial | 95 | -2815 |
| long | 5 | 2 | 8 | initial | 95 | -2965 |
| long | 5 | 2 | 10 | initial | 95 | -2965 |

Inverted direction:

| Direction | First Target | Stop | Runner Target | Runner Stop | Trades | Net USD |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| long | 5 | 10 | 15 | initial | 68 | 4849 |
| long | 5 | 8 | 15 | initial | 68 | 4049 |
| long | 2 | 10 | 15 | initial | 68 | 3749 |
| long | 4 | 10 | 15 | initial | 68 | 3049 |
| long | 2 | 8 | 15 | initial | 68 | 2449 |

## Walk-Forward Holdouts

| Variant | Holdout Windows | Holdout Trades | Holdout Net USD |
| --- | ---: | ---: | ---: |
| Logged | 4 | 72 | -11254 |
| Inverted | 4 | 100 | -4512.5 |

Inverted holdout rows:

| Holdout Dates | Direction | First Target | Stop | Runner Target | Runner Stop | Trades | Net USD |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| `2026-05-29;2026-06-01;2026-06-02;2026-06-03;2026-06-04` | all | 5 | 5 | 10 | initial | 21 | 3553 |
| `2026-06-05;2026-06-08;2026-06-09;2026-06-10;2026-06-11` | all | 5 | 5 | 10 | initial | 30 | -3710 |
| `2026-06-12;2026-06-15;2026-06-16;2026-06-17;2026-06-18` | short | 4 | 5 | 15 | initial | 19 | -2083 |
| `2026-06-19;2026-06-22;2026-06-23;2026-06-24;2026-06-25` | all | 4 | 10 | 15 | initial | 30 | -2272.5 |

## Interpretation

The inverted/fade direction produces positive in-sample rows, which means the failed continuation rule contains some information. However, the walk-forward holdout remains negative. Treat this as a parameter-fit warning, not as a tradable fade rule.

A future Delta Impulse variant needs a materially different entry hypothesis, such as a stricter auction regime or liquidity-sweep context, before more exit optimization is useful.
