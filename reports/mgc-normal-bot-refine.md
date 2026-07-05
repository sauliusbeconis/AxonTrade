# MGC Normal Bot Refinement

Status: refinement of the first MGC normal-profitability VWAP pullback lead.

## Source

- rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- base strategy: `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0`
- base signals: `149`

## Filter Search

- direction: both, long-only, short-only
- weekdays: all week, no Friday, Monday-Wednesday, Tuesday-Thursday, Tuesday-Wednesday, Wednesday-Thursday
- entry windows: `08:20-10:30`, `08:20-09:30`, `09:00-10:30`, `09:30-10:30`, `08:20-10:00`
- context: absolute delta caps, bar-range caps, day-range caps, VWAP-distance caps, simple combinations
- risk points: `20/12`, `25/12`, `25/15`, `30/15`, `30/18`, `35/20`, `25/20`, `30/20`

## Result

Best refined row by normal-profitability ranking:

| Metric | Value |
| --- | ---: |
| Strategy | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:none` |
| Quantity | `5` |
| Target / stop points | `30 / 15` |
| Target / stop net | `$1490 / $760` |
| Trades | `116` |
| Net | `$19400` |
| Average trade | `$167.24137931` |
| Win rate | `49.1%` |
| Profit factor | `1.49916377` |
| Max drawdown | `$-3950` |
| Drawdown / net | `20.4%` |
| Latest-year net | `$8040` |
| Recent 120 trade-day net | `$7340` |
| Worst year | `$4070` |
| Worst quarter | `$-885` |

Rows passing the normal-profitability lens: `224`.

## Top Rows

| Rank | Qty | Target | Stop | Trades | Net | PF | DD/Net | Latest | Recent120 | Worst Q | Strategy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 5 | 30 | 15 | 116 | 19400 | 1.49916377 | 20.4% | 8040 | 7340 | -885 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:none` |
| 2 | 5 | 30 | 15 | 116 | 19400 | 1.49916377 | 20.4% | 8040 | 7340 | -885 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:vwapdist20` |
| 3 | 5 | 30 | 15 | 116 | 19400 | 1.49916377 | 20.4% | 8040 | 7340 | -885 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:vwapdist30` |
| 4 | 3 | 30 | 15 | 116 | 11640 | 1.49916377 | 20.4% | 4824 | 4404 | -531 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:none` |
| 5 | 3 | 30 | 15 | 116 | 11640 | 1.49916377 | 20.4% | 4824 | 4404 | -531 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:vwapdist20` |
| 6 | 3 | 30 | 15 | 116 | 11640 | 1.49916377 | 20.4% | 4824 | 4404 | -531 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:vwapdist30` |
| 7 | 2 | 30 | 15 | 116 | 7760 | 1.49916377 | 20.4% | 3216 | 2936 | -354 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:none` |
| 8 | 2 | 30 | 15 | 116 | 7760 | 1.49916377 | 20.4% | 3216 | 2936 | -354 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:vwapdist20` |
| 9 | 2 | 30 | 15 | 116 | 7760 | 1.49916377 | 20.4% | 3216 | 2936 | -354 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:vwapdist30` |
| 10 | 1 | 30 | 15 | 116 | 3880 | 1.49916377 | 20.4% | 1608 | 1468 | -177 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:none` |
| 11 | 1 | 30 | 15 | 116 | 3880 | 1.49916377 | 20.4% | 1608 | 1468 | -177 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:vwapdist20` |
| 12 | 1 | 30 | 15 | 116 | 3880 | 1.49916377 | 20.4% | 1608 | 1468 | -177 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:vwapdist30` |
| 13 | 5 | 30 | 15 | 114 | 18670 | 1.48996195 | 23.0% | 8800 | 8100 | -885 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:dayrange60` |
| 14 | 3 | 30 | 15 | 114 | 11202 | 1.48996195 | 23.0% | 5280 | 4860 | -531 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:dayrange60` |
| 15 | 2 | 30 | 15 | 114 | 7468 | 1.48996195 | 23.0% | 3520 | 3240 | -354 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:dayrange60` |
| 16 | 1 | 30 | 15 | 114 | 3734 | 1.48996195 | 23.0% | 1760 | 1620 | -177 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:dayrange60` |
| 17 | 5 | 30 | 15 | 107 | 18325 | 1.51663378 | 25.7% | 8800 | 8100 | -1615 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:abs200_day60` |
| 18 | 3 | 30 | 15 | 107 | 10995 | 1.51663378 | 25.7% | 5280 | 4860 | -969 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:abs200_day60` |
| 19 | 2 | 30 | 15 | 107 | 7330 | 1.51663378 | 25.7% | 3520 | 3240 | -646 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:abs200_day60` |
| 20 | 1 | 30 | 15 | 107 | 3665 | 1.51663378 | 25.7% | 1760 | 1620 | -323 | `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:abs200_day60` |

## Interpretation

The refinement is still offline research. Prefer candidates that improve recent performance and reduce bad-quarter behavior without becoming too sparse.
