# MGC Lookback Breakout Refinement

Status: focused refinement of the high-frequency MGC lookback-breakout lead. Not an ACSIL candidate yet.

## Source

- rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- base parameter sets: `64`
- base parameter sets with signals: `64`
- instrument: `MGC`, one-minute Sierra order-flow export
- cost model: `$0.50/side` commission plus `1` total slippage tick per contract

## Search Space

- family: lookback breakout continuation
- lookbacks: `5`, `10`, `15`, `20` bars
- buffers: `0`, `0.5` points
- delta thresholds: `0`, `50`
- close-location thresholds: `0.50`, `0.55`
- entry ends: `10:30`, `13:30`
- policies: max `1` trade/day and max `2` trades/day with `15` minute re-entry gap
- filters: direction, weekday, time, bar range, day range, VWAP distance, and absolute delta caps

## Result

Best row by focused normal-profitability ranking:

| Metric | Value |
| --- | ---: |
| Strategy | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1030:filterbar8:maxday1_gap0` |
| Target / stop points | `25 / 15` |
| Target / stop net | `$248 / $152` |
| Trades | `586` |
| Signal days | `586` |
| Net | `$8445` |
| Average trade | `$14.4112628` |
| Win rate | `48.8%` |
| Profit factor | `1.21812687` |
| Max trade-sequence drawdown | `$-1337` |
| Drawdown / net | `15.8%` |
| Latest-year trades | `124` |
| Latest-year net | `$2622` |
| Recent 120 trade-day net | `$2542` |
| Worst year | `$2460` |
| Worst quarter | `$-456` |

Rows passing the focused first-pass lens: `55`.

## Top Rows

| Rank | Target | Stop | Trades | Net | PF | DD/Net | Latest | Recent120 | Worst Q | Strategy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 25 | 15 | 586 | 8445 | 1.21812687 | 15.8% | 2622 | 2542 | -456 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1030:filterbar8:maxday1_gap0` |
| 2 | 25 | 15 | 586 | 7973 | 1.20478771 | 16.8% | 2222 | 2142 | -456 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.55:end1030:filterbar8:maxday1_gap0` |
| 3 | 30 | 15 | 554 | 7982 | 1.2185951 | 17.4% | 3874 | 3415 | -366 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.55:end1030:filterabsdelta100:maxday1_gap0` |
| 4 | 30 | 15 | 555 | 8324 | 1.22806104 | 17.7% | 4324 | 3865 | -460 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1030:filterabsdelta100:maxday1_gap0` |
| 5 | 30 | 15 | 586 | 8287 | 1.20992502 | 18.5% | 3822 | 3542 | -599 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1030:filterbar8:maxday1_gap0` |
| 6 | 25 | 15 | 554 | 7796 | 1.21803944 | 18.9% | 3095 | 2711 | -309 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.55:end1030:filterabsdelta100:maxday1_gap0` |
| 7 | 25 | 15 | 555 | 8047 | 1.22516019 | 19.4% | 3495 | 3111 | -293 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1030:filterabsdelta100:maxday1_gap0` |
| 8 | 30 | 15 | 658 | 10074 | 1.22515757 | 19.9% | 5805 | 5683 | -791 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.5:end1030:filtervwapdist20:maxday2_gap15` |
| 9 | 30 | 15 | 660 | 9953 | 1.22188287 | 20.2% | 5698 | 5576 | -801 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.55:end1030:filtervwapdist20:maxday2_gap15` |
| 10 | 20 | 12 | 476 | 6462 | 1.22630805 | 20.4% | 1391 | 1727 | -777 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.5:end1330:filternofri_bar8:maxday1_gap0` |
| 11 | 25 | 15 | 540 | 8022 | 1.2262714 | 20.5% | 4472 | 4392 | -286 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.5:end1030:filtervwapdist20:maxday1_gap0` |
| 12 | 25 | 15 | 540 | 7802 | 1.22010946 | 20.7% | 4198 | 4118 | -363 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.55:end1030:filtervwapdist20:maxday1_gap0` |
| 13 | 25 | 15 | 592 | 7933 | 1.20095754 | 20.7% | 2262 | 2182 | -456 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1330:filterbar8:maxday1_gap0` |
| 14 | 25 | 15 | 669 | 9916 | 1.22390823 | 20.7% | 5529 | 5257 | -558 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.5:end1030:filtervwapdist20:maxday2_gap15` |
| 15 | 30 | 15 | 540 | 7350 | 1.20127612 | 20.8% | 3895 | 4065 | -445 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.5:end1030:filtervwapdist20:maxday1_gap0` |
| 16 | 25 | 15 | 671 | 9762 | 1.21985991 | 21.1% | 5422 | 5150 | -555 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.55:end1030:filtervwapdist20:maxday2_gap15` |
| 17 | 25 | 15 | 624 | 8427 | 1.20781751 | 21.1% | 3537 | 2561 | -292 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1030:filtervwapdist20:maxday2_gap15` |
| 18 | 20 | 12 | 473 | 6188 | 1.21764209 | 21.3% | 1117 | 1453 | -777 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.5:end1030:filternofri_bar8:maxday1_gap0` |
| 19 | 25 | 15 | 556 | 7698 | 1.21028765 | 21.5% | 4103 | 4023 | -299 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.5:end1330:filtervwapdist20:maxday1_gap0` |
| 20 | 20 | 12 | 701 | 9126 | 1.21531202 | 21.7% | 4102 | 4332 | -1100 | `mgc_lookback_breakout_refine_base:lb5:buf0:delta0:cl0.5:end1030:filternofri_bar8:maxday2_gap15` |
| 21 | 25 | 15 | 608 | 8063 | 1.20097208 | 22.2% | 2764 | 2436 | -769 | `mgc_lookback_breakout_refine_base:lb10:buf0.5:delta0:cl0.55:end1030:filtervwapdist20:maxday2_gap15` |
| 22 | 25 | 15 | 610 | 8038 | 1.20034895 | 22.3% | 3331 | 3003 | -772 | `mgc_lookback_breakout_refine_base:lb10:buf0.5:delta0:cl0.5:end1030:filtervwapdist20:maxday2_gap15` |
| 23 | 20 | 12 | 586 | 7469 | 1.21662461 | 22.9% | 2030 | 1970 | -366 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1030:filterbar8:maxday1_gap0` |
| 24 | 25 | 15 | 538 | 7383 | 1.21638335 | 23.6% | 1436 | 1204 | -529 | `mgc_lookback_breakout_refine_base:lb10:buf0.5:delta50:cl0.5:end1330:filtervwapdist20:maxday1_gap0` |
| 25 | 20 | 12 | 592 | 7057 | 1.20111716 | 24.2% | 1740 | 1680 | -366 | `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1330:filterbar8:maxday1_gap0` |

## Interpretation

The refinement found whether the high-frequency lookback lead can be improved without making it sparse. Rows that pass this lens still need slippage stress and chronological holdout testing before implementation.
