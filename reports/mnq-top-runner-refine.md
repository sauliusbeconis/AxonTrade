# MNQ Top-Runner Refinement

Status: focused refinement of the first-pass MNQ runner leads.

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- quantity: fixed `2 MNQ`
- no breakeven or eval-pass geometry

## Result

Accepted rows by stricter runner lens: `82`.

Best accepted row:

| Metric | Value |
| --- | ---: |
| Base | `lookback_lb20_buf0_delta600_cl65_end1230_skipfri` |
| Filter | `time_1000_1100__clmin_gte0p9` |
| Target / Stop | `160 / 70` |
| Trades | `87` |
| Net | `$11772` |
| PF | `2.15039578` |
| Net/DD | `6.34951456` |
| DD | `$-1854` |
| Latest-year net | `$7089` |
| Worst quarter | `$-1005` |

## Top Rows

| Rank | Base | Filter | Target / Stop | Trades | Net | PF | Net/DD | DD | Latest | Worst Q |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `lookback_lb20_buf0_delta600_cl65_end1230_skipfri` | `time_1000_1100__clmin_gte0p9` | 160 / 70 | 87 | 11772 | 2.15039578 | 6.34951456 | -1854 | 7089 | -1005 |
| 2 | `lookback_lb20_buf0_delta600_cl65_end1230_skipfri` | `time_1000_1100__clmin_gte0p9` | 120 / 70 | 87 | 10135 | 2.08002984 | 8.84380454 | -1146 | 5548 | -1005 |
| 3 | `or60_buf0_delta0_cl65_end1430_allweek` | `weekday_tue_wed_thu__bar_lte25` | 100 / 70 | 87 | 7435 | 2.00202156 | 6.2742616 | -1185 | 2564 | -252 |
| 4 | `vwap_pullback_120_30_delta0_cl65_end1230_allweek` | `prev5_lte20` | 200 / 20 | 83 | 5542 | 1.98192771 | 4.45140562 | -1245 | 2531 | -415 |
| 5 | `or60_buf0_delta0_cl65_end1430_allweek` | `weekday_wed_thu_fri__absdelta_lte1000` | 120 / 70 | 143 | 14624 | 1.95857368 | 7.08184019 | -2065 | 5103 | -283 |
| 6 | `lookback_lb20_buf0_delta600_cl65_end1230_skipfri` | `time_1000_1100__clmin_gte0p9` | 160 / 90 | 87 | 10898 | 1.92622811 | 4.51449876 | -2414 | 6467 | -1325 |
| 7 | `vwap_pullback_120_30_delta0_cl65_end1230_allweek` | `weekday_not_mon__prev5_lte40` | 200 / 20 | 83 | 5102 | 1.90396882 | 4.39070568 | -1162 | 1900 | -498 |
| 8 | `vwap_pullback_120_30_delta0_cl65_end1230_allweek` | `weekday_not_mon__prev5_lte60` | 200 / 20 | 84 | 5019 | 1.87637507 | 4.0313253 | -1245 | 1817 | -498 |
| 9 | `lookback_lb20_buf0_delta600_cl65_end1230_skipfri` | `time_1000_1100__clmin_gte0p9` | 120 / 90 | 87 | 9341 | 1.87487122 | 5.93456163 | -1574 | 5006 | -1325 |
| 10 | `vwap_pullback_120_30_delta600_cl65_end1230_allweek` | `time_1030_1230__vwapdist_lte180` | 200 / 25 | 81 | 5853 | 1.8742345 | 3.15695793 | -1854 | 2491 | -412 |
| 11 | `or60_buf0_delta0_cl65_end1430_allweek` | `weekday_tue_wed_thu__bar_lte25` | 80 / 70 | 87 | 6273 | 1.86763485 | 4.66394052 | -1345 | 2067 | -186 |
| 12 | `lookback_lb20_buf0_delta600_cl65_end1230_skipfri` | `time_1000_1100__clmin_gte0p8` | 160 / 70 | 158 | 17334 | 1.85939514 | 9.57150745 | -1811 | 9197 | -325 |
| 13 | `vwap_pullback_120_30_delta0_cl65_end1230_allweek` | `weekday_not_mon__clmin_gte0p7` | 200 / 25 | 89 | 6177 | 1.85672677 | 4.61314414 | -1339 | 1974 | -206 |
| 14 | `vwap_pullback_120_30_delta600_cl65_end1230_allweek` | `time_1030_1230` | 200 / 25 | 82 | 5750 | 1.84583701 | 3.10140237 | -1854 | 2491 | -412 |
| 15 | `vwap_pullback_120_30_delta600_cl65_end1230_allweek` | `time_1030_1230__vwapdistmin_gte0` | 200 / 25 | 82 | 5750 | 1.84583701 | 3.10140237 | -1854 | 2491 | -412 |

## Best By Base

| Base | Filter | Target / Stop | Trades | Net | PF | DD | Latest | Worst Q |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `lookback_lb20_buf0_delta600_cl65_end1230_skipfri` | `time_1000_1100__clmin_gte0p9` | 160 / 70 | 87 | 11772 | 2.15039578 | -1854 | 7089 | -1005 |
| `or60_buf0_delta0_cl65_end1430_allweek` | `weekday_tue_wed_thu__bar_lte25` | 100 / 70 | 87 | 7435 | 2.00202156 | -1185 | 2564 | -252 |
| `vwap_pullback_120_30_delta0_cl65_end1230_allweek` | `prev5_lte20` | 200 / 20 | 83 | 5542 | 1.98192771 | -1245 | 2531 | -415 |
| `vwap_pullback_120_30_delta600_cl65_end1230_allweek` | `time_1030_1230__vwapdist_lte180` | 200 / 25 | 81 | 5853 | 1.8742345 | -1854 | 2491 | -412 |

## Interpretation

The goal of this pass is to find a stronger normal-profitability runner than the current MNQ VWAP/delta lead. Any accepted row still needs slippage stress and fixed holdout validation before replay.
