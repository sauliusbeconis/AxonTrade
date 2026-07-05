# MNQ Top-Runner Validation

Status: frozen validation of the strongest MNQ normal-profitability runner leads.

## Objective

This skips the breakeven-frequency path and tests a different family: lookback-breakout runners with fixed target/stop exits. The goal is PF, net profit, and drawdown quality, not eval-pass geometry.

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique dates: `507`
- quantity: fixed `2 MNQ`
- cost model: `$0.50/side` commission plus variable total slippage ticks per contract
- same-bar handling: stop first
- holdout configs: `120x40`, `180x40`, `240x60`

## Frozen Candidates

| Candidate | Label | Filter | Target / Stop |
| --- | --- | --- | ---: |
| `mnq_top_runner_lb20_cl90_t160_s70` | high PF | `time_1000_1100__clmin_gte0p9` | 160 / 70 |
| `mnq_top_runner_lb20_cl90_t120_s70` | lower DD | `time_1000_1100__clmin_gte0p9` | 120 / 70 |
| `mnq_top_runner_lb20_cl80_t160_s70` | higher sample | `time_1000_1100__clmin_gte0p8` | 160 / 70 |

## Base Slippage

| Candidate | Label | Trades | /Wk | Net | PF | Win | Target Hit | Latest | Worst Q | DD | Net/DD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mnq_top_runner_lb20_cl90_t160_s70` | high PF | 87 | 0.84937238 | 11772 | 2.15039578 | 54.0% | 29.9% | 7089 | -1005 | -1854 | 6.34951456 |
| `mnq_top_runner_lb20_cl90_t120_s70` | lower DD | 87 | 0.84937238 | 10135 | 2.08002984 | 57.5% | 40.2% | 5548 | -1005 | -1146 | 8.84380454 |
| `mnq_top_runner_lb20_cl80_t160_s70` | higher sample | 158 | 1.54253835 | 17334 | 1.85939514 | 51.3% | 27.8% | 9197 | -325 | -1811 | 9.57150745 |

## Slippage Stress

| Candidate | Slippage Ticks | Net | PF | Latest | Worst Q | DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `mnq_top_runner_lb20_cl80_t160_s70` | 1 | 17334 | 1.85939514 | 9197 | -325 | -1811 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 2 | 17176 | 1.84832321 | 9151 | -339 | -1827 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 4 | 16860 | 1.82643008 | 9059 | -367 | -1859 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 6 | 16544 | 1.804865 | 8967 | -395 | -1891 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 1 | 10135 | 2.08002984 | 5548 | -1005 | -1146 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 2 | 10048 | 2.06655344 | 5521 | -1011 | -1151 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 4 | 9874 | 2.03991575 | 5467 | -1023 | -1161 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 6 | 9700 | 2.01369004 | 5413 | -1035 | -1171 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 1 | 11772 | 2.15039578 | 7089 | -1005 | -1854 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 2 | 11685 | 2.13744768 | 7062 | -1011 | -1863 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 4 | 11511 | 2.11185164 | 7008 | -1023 | -1881 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 6 | 11337 | 2.08664814 | 6954 | -1035 | -1899 |

## Rolling Holdout

| Candidate | Config | Windows | Positive | Negative | No Trade | Holdout Net | Worst | Median |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mnq_top_runner_lb20_cl80_t160_s70` | 120x40 | 9 | 6 | 3 | 0 | 8193 | -807 | 724 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 180x40 | 8 | 7 | 1 | 0 | 12322 | -158 | 1287.5 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 240x60 | 4 | 4 | 0 | 0 | 8055 | 1124 | 1900.5 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 120x40 | 9 | 6 | 3 | 0 | 5427 | -779 | 592 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 180x40 | 8 | 6 | 2 | 0 | 8340 | -217 | 1041.5 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 240x60 | 4 | 4 | 0 | 0 | 5850 | 444 | 1122.5 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 120x40 | 9 | 7 | 2 | 0 | 5687 | -779 | 637 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 180x40 | 8 | 7 | 1 | 0 | 9240 | -217 | 711 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 240x60 | 4 | 4 | 0 | 0 | 6550 | 626 | 1251 |

## Period Breakdown: `mnq_top_runner_lb20_cl90_t160_s70`

| Period | Trades | Net | PF | Max DD |
| --- | ---: | ---: | ---: | ---: |
| quarter:2024Q3 | 11 | 1864 | 2.31731449 | -283 |
| quarter:2024Q4 | 6 | 682 | 2.92112676 | -355 |
| quarter:2025Q1 | 6 | -1005 | 0.11219081 | -1062 |
| quarter:2025Q2 | 7 | 450 | 1.3975265 | -849 |
| quarter:2025Q3 | 14 | 1145 | 1.83333333 | -853 |
| quarter:2025Q4 | 16 | 1547 | 1.78091873 | -765 |
| quarter:2026Q1 | 11 | 836 | 1.48831776 | -1146 |
| quarter:2026Q2 | 15 | 5616 | 5.96113074 | -283 |
| quarter:2026Q3 | 1 | 637 | 999 | 0 |
| year:2024 | 17 | 2546 | 2.43841808 | -355 |
| year:2025 | 43 | 2137 | 1.38031678 | -1854 |
| year:2026 | 27 | 7089 | 3.49261603 | -1146 |

## Interpretation

This validation promotes the lookback-breakout runner family to serious replay-candidate status if it keeps positive slippage stress and mostly positive rolling holdouts. It is not implemented as ACSIL and is not approved for live routing yet.

Compare against the current MNQ VWAP/delta live lead: about `186` trades, `$9584.50` net, `2.09` PF, and `-$976` drawdown. The runner candidate can beat net/PF, but its drawdown is larger, so replay quality and operational fit matter before build.
