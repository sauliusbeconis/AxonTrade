# MGC Lookback Breakout Slippage Stress

Status: slippage stress for the refined MGC lookback-breakout normal lead.

## Source

- rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- filtered signals: `6690`
- lead: `mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1030:filterbar8:maxday1_gap0`
- policy: max `1` trade/day, no re-entry

## Stress Rows

| Target | Stop | Slip Ticks | Target Net | Stop Net | Trades | Net | PF | DD/Net | Latest | Recent120 | Worst Q |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 15 | 1 | 248 | 152 | 586 | 8445 | 1.21812687 | 15.8% | 2622 | 2542 | -456 |
| 25 | 15 | 2 | 247 | 153 | 586 | 7859 | 1.20142502 | 17.3% | 2498 | 2428 | -518 |
| 25 | 15 | 3 | 246 | 154 | 586 | 7273 | 1.18497889 | 19.1% | 2374 | 2314 | -584 |
| 25 | 15 | 4 | 245 | 155 | 586 | 6687 | 1.16877839 | 21.3% | 2250 | 2200 | -650 |
| 25 | 15 | 5 | 244 | 156 | 586 | 6101 | 1.152823 | 23.8% | 2126 | 2086 | -716 |
| 25 | 15 | 6 | 243 | 157 | 586 | 5515 | 1.13710038 | 27.4% | 2002 | 1972 | -782 |
| 30 | 15 | 1 | 298 | 152 | 586 | 8287 | 1.20992502 | 18.5% | 3822 | 3542 | -599 |
| 30 | 15 | 2 | 297 | 153 | 586 | 7701 | 1.19358001 | 20.6% | 3698 | 3428 | -665 |
| 30 | 15 | 3 | 296 | 154 | 586 | 7115 | 1.17748453 | 23.0% | 3574 | 3314 | -731 |
| 30 | 15 | 4 | 295 | 155 | 586 | 6529 | 1.16162891 | 25.9% | 3450 | 3200 | -797 |
| 30 | 15 | 5 | 294 | 156 | 586 | 5943 | 1.14601248 | 29.3% | 3326 | 3086 | -863 |
| 30 | 15 | 6 | 293 | 157 | 586 | 5357 | 1.13062349 | 33.5% | 3202 | 2972 | -929 |

## Interpretation

This keeps the same entry and one-trade-per-day policy while increasing total slippage ticks per contract. A build candidate should remain positive in latest-year and recent windows after this stress, then pass chronological holdout testing.
