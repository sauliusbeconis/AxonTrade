# MNQ Eval Live Final Validation

Status: final offline research battery for `AxonTrade MNQ Eval Live Bot` on the current MNQ export.

## Scope

- source rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique trading dates: `507`
- raw accepted setup candidates after schedule/spacing/context: `186`
- instrument: `MNQ`, `1+1 MNQ` scaled exit
- base cost model: `$0.50/side` commission plus `1` total slippage tick per contract
- same-bar handling: stop first
- implementation reality tested here: `independent` reproduces the old paper audit; `live_sequenced` rejects entries while the previous trade is still open, matching the ACSIL position/working-order gate.

## Implemented Rule

- strategy: `mnq_vwap_delta_local_fade_80pt_400d_cl0.4_nofri_no11_15_exit25_140_40_initial`
- entry: VWAP/delta exhaustion fade, `80` point VWAP extension, bar delta `400`, close-location `0.4`
- schedule: `09:45-15:45`, no Friday entries, no `11:00` or `15:00` exchange-hour entries
- pacing: `900` seconds between raw candidates, max `20` raw candidates per day
- exits: first target `25`, initial stop `140`, runner target `40`, runner stop remains initial

## Scorecard

| Mode | Slip | Trades | /Wk | Net | Avg | PF | Win | Runner Target | Stop | DD | Net/DD | Latest | Worst Year | Worst Q | Worst Month | Max Gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `independent` | 1 | 186 | 1.81337047 | 9584.5 | 51.52956989 | 2.09212625 | 80.1% | 76.3% | 8.1% | -976 | 9.82018443 | 2857.5 | 1676.5 | -309 | -394.5 | 25 |
| `independent` | 3 | 186 | 1.81337047 | 9212.5 | 49.52956989 | 2.04096045 | 80.1% | 76.3% | 8.1% | -982 | 9.38136456 | 2749.5 | 1590.5 | -315 | -408.5 | 25 |
| `independent` | 6 | 186 | 1.81337047 | 8654.5 | 46.52956989 | 1.96541915 | 79.0% | 76.3% | 8.1% | -991 | 8.73309788 | 2587.5 | 1461.5 | -324 | -429.5 | 25 |
| `independent` | 12 | 186 | 1.81337047 | 7538.5 | 40.52956989 | 1.81953579 | 79.0% | 76.3% | 8.1% | -1009 | 7.47125867 | 2263.5 | 1203.5 | -342 | -471.5 | 25 |
| `live_sequenced` | 1 | 166 | 1.6183844 | 8897 | 53.59638554 | 2.12059953 | 82.5% | 78.3% | 8.4% | -924.5 | 9.62358031 | 2715 | 914.5 | -309 | -521.5 | 25 |
| `live_sequenced` | 3 | 166 | 1.6183844 | 8565 | 51.59638554 | 2.07095967 | 82.5% | 78.3% | 8.4% | -932.5 | 9.1849866 | 2617 | 840.5 | -315 | -533.5 | 25 |
| `live_sequenced` | 6 | 166 | 1.6183844 | 8067 | 48.59638554 | 1.99740356 | 81.3% | 78.3% | 8.4% | -944.5 | 8.541027 | 2470 | 729.5 | -324 | -551.5 | 25 |
| `live_sequenced` | 12 | 166 | 1.6183844 | 7071 | 42.59638554 | 1.85460479 | 81.3% | 78.3% | 8.4% | -968.5 | 7.3009809 | 2176 | 507.5 | -342 | -587.5 | 25 |

## Live-Sequenced Holdouts

| Slip | Config | Windows | Positive | Negative | No Trade | Net | Worst | Median |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 20x5 | 97 | 60 | 20 | 17 | 8700 | -563 | 127 |
| 1 | 40x10 | 46 | 36 | 8 | 2 | 8822 | -898 | 194 |
| 1 | 60x10 | 44 | 35 | 7 | 2 | 8379 | -898 | 194 |
| 1 | 90x15 | 27 | 24 | 3 | 0 | 8541.5 | -436 | 265.5 |
| 1 | 120x20 | 19 | 18 | 1 | 0 | 8545.5 | -114 | 402 |
| 1 | 180x30 | 10 | 9 | 1 | 0 | 6367 | -139 | 584 |
| 6 | 20x5 | 97 | 59 | 21 | 17 | 7930 | -568 | 122 |
| 6 | 40x10 | 46 | 35 | 9 | 2 | 8082 | -908 | 171.5 |
| 6 | 60x10 | 44 | 34 | 8 | 2 | 7684 | -908 | 171.5 |
| 6 | 90x15 | 27 | 24 | 3 | 0 | 7896.5 | -446 | 244 |
| 6 | 120x20 | 19 | 18 | 1 | 0 | 7905.5 | -129 | 372 |
| 6 | 180x30 | 10 | 8 | 2 | 0 | 5887 | -174 | 551.5 |

## Period Stress

| Mode | Slip | Worst Year | Worst Quarter | Worst Month |
| --- | ---: | ---: | ---: | ---: |
| `independent` | 1 | `2024=1676.5` | `2026Q3=-309` | `2024-10=-394.5` |
| `live_sequenced` | 1 | `2024=914.5` | `2026Q3=-309` | `2024-10=-521.5` |
| `live_sequenced` | 6 | `2024=729.5` | `2026Q3=-324` | `2024-10=-551.5` |

## Monte Carlo Trade-Order Risk

This shuffles the same trade outcomes to estimate path-risk sensitivity. It does not change the edge; it only changes trade order.

| Mode | Slip | Chron DD | Median DD | P95 DD | P99 DD | P(DD <= -1000) | P(DD <= -1500) | P95 Loss Streak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `independent` | 1 | -976 | -1210.5 | -1931 | -2367 | 78.4% | 22.4% | 4 |
| `live_sequenced` | 1 | -924.5 | -1193 | -1931.5 | -2365 | 76.8% | 20.7% | 4 |
| `live_sequenced` | 6 | -944.5 | -1242.5 | -1979 | -2412 | 82.5% | 24.8% | 4 |

## Neighborhood Search

- rows tested: `15552`
- accepted by the live-sequenced final lens: `0`
- final lens: at least `80` live-sequenced trades, net above current live-sequenced net, PF `>= 1.60`, DD better than `-$1200`, positive latest/worst year, worst quarter better than `-$800`, at least `8` fixed `40x10` windows, at most one negative `40x10` window, and worst `40x10` window better than `-$500`.
- current implemented row rank in the live-sequenced neighborhood: `304` of `15552`

| Rank | Strategy | Trades | Net | PF | DD | Latest | Worst Year | Worst Q | WF40 | WF40 Worst | Decision |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `mnq_eval_live_final:vwap80:delta300:cl0.425:space900:t25:s150:r45:initial` | 227 | 11010.5 | 1.89519899 | -1213.5 | 3158.5 | 834 | -86.5 | 34/46 | -801 | reject: drawdown worse than -1200 |
| 2 | `mnq_eval_live_final:vwap80:delta400:cl0.425:space900:t25:s150:r45:initial` | 186 | 10866 | 2.23963265 | -1277.5 | 3015.5 | 1154.5 | -192 | 37/46 | -938 | reject: drawdown worse than -1200 |
| 3 | `mnq_eval_live_final:vwap80:delta300:cl0.425:space900:t25:s150:r50:initial` | 226 | 10748.5 | 1.80636933 | -1347.5 | 2538.5 | 822 | -415 | 32/46 | -791 | reject: drawdown worse than -1200 |
| 4 | `mnq_eval_live_final:vwap80:delta300:cl0.425:space900:t25:s150:r40:initial` | 231 | 10677.5 | 1.86597729 | -1350 | 3240.5 | 470.5 | -166.5 | 34/46 | -811 | reject: drawdown worse than -1200 |
| 5 | `mnq_eval_live_final:vwap75:delta300:cl0.425:space900:t25:s150:r45:initial` | 244 | 10641.5 | 1.74377075 | -1306 | 2817.5 | 1106 | -55 | 34/46 | -676 | reject: drawdown worse than -1200 |
| 6 | `mnq_eval_live_final:vwap80:delta300:cl0.425:space1200:t25:s150:r45:initial` | 224 | 10599.5 | 1.861783 | -1213.5 | 2884.5 | 834 | -86.5 | 34/46 | -801 | reject: drawdown worse than -1200 |
| 7 | `mnq_eval_live_final:vwap80:delta400:cl0.425:space1200:t25:s150:r45:initial` | 184 | 10592 | 2.20837374 | -1277.5 | 2878.5 | 1154.5 | -192 | 37/46 | -938 | reject: drawdown worse than -1200 |
| 8 | `mnq_eval_live_final:vwap80:delta300:cl0.425:space900:t25:s140:r45:initial` | 227 | 10576.5 | 1.83963799 | -1174 | 3338 | 585 | -396.5 | 33/46 | -761 | reject: holdout instability |
| 9 | `mnq_eval_live_final:vwap75:delta300:cl0.425:space900:t25:s150:r40:initial` | 248 | 10568.5 | 1.75033724 | -1487 | 3249.5 | 712.5 | -95 | 35/46 | -692 | reject: drawdown worse than -1200 |
| 10 | `mnq_eval_live_final:vwap75:delta400:cl0.425:space900:t25:s150:r45:initial` | 198 | 10518.5 | 2.03523449 | -1015.5 | 2860.5 | 1426.5 | -192 | 36/46 | -813 | reject: holdout instability |
| 11 | `mnq_eval_live_final:vwap80:delta300:cl0.425:space900:t25:s140:r40:initial` | 231 | 10514 | 1.85020014 | -1325 | 3466 | 241.5 | -466.5 | 33/46 | -771 | reject: drawdown worse than -1200 |
| 12 | `mnq_eval_live_final:vwap75:delta300:cl0.425:space900:t25:s140:r40:initial` | 248 | 10485 | 1.74671509 | -1407 | 3475 | 483.5 | -171 | 34/46 | -646 | reject: drawdown worse than -1200 |
| 13 | `mnq_eval_live_final:vwap80:delta300:cl0.425:space900:t25:s140:r50:initial` | 226 | 10384.5 | 1.76658177 | -1222 | 2778 | 573 | -355 | 32/46 | -751 | reject: drawdown worse than -1200 |
| 14 | `mnq_eval_live_final:vwap80:delta400:cl0.425:space900:t25:s140:r45:initial` | 186 | 10338 | 2.12903402 | -1237.5 | 3181 | 905.5 | -152 | 36/46 | -898 | reject: drawdown worse than -1200 |
| 15 | `mnq_eval_live_final:vwap80:delta400:cl0.425:space900:t25:s150:r50:initial` | 185 | 10334 | 2.05497422 | -1277.5 | 2255.5 | 1102.5 | -562 | 34/46 | -938 | reject: drawdown worse than -1200 |
| 16 | `mnq_eval_live_final:vwap75:delta300:cl0.425:space900:t25:s150:r50:initial` | 242 | 10326 | 1.67325183 | -1644.5 | 2054 | 1124 | -415 | 32/46 | -666 | reject: drawdown worse than -1200 |
| 17 | `mnq_eval_live_final:vwap80:delta400:cl0.425:space900:t25:s150:r40:initial` | 187 | 10316.5 | 2.17768265 | -1277.5 | 3146.5 | 671.5 | -222 | 36/46 | -938 | reject: drawdown worse than -1200 |
| 18 | `mnq_eval_live_final:vwap80:delta300:cl0.425:space1200:t25:s150:r50:initial` | 223 | 10307.5 | 1.77328482 | -1347.5 | 2244.5 | 822 | -415 | 32/46 | -791 | reject: drawdown worse than -1200 |
| 19 | `mnq_eval_live_final:vwap75:delta300:cl0.425:space900:t25:s140:r45:initial` | 244 | 10307.5 | 1.71064153 | -1286 | 3017 | 857 | -15 | 33/46 | -636 | reject: drawdown worse than -1200 |
| 20 | `mnq_eval_live_final:vwap75:delta400:cl0.425:space900:t25:s150:r40:initial` | 199 | 10269 | 2.03706322 | -1025.5 | 3351.5 | 913.5 | -222 | 36/46 | -813 | reject: holdout instability |

## Decision

No neighborhood row replaces the current implemented rule under the live-sequenced final lens. The MNQ Eval Live VWAP/delta family is `100%` offline researched for the current export, with the caveat that live-sequenced stats are the real executable baseline.

Key finding:

- Legacy independent audit: `186` trades, `9584.5` net, `2.09212625` PF, `-976` DD.
- Live-sequenced executable path: `166` trades, `8897` net, `2.12059953` PF, `-924.5` DD.
- Six-tick live-sequenced stress: `8067` net, `1.99740356` PF, `-944.5` DD.

Next gate is monitored forward evidence, not more static tuning or default changes.
