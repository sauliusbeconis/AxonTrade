# MGC Comprehensive Normal Search

Status: broad event-based MGC normal-profitability research. Not an ACSIL candidate yet.

## Source

- rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- unique dates: `717`
- instrument: `MGC`, one-minute Sierra order-flow export
- simulation: non-overlapping trades, configurable max trades/day, fixed target/stop exits, flatten by `16:30`

## Search Families

- `mgc_lookback_breakout_all` raw signals: `249777`
- `mgc_delta_impulse` raw signals: `43044`
- `mgc_or_breakout_all` raw signals: `42467`
- `mgc_vwap_fade` raw signals: `34201`
- `mgc_or_retest_all` raw signals: `16294`
- `mgc_vwap_pullback_all` raw signals: `12045`
- `mgc_vwap_reclaim` raw signals: `5409`

## Result

Best row by broad normal-profitability ranking:

| Metric | Value |
| --- | ---: |
| Strategy | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.5:end1030:maxday1:gap0` |
| Family | `mgc_lookback_breakout_all` |
| Target / stop points | `30 / 15` |
| Target / stop net | `$298 / $152` |
| Trades | `593` |
| Signal days | `593` |
| Net | `$7265` |
| Average trade | `$12.25126476` |
| Win rate | `47.6%` |
| Profit factor | `1.17876037` |
| Max trade-sequence drawdown | `$-1386` |
| Drawdown / net | `19.1%` |
| Latest-year trades | `130` |
| Latest-year net | `$2792` |
| Recent 120 trade-day net | `$2512` |
| Worst year | `$2138` |
| Worst quarter | `$-817` |

No row passed the broad first-pass lens.

## Top Rows

| Rank | Family | Target | Stop | Trades | Net | PF | DD/Net | Latest | Recent120 | Worst Q | Strategy |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | mgc_lookback_breakout_all | 30 | 15 | 593 | 7265 | 1.17876037 | 19.1% | 2792 | 2512 | -817 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.5:end1030:maxday1:gap0` |
| 2 | mgc_lookback_breakout_all | 30 | 15 | 593 | 7265 | 1.17876037 | 19.1% | 2792 | 2512 | -817 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.5:end1330:maxday1:gap0` |
| 3 | mgc_lookback_breakout_all | 30 | 15 | 593 | 6702 | 1.16403152 | 21.0% | 2342 | 2062 | -819 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.55:end1030:maxday1:gap0` |
| 4 | mgc_lookback_breakout_all | 30 | 15 | 593 | 6702 | 1.16403152 | 21.0% | 2342 | 2062 | -819 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.55:end1330:maxday1:gap0` |
| 5 | mgc_lookback_breakout_all | 30 | 15 | 912 | 10357 | 1.1658022 | 23.2% | 2649 | 3251 | -1256 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.5:end1330:maxday2:gap15` |
| 6 | mgc_vwap_pullback_all | 15 | 10 | 484 | 4025 | 1.17195711 | 24.3% | 1048 | 356 | -667 | `mgc_vwap_pullback_all:stretch8:pb2:delta0:cl0.55:end1330:maxday2:gap15` |
| 7 | mgc_lookback_breakout_all | 30 | 15 | 913 | 9685 | 1.15413384 | 24.8% | 2462 | 3064 | -1258 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.55:end1330:maxday2:gap15` |
| 8 | mgc_lookback_breakout_all | 30 | 15 | 772 | 9658 | 1.17450538 | 25.2% | 4188 | 4317 | -1078 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.5:end1030:maxday2:gap15` |
| 9 | mgc_lookback_breakout_all | 30 | 15 | 593 | 6216 | 1.15083718 | 25.2% | 2980 | 3150 | -1011 | `mgc_lookback_breakout_all:lb10:buf0.5:delta0:cl0.5:end1330:maxday1:gap0` |
| 10 | mgc_lookback_breakout_all | 20 | 12 | 593 | 6350 | 1.17934307 | 25.8% | 1298 | 918 | -366 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.5:end1030:maxday1:gap0` |
| 11 | mgc_lookback_breakout_all | 20 | 12 | 593 | 6350 | 1.17934307 | 25.8% | 1298 | 918 | -366 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.5:end1330:maxday1:gap0` |
| 12 | mgc_lookback_breakout_all | 30 | 15 | 593 | 5942 | 1.14363065 | 26.4% | 2530 | 2700 | -1063 | `mgc_lookback_breakout_all:lb10:buf0.5:delta0:cl0.55:end1330:maxday1:gap0` |
| 13 | mgc_lookback_breakout_all | 30 | 15 | 589 | 5920 | 1.14378704 | 26.5% | 2980 | 3150 | -992 | `mgc_lookback_breakout_all:lb10:buf0.5:delta0:cl0.5:end1030:maxday1:gap0` |
| 14 | mgc_lookback_breakout_all | 30 | 15 | 755 | 8145 | 1.14822566 | 26.5% | 3828 | 3957 | -819 | `mgc_lookback_breakout_all:lb10:buf0.5:delta0:cl0.55:end1030:maxday2:gap15` |
| 15 | mgc_lookback_breakout_all | 30 | 15 | 773 | 9075 | 1.16288545 | 26.9% | 3717 | 3846 | -1080 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.55:end1030:maxday2:gap15` |
| 16 | mgc_lookback_breakout_all | 20 | 12 | 593 | 4919 | 1.13589524 | 27.1% | 1298 | 1238 | -649 | `mgc_lookback_breakout_all:lb10:buf0.5:delta0:cl0.5:end1330:maxday1:gap0` |
| 17 | mgc_lookback_breakout_all | 30 | 15 | 589 | 5646 | 1.13660118 | 27.8% | 2530 | 2700 | -1044 | `mgc_lookback_breakout_all:lb10:buf0.5:delta0:cl0.55:end1030:maxday1:gap0` |
| 18 | mgc_lookback_breakout_all | 20 | 12 | 593 | 5885 | 1.16516517 | 28.0% | 978 | 598 | -366 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.55:end1030:maxday1:gap0` |
| 19 | mgc_lookback_breakout_all | 20 | 12 | 593 | 5885 | 1.16516517 | 28.0% | 978 | 598 | -366 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.55:end1330:maxday1:gap0` |
| 20 | mgc_lookback_breakout_all | 20 | 12 | 589 | 4663 | 1.12895821 | 28.5% | 1298 | 1238 | -649 | `mgc_lookback_breakout_all:lb10:buf0.5:delta0:cl0.5:end1030:maxday1:gap0` |
| 21 | mgc_lookback_breakout_all | 30 | 15 | 907 | 8239 | 1.13007989 | 29.9% | 1821 | 2271 | -1044 | `mgc_lookback_breakout_all:lb10:buf0.5:delta0:cl0.55:end1330:maxday2:gap15` |
| 22 | mgc_lookback_breakout_all | 20 | 12 | 863 | 7514 | 1.14074324 | 31.4% | 3162 | 2280 | -1044 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.5:end1030:maxday2:gap15` |
| 23 | mgc_lookback_breakout_all | 30 | 15 | 906 | 7514 | 1.1186034 | 32.8% | 2008 | 2458 | -992 | `mgc_lookback_breakout_all:lb10:buf0.5:delta0:cl0.5:end1330:maxday2:gap15` |
| 24 | mgc_lookback_breakout_all | 20 | 12 | 862 | 7080 | 1.13230924 | 33.4% | 2985 | 2103 | -1034 | `mgc_lookback_breakout_all:lb10:buf0:delta0:cl0.55:end1030:maxday2:gap15` |
| 25 | mgc_lookback_breakout_all | 30 | 15 | 756 | 7764 | 1.1410303 | 34.9% | 4147 | 4276 | -819 | `mgc_lookback_breakout_all:lb10:buf0.5:delta0:cl0.5:end1030:maxday2:gap15` |

## Interpretation

This pass directly addresses the sparse-sample problem by allowing repeated intraday signals and testing multiple families. A candidate still needs holdout/walk-forward validation and slippage stress before implementation.
