# MGC Normal Bot Research

Status: exploratory MGC normal-profitability research. Not an ACSIL candidate yet.

## Objective

Find a normal MGC bot candidate, not an eval-pass configuration. Ranking favors profitability, recent performance, profit factor, yearly/quarterly stability, and drawdown-to-net ratio.

## Source

- rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- unique dates: `717`
- instrument: `MGC`, point value `$10`, tick value `$1`
- cost model: `$0.50/side` commission plus `1` total slippage tick per contract
- setup window inherited from the MGC research profile: `08:20` to `13:30`, flatten by `16:30`

## Search Space

- entry families: COMEX opening-range breakout, lookback breakout, VWAP pullback continuation
- one strategy signal per chart date
- quantities: `1`, `2`, `3`, `5` MGC
- target/stop points: `6/4`, `8/5`, `10/6`, `12/8`, `15/10`, `20/12`, `25/15`, `8/8`, `12/12`, `20/20`

## Result

Best row by normal-profitability ranking:

| Metric | Value |
| --- | ---: |
| Strategy | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0` |
| Quantity | `5` |
| Target / stop points | `25 / 15` |
| Target / stop net | `$1240 / $760` |
| Trades | `149` |
| Net | `$16905` |
| Average trade | `$113.45637584` |
| Win rate | `48.3%` |
| Profit factor | `1.32544037` |
| Max trade-sequence drawdown | `$-10320` |
| Drawdown / net | `61.0%` |
| Latest-year trades | `59` |
| Latest-year net | `$1600` |
| Recent 120 trade-day net | `$1400` |
| Worst year | `$1600` |
| Worst quarter | `$-7080` |
| Signal frequency | `25.1%` of trade dates |

Rows passing the first normal-profitability lens: `4`.

## Top Rows

| Rank | Family | Qty | Target | Stop | Trades | Net | PF | DD/Net | Latest | Recent120 | Worst Q | Strategy |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | mgc_vwap_pullback | 5 | 25 | 15 | 149 | 16905 | 1.32544037 | 61.0% | 1600 | 1400 | -7080 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0` |
| 2 | mgc_vwap_pullback | 3 | 25 | 15 | 149 | 10143 | 1.32544037 | 61.0% | 960 | 840 | -4248 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0` |
| 3 | mgc_vwap_pullback | 2 | 25 | 15 | 149 | 6762 | 1.32544037 | 61.0% | 640 | 560 | -2832 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0` |
| 4 | mgc_vwap_pullback | 1 | 25 | 15 | 149 | 3381 | 1.32544037 | 61.0% | 320 | 280 | -1416 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0` |
| 5 | mgc_vwap_pullback | 5 | 25 | 15 | 120 | 12290 | 1.29754267 | 69.3% | 2240 | 3280 | -6240 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri1` |
| 6 | mgc_vwap_pullback | 3 | 25 | 15 | 120 | 7374 | 1.29754267 | 69.3% | 1344 | 1968 | -3744 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri1` |
| 7 | mgc_vwap_pullback | 2 | 25 | 15 | 120 | 4916 | 1.29754267 | 69.3% | 896 | 1312 | -2496 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri1` |
| 8 | mgc_vwap_pullback | 1 | 25 | 15 | 120 | 2458 | 1.29754267 | 69.3% | 448 | 656 | -1248 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri1` |
| 9 | mgc_vwap_pullback | 5 | 25 | 15 | 101 | 8635 | 1.26246201 | 101.8% | 6230 | 3495 | -2430 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri0` |
| 10 | mgc_vwap_pullback | 3 | 25 | 15 | 101 | 5181 | 1.26246201 | 101.8% | 3738 | 2097 | -1458 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri0` |
| 11 | mgc_vwap_pullback | 2 | 25 | 15 | 101 | 3454 | 1.26246201 | 101.8% | 2492 | 1398 | -972 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri0` |
| 12 | mgc_vwap_pullback | 1 | 25 | 15 | 101 | 1727 | 1.26246201 | 101.8% | 1246 | 699 | -486 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri0` |
| 13 | mgc_or_breakout | 5 | 20 | 20 | 445 | 25345 | 1.16544814 | 30.1% | 11340 | 10270 | -5430 | `mgc_or_breakout:min_or6:buf0.5:delta0:cl0.55:end1330:skipfri0` |
| 14 | mgc_or_breakout | 3 | 20 | 20 | 445 | 15207 | 1.16544814 | 30.1% | 6804 | 6162 | -3258 | `mgc_or_breakout:min_or6:buf0.5:delta0:cl0.55:end1330:skipfri0` |
| 15 | mgc_or_breakout | 2 | 20 | 20 | 445 | 10138 | 1.16544814 | 30.1% | 4536 | 4108 | -2172 | `mgc_or_breakout:min_or6:buf0.5:delta0:cl0.55:end1330:skipfri0` |
| 16 | mgc_or_breakout | 1 | 20 | 20 | 445 | 5069 | 1.16544814 | 30.1% | 2268 | 2054 | -1086 | `mgc_or_breakout:min_or6:buf0.5:delta0:cl0.55:end1330:skipfri0` |
| 17 | mgc_or_breakout | 5 | 20 | 20 | 451 | 23195 | 1.14880513 | 44.8% | 5675 | 4605 | -5730 | `mgc_or_breakout:min_or6:buf0:delta0:cl0.55:end1330:skipfri0` |
| 18 | mgc_or_breakout | 3 | 20 | 20 | 451 | 13917 | 1.14880513 | 44.8% | 3405 | 2763 | -3438 | `mgc_or_breakout:min_or6:buf0:delta0:cl0.55:end1330:skipfri0` |
| 19 | mgc_or_breakout | 2 | 20 | 20 | 451 | 9278 | 1.14880513 | 44.8% | 2270 | 1842 | -2292 | `mgc_or_breakout:min_or6:buf0:delta0:cl0.55:end1330:skipfri0` |
| 20 | mgc_or_breakout | 1 | 20 | 20 | 451 | 4639 | 1.14880513 | 44.8% | 1135 | 921 | -1146 | `mgc_or_breakout:min_or6:buf0:delta0:cl0.55:end1330:skipfri0` |

## Interpretation

This scan deliberately avoids eval-pass metrics. A real MGC bot candidate still needs slippage stress, walk-forward/frozen holdout testing, session filtering, and Sierra replay/mechanics validation before implementation.
