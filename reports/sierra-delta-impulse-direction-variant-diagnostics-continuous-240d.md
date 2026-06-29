# Sierra Delta Impulse Direction Variant Diagnostics

Status: **diagnostic only**

## Sources

- Bars export: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Continuous_240D.txt`
- Signal log: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`
- Logged-direction sweep: `reports/sierra-delta-impulse-direction-variant-sweep-logged-continuous-240d.csv`
- Inverted-direction sweep: `reports/sierra-delta-impulse-direction-variant-sweep-inverted-continuous-240d.csv`
- Logged-direction walk-forward: `reports/sierra-delta-impulse-direction-variant-walk-forward-logged-continuous-240d.csv`
- Inverted-direction walk-forward: `reports/sierra-delta-impulse-direction-variant-walk-forward-inverted-continuous-240d.csv`

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
| short | 5 | 8 | 15 | initial | 426 | -23469.5 |
| short | 3 | 8 | 15 | initial | 426 | -25019.5 |
| short | 2 | 8 | 15 | initial | 426 | -25219.5 |
| short | 4 | 8 | 15 | initial | 426 | -27094.5 |
| short | 3 | 8 | 5 | initial | 426 | -27732 |

Inverted direction:

| Direction | First Target | Stop | Runner Target | Runner Stop | Trades | Net USD |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| long | 5 | 8 | 15 | initial | 426 | -1482 |
| long | 3 | 8 | 15 | initial | 426 | -2507 |
| long | 4 | 8 | 15 | initial | 426 | -3007 |
| long | 2 | 8 | 15 | initial | 426 | -5207 |
| long | 5 | 10 | 15 | initial | 426 | -5819.5 |

## Walk-Forward Holdouts

| Variant | Holdout Windows | Holdout Trades | Holdout Net USD |
| --- | ---: | ---: | ---: |
| Logged | 29 | 467 | -58781.5 |
| Inverted | 29 | 437 | -13209 |

Inverted holdout rows:

| Holdout Dates | Direction | First Target | Stop | Runner Target | Runner Stop | Trades | Net USD |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| `2025-12-01;2025-12-02;2025-12-03;2025-12-04;2025-12-05` | short | 4 | 5 | 8 | initial | 18 | 6074 |
| `2025-12-08;2025-12-09;2025-12-10;2025-12-11;2025-12-12` | short | 4 | 5 | 8 | initial | 14 | -298 |
| `2025-12-15;2025-12-16;2025-12-17;2025-12-18;2025-12-19` | short | 5 | 5 | 8 | initial | 16 | 638 |
| `2025-12-22;2025-12-23;2025-12-24;2025-12-26;2025-12-29` | all | 4 | 8 | 8 | initial | 30 | -8935 |
| `2025-12-30;2025-12-31;2026-01-02;2026-01-05;2026-01-06` | short | 5 | 10 | 10 | initial | 15 | -1105 |
| `2026-01-07;2026-01-08;2026-01-09;2026-01-12;2026-01-13` | long | 3 | 10 | 15 | initial | 8 | 4844 |
| `2026-01-14;2026-01-15;2026-01-16;2026-01-19;2026-01-20` | long | 3 | 10 | 15 | initial | 11 | 623 |
| `2026-01-21;2026-01-22;2026-01-23;2026-01-26;2026-01-27` | long | 3 | 10 | 15 | initial | 6 | -2154.5 |
| `2026-01-28;2026-01-29;2026-01-30;2026-02-02;2026-02-03` | long | 5 | 8 | 15 | initial | 17 | -5269 |
| `2026-02-04;2026-02-05;2026-02-06;2026-02-09;2026-02-10` | long | 5 | 4 | 15 | initial | 11 | -3227 |
| `2026-02-11;2026-02-12;2026-02-13;2026-02-16;2026-02-17` | short | 2 | 6 | 15 | initial | 15 | 2695 |
| `2026-02-18;2026-02-19;2026-02-20;2026-02-23;2026-02-24` | short | 5 | 4 | 15 | initial | 16 | 538 |
| `2026-02-25;2026-02-26;2026-02-27;2026-03-02;2026-03-03` | short | 5 | 8 | 10 | initial | 22 | -1654 |
| `2026-03-04;2026-03-05;2026-03-06;2026-03-09;2026-03-10` | all | 5 | 10 | 10 | initial | 30 | -3710 |
| `2026-03-11;2026-03-12;2026-03-13;2026-03-16;2026-03-17` | all | 5 | 8 | 10 | initial | 30 | -2310 |
| `2026-03-18;2026-03-19;2026-03-20;2026-03-23;2026-03-24` | long | 5 | 10 | 15 | initial | 9 | 737 |
| `2026-03-25;2026-03-26;2026-03-27;2026-03-30;2026-03-31` | long | 3 | 10 | 15 | initial | 15 | -1155 |
| `2026-04-01;2026-04-02;2026-04-06;2026-04-07;2026-04-08` | long | 3 | 10 | 5 | initial | 14 | -148 |
| `2026-04-09;2026-04-10;2026-04-13;2026-04-14;2026-04-15` | long | 3 | 10 | 5 | initial | 8 | 1344 |
| `2026-04-16;2026-04-17;2026-04-20;2026-04-21;2026-04-22` | long | 4 | 8 | 5 | initial | 13 | 59 |
| `2026-04-23;2026-04-24;2026-04-27;2026-04-28;2026-04-29` | long | 4 | 8 | 5 | initial | 12 | -934 |
| `2026-04-30;2026-05-01;2026-05-04;2026-05-05;2026-05-06` | long | 4 | 8 | 15 | initial | 12 | 2566 |
| `2026-05-07;2026-05-08;2026-05-11;2026-05-12;2026-05-13` | long | 4 | 8 | 15 | initial | 12 | -934 |
| `2026-05-14;2026-05-15;2026-05-18;2026-05-19;2026-05-20` | long | 4 | 6 | 15 | initial | 11 | -2627 |
| `2026-05-21;2026-05-22;2026-05-25;2026-05-26;2026-05-27` | long | 5 | 6 | 15 | initial | 15 | -1917.5 |
| `2026-05-28;2026-05-29;2026-06-01;2026-06-02;2026-06-03` | long | 5 | 4 | 15 | initial | 14 | 2452 |
| `2026-06-04;2026-06-05;2026-06-08;2026-06-09;2026-06-10` | short | 3 | 5 | 5 | initial | 12 | -1384 |
| `2026-06-11;2026-06-12;2026-06-15;2026-06-16;2026-06-17` | short | 4 | 10 | 5 | initial | 15 | -655 |
| `2026-06-18;2026-06-19;2026-06-22;2026-06-23;2026-06-24` | short | 4 | 10 | 5 | initial | 16 | 2638 |

## Interpretation

The inverted/fade direction is less bad than the logged continuation direction, but its best full-sample sweep row is still negative. That is not a tradable inversion edge.

In walk-forward holdout, inverted direction changes net by 45572.5 USD versus logged direction, but remains -13209 USD overall.

A future Delta Impulse variant needs a materially different entry hypothesis, such as a stricter auction regime or liquidity-sweep context, before more exit optimization is useful.
