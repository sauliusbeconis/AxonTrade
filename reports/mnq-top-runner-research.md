# MNQ Top-Runner Research

Status: first-pass normal-profitability runner scan for MNQ.

## Objective

This pass skips the breakeven-frequency idea and searches for stronger runner-style bots: high profit factor, high net, and low trade-sequence drawdown. It is not eval-pass geometry.

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique dates: `507`
- instrument: `MNQ`, point value `$2`, tick value `$0.50`
- cost model: `$0.50/side` commission plus `1` total slippage tick per contract

## Search Space

- entry families: lookback breakout, opening-range breakout, VWAP pullback, delta impulse
- exit: fixed runner target/stop with session flatten
- quantity: fixed `2 MNQ` for comparable PF/net/DD
- target grid: `60,80,100,120,160,200,260,320` MNQ points
- stop grid: `25,35,50,70,90,120` MNQ points
- one-hour signal spacing and one open trade per strategy

## Result

Accepted rows by runner lens: `0`.

Top ranked row:

| Metric | Value |
| --- | ---: |
| Strategy | `runner_vwap_pullback:stretch120:pb30:delta600:cl0.65:end1230:skipfri1` |
| Family | `runner_vwap_pullback` |
| Target / Stop | `200 / 25` |
| Trades | `71` |
| Trades/week | `0.69316597` |
| Net | `$2587` |
| PF | `1.41860841` |
| Net/DD | `1.45500562` |
| Max trade-sequence DD | `$-1778` |
| Latest-year net | `$304` |
| Worst quarter | `$-542` |
| Win rate | `15.5%` |
| Target hit rate | `15.5%` |
| Stop hit rate | `84.5%` |

## Top Rows

| Rank | Family | Target / Stop | Trades | /Wk | Net | PF | Net/DD | DD | Latest | Worst Q | Strategy |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | runner_vwap_pullback | 200 / 25 | 71 | 0.69316597 | 2587 | 1.41860841 | 1.45500562 | -1778 | 304 | -542 | `runner_vwap_pullback:stretch120:pb30:delta600:cl0.65:end1230:skipfri1` |
| 2 | runner_vwap_pullback | 200 / 25 | 82 | 0.80055788 | 2945 | 1.41438019 | 1.87340967 | -1572 | 1486 | -645 | `runner_vwap_pullback:stretch120:pb30:delta0:cl0.65:end1230:skipfri1` |
| 3 | runner_vwap_pullback | 260 / 25 | 113 | 1.10320781 | 3762 | 1.38855608 | 2.00106383 | -1880 | 1592 | -412 | `runner_vwap_pullback:stretch120:pb30:delta0:cl0.65:end1230:skipfri0` |
| 4 | runner_vwap_pullback | 200 / 25 | 84 | 0.82008368 | 2739 | 1.37453849 | 1.74236641 | -1572 | 1383 | -645 | `runner_vwap_pullback:stretch120:pb30:delta0:cl0.55:end1230:skipfri1` |
| 5 | runner_vwap_pullback | 60 / 25 | 99 | 0.9665272 | 2383 | 1.37316004 | 1.65256588 | -1442 | 94 | -432 | `runner_vwap_pullback:stretch120:pb30:delta600:cl0.65:end1230:skipfri0` |
| 6 | runner_vwap_pullback | 200 / 25 | 73 | 0.71269177 | 2381 | 1.37284685 | 1.33914511 | -1778 | 201 | -542 | `runner_vwap_pullback:stretch120:pb30:delta600:cl0.55:end1230:skipfri1` |
| 7 | runner_vwap_pullback | 100 / 25 | 99 | 0.9665272 | 2803 | 1.37278893 | 1.88500336 | -1487 | 1174 | -309 | `runner_vwap_pullback:stretch120:pb30:delta600:cl0.65:end1230:skipfri0` |
| 8 | runner_vwap_pullback | 320 / 25 | 113 | 1.10320781 | 3584 | 1.37017145 | 1.81284775 | -1977 | 1862 | -412 | `runner_vwap_pullback:stretch120:pb30:delta0:cl0.65:end1230:skipfri0` |
| 9 | runner_vwap_pullback | 80 / 25 | 99 | 0.9665272 | 2403 | 1.33811735 | 1.66643551 | -1442 | 1134 | -285 | `runner_vwap_pullback:stretch120:pb30:delta600:cl0.65:end1230:skipfri0` |
| 10 | runner_vwap_pullback | 100 / 25 | 114 | 1.11297071 | 2758 | 1.31501999 | 1.71838006 | -1605 | 762 | -412 | `runner_vwap_pullback:stretch120:pb30:delta0:cl0.65:end1230:skipfri0` |
| 11 | runner_vwap_pullback | 120 / 25 | 114 | 1.11297071 | 2758 | 1.30086179 | 1.40142276 | -1968 | 1062 | -412 | `runner_vwap_pullback:stretch120:pb30:delta0:cl0.65:end1230:skipfri0` |
| 12 | runner_vwap_pullback | 60 / 25 | 82 | 0.80055788 | 1414 | 1.2590218 | 1.04818384 | -1349 | 475 | -432 | `runner_vwap_pullback:stretch120:pb10:delta600:cl0.65:end1230:skipfri0` |
| 13 | runner_lookback_breakout | 60 / 35 | 187 | 1.82566248 | 3642 | 1.25734878 | 2.48940533 | -1463 | 3540 | -823 | `runner_lookback_breakout:lb60:buf5:delta1000:cl0.65:end1430:skipfri1` |
| 14 | runner_vwap_pullback | 120 / 25 | 99 | 0.9665272 | 1983 | 1.24682599 | 1.02746114 | -1930 | 894 | -385 | `runner_vwap_pullback:stretch120:pb30:delta600:cl0.65:end1230:skipfri0` |
| 15 | runner_vwap_pullback | 60 / 25 | 114 | 1.11297071 | 1858 | 1.24376804 | 1.6114484 | -1153 | 22 | -381 | `runner_vwap_pullback:stretch120:pb30:delta0:cl0.65:end1230:skipfri0` |

## Best By Family

| Family | Target / Stop | Trades | Net | PF | DD | Latest | Worst Q | Strategy |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| runner_vwap_pullback | 200 / 25 | 71 | 2587 | 1.41860841 | -1778 | 304 | -542 | `runner_vwap_pullback:stretch120:pb30:delta600:cl0.65:end1230:skipfri1` |
| runner_lookback_breakout | 60 / 35 | 187 | 3642 | 1.25734878 | -1463 | 3540 | -823 | `runner_lookback_breakout:lb60:buf5:delta1000:cl0.65:end1430:skipfri1` |
| runner_opening_range_breakout | 100 / 90 | 479 | 15268 | 1.2127292 | -3880 | 5844 | -1372 | `runner_opening_range_breakout:or60:buf0:delta600:cl0.55:end1430:skipfri1` |
| runner_delta_impulse | 100 / 90 | 457 | 13306 | 1.18735567 | -3348 | 381 | -1089 | `runner_delta_impulse:range10:delta1600:cl0.65:vwap40:end1230:skipfri1` |

## Interpretation

Rows from this scan are research leads only. A candidate must still pass slippage stress and fixed holdout validation before replay/mechanics.
