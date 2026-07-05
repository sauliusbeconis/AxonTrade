# MNQ Breakeven-Frequency Refinement

Status: focused filter refinement of the weak-positive MNQ breakeven-frequency lead.

## Fixed Baseline

- strategy: `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1230:skipfri1:maxday1:space30`
- management: `4 MNQ`, split `3+1`, `25 / 40 / 80`
- base evaluated trades before filters: `362`
- source rows: `67300`
- source dates: `2024-07-15` through `2026-07-02`

## Result

| Baseline Metric | Value |
| --- | ---: |
| Trades | `362` |
| Trades/week | `3.53417015` |
| Net | `$1173.5` |
| PF | `1.02895386` |
| Latest-year net | `$-246.5` |
| Worst quarter | `$-2728` |
| Max trade-sequence DD | `$-3986` |

Rows meeting the acceptance lens: `0`.
No refined filter is accepted. The weak positive row could not be stabilized with simple time, weekday, direction, or context filters.

## Top Ranked Filters

| Rank | Filter | Trades | /Wk | T1 Hit | Full Stop | Net | PF | Latest-Year Net | Worst Quarter | Max DD |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `prev5_lte30` | 84 | 0.82008368 | 65.5% | 33.3% | 1913 | 1.20957493 | 471.5 | -280 | -1520 |
| 2 | `time_1030_1230__prev5_lte30` | 84 | 0.82008368 | 65.5% | 33.3% | 1913 | 1.20957493 | 471.5 | -280 | -1520 |
| 3 | `time_1100_1230__vwapdist_lte120` | 152 | 1.48396095 | 66.4% | 32.9% | 1356 | 1.08319018 | 167.5 | -789.5 | -1977.5 |
| 4 | `openmove_lte120` | 223 | 2.17712692 | 65.0% | 34.1% | 645.5 | 1.02594245 | 16 | -886 | -1902 |
| 5 | `weekday_mon_tue_wed__lbmove_lte60` | 96 | 0.93723849 | 67.7% | 31.2% | 2388.5 | 1.24160429 | 175.5 | -938 | -2959.5 |
| 6 | `weekday_not_thu__lbmove_lte60` | 96 | 0.93723849 | 67.7% | 31.2% | 2388.5 | 1.24160429 | 175.5 | -938 | -2959.5 |
| 7 | `weekday_mon_tue_wed__lbmove_lte80` | 144 | 1.40585774 | 67.4% | 31.9% | 3260.5 | 1.21589856 | 563.5 | -665.5 | -2529.5 |
| 8 | `weekday_not_thu__lbmove_lte80` | 144 | 1.40585774 | 67.4% | 31.9% | 3260.5 | 1.21589856 | 563.5 | -665.5 | -2529.5 |
| 9 | `weekday_tue_wed_thu__absdelta_lte1600` | 106 | 1.0348675 | 67.9% | 32.1% | 2310 | 1.20840852 | 904 | -346 | -2158 |
| 10 | `weekday_not_mon__absdelta_lte1600` | 106 | 1.0348675 | 67.9% | 32.1% | 2310 | 1.20840852 | 904 | -346 | -2158 |
| 11 | `weekday_mon_tue_wed__lbmove_lte120` | 206 | 2.0111576 | 67.5% | 32.0% | 4179.5 | 1.19329849 | 1163.5 | -716 | -2488 |
| 12 | `weekday_not_thu__lbmove_lte120` | 206 | 2.0111576 | 67.5% | 32.0% | 4179.5 | 1.19329849 | 1163.5 | -716 | -2488 |

## Positive Latest-Year Rows

| Rank | Filter | Trades | Net | PF | Latest-Year Net | Worst Quarter | Max DD |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `weekday_wed` | 92 | 3392 | 1.40018877 | 175.5 | -1060 | -1508 |
| 2 | `short_only` | 158 | 3862 | 1.25205587 | 638 | -1410 | -1994 |
| 3 | `weekday_mon_tue_wed__vwapdist_lte80` | 172 | 4273.5 | 1.2458295 | 1465.5 | -1430 | -2911.5 |
| 4 | `weekday_not_thu__vwapdist_lte80` | 172 | 4273.5 | 1.2458295 | 1465.5 | -1430 | -2911.5 |
| 5 | `weekday_mon_tue_wed__lbmove_lte60` | 96 | 2388.5 | 1.24160429 | 175.5 | -938 | -2959.5 |
| 6 | `weekday_not_thu__lbmove_lte60` | 96 | 2388.5 | 1.24160429 | 175.5 | -938 | -2959.5 |
| 7 | `short_only__vwapdist_lte120` | 128 | 2982 | 1.2345446 | 646 | -1372 | -2002 |
| 8 | `weekday_mon_tue_wed__lbmove_lte80` | 144 | 3260.5 | 1.21589856 | 563.5 | -665.5 | -2529.5 |
| 9 | `weekday_not_thu__lbmove_lte80` | 144 | 3260.5 | 1.21589856 | 563.5 | -665.5 | -2529.5 |
| 10 | `prev5_lte30` | 84 | 1913 | 1.20957493 | 471.5 | -280 | -1520 |

## Interpretation

The breakeven-frequency concept still has one useful observation: a high target-one touch rate is possible on MNQ lookback continuation. The problem is that the protected outcomes are too small relative to the full stops, and the runner does not hit often enough to carry the strategy.

Next research should either change the entry family or use a different trade-management shape. More filtering of this exact baseline is likely to overfit.
