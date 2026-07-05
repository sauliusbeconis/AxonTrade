# MGC Normal Bot Slippage Stress

Status: stress test for the refined MGC VWAP pullback normal-profitability lead.

## Source

- rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- filtered signals: `116`
- lead: `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:none`
- fixed exits: `30` point target, `15` point stop

## Stress Rows

| Qty | Slip Ticks | Target Net | Stop Net | Net | PF | DD/Net | Latest | Recent120 | Worst Q |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 298 | 152 | 3880 | 1.49916377 | 20.4% | 1608 | 1468 | -177 |
| 1 | 2 | 297 | 153 | 3764 | 1.48059244 | 21.5% | 1568 | 1433 | -191 |
| 1 | 3 | 296 | 154 | 3648 | 1.46229882 | 22.8% | 1528 | 1398 | -205 |
| 1 | 4 | 295 | 155 | 3532 | 1.44427673 | 24.1% | 1488 | 1363 | -219 |
| 1 | 5 | 294 | 156 | 3416 | 1.42652016 | 25.5% | 1448 | 1328 | -233 |
| 1 | 6 | 293 | 157 | 3300 | 1.4090233 | 27.0% | 1408 | 1293 | -247 |
| 3 | 1 | 894 | 456 | 11640 | 1.49916377 | 20.4% | 4824 | 4404 | -531 |
| 3 | 2 | 891 | 459 | 11292 | 1.48059244 | 21.5% | 4704 | 4299 | -573 |
| 3 | 3 | 888 | 462 | 10944 | 1.46229882 | 22.8% | 4584 | 4194 | -615 |
| 3 | 4 | 885 | 465 | 10596 | 1.44427673 | 24.1% | 4464 | 4089 | -657 |
| 3 | 5 | 882 | 468 | 10248 | 1.42652016 | 25.5% | 4344 | 3984 | -699 |
| 3 | 6 | 879 | 471 | 9900 | 1.4090233 | 27.0% | 4224 | 3879 | -741 |
| 5 | 1 | 1490 | 760 | 19400 | 1.49916377 | 20.4% | 8040 | 7340 | -885 |
| 5 | 2 | 1485 | 765 | 18820 | 1.48059244 | 21.5% | 7840 | 7165 | -955 |
| 5 | 3 | 1480 | 770 | 18240 | 1.46229882 | 22.8% | 7640 | 6990 | -1025 |
| 5 | 4 | 1475 | 775 | 17660 | 1.44427673 | 24.1% | 7440 | 6815 | -1095 |
| 5 | 5 | 1470 | 780 | 17080 | 1.42652016 | 25.5% | 7240 | 6640 | -1165 |
| 5 | 6 | 1465 | 785 | 16500 | 1.4090233 | 27.0% | 7040 | 6465 | -1235 |

## Interpretation

The stress keeps the same target/stop points and increases transaction cost. Quantity scales the dollars, so the important checks are profit factor, latest-year net, recent 120-trade-day net, and drawdown-to-net stability.
