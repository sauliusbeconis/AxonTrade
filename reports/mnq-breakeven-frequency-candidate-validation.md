# MNQ Breakeven-Frequency Candidate Validation

Status: validation pass for the current MNQ breakeven-frequency candidate.

## Candidate

- signal: `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1230:skipfri1:maxday1:space30`
- filter: `short_only__vwapdist_lte120` (short entries only; directional VWAP distance <= 120)
- management: first leg exits at target one; runner stop moves to breakeven; conservative same-bar handling
- risk geometry: `30 / 50 / 120` points
- filtered trades: `128`
- source rows: `67300`
- source dates: `2024-07-15` through `2026-07-02`

## Base Slippage

| Version | Qty | Split | Trades/Wk | Net | PF | Latest-Year Net | Worst Quarter | Max DD |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| growth | 4 | 3+1 | 1.24965132 | 7603.5 | 1.58524477 | 2236 | -638 | -1624 |
| balanced | 3 | 2+1 | 1.24965132 | 5235.5 | 1.53730501 | 1632 | -598.5 | -1249.5 |
| low-risk | 2 | 1+1 | 1.24965132 | 2867.5 | 1.44142549 | 1028 | -586 | -1108 |

## Slippage Stress

| Candidate | Slippage Ticks | Net | PF | Latest-Year Net | Worst Quarter | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `mnq_be_freq_short_vwap_q2_1p1_30_50_120` | 1 | 2867.5 | 1.44142549 | 1028 | -586 | -1108 |
| `mnq_be_freq_short_vwap_q2_1p1_30_50_120` | 2 | 2739.5 | 1.4196538 | 1004 | -608 | -1144 |
| `mnq_be_freq_short_vwap_q2_1p1_30_50_120` | 4 | 2483.5 | 1.37674454 | 956 | -652 | -1216 |
| `mnq_be_freq_short_vwap_q2_1p1_30_50_120` | 6 | 2227.5 | 1.33466046 | 908 | -696 | -1288 |
| `mnq_be_freq_short_vwap_q3_2p1_30_50_120` | 1 | 5235.5 | 1.53730501 | 1632 | -598.5 | -1249.5 |
| `mnq_be_freq_short_vwap_q3_2p1_30_50_120` | 2 | 5043.5 | 1.51506332 | 1596 | -618 | -1296 |
| `mnq_be_freq_short_vwap_q3_2p1_30_50_120` | 4 | 4659.5 | 1.47122775 | 1524 | -678 | -1404 |
| `mnq_be_freq_short_vwap_q3_2p1_30_50_120` | 6 | 4275.5 | 1.42823518 | 1452 | -744 | -1512 |
| `mnq_be_freq_short_vwap_q4_3p1_30_50_120` | 1 | 7603.5 | 1.58524477 | 2236 | -638 | -1624 |
| `mnq_be_freq_short_vwap_q4_3p1_30_50_120` | 2 | 7347.5 | 1.56276808 | 2188 | -664 | -1632 |
| `mnq_be_freq_short_vwap_q4_3p1_30_50_120` | 4 | 6835.5 | 1.51846936 | 2092 | -716 | -1648 |
| `mnq_be_freq_short_vwap_q4_3p1_30_50_120` | 6 | 6323.5 | 1.47502254 | 1996 | -792 | -1736 |

## Period Breakdown

### `mnq_be_freq_short_vwap_q4_3p1_30_50_120`

| Period | Trades | Net | PF | Max DD |
| --- | ---: | ---: | ---: | ---: |
| year:2024 | 34 | 3396 | 2.39408867 | -812 |
| year:2025 | 70 | 1971.5 | 1.23123387 | -1624 |
| year:2026 | 24 | 2236 | 2.10147783 | -1044 |
| quarter:2024Q3 | 18 | 2932 | 4.61083744 | -406 |
| quarter:2024Q4 | 16 | 464 | 1.28571429 | -812 |
| quarter:2025Q1 | 13 | -638 | 0.68571429 | -1450 |
| quarter:2025Q2 | 13 | 1002 | 1.8226601 | -1044 |
| quarter:2025Q3 | 22 | 2179.5 | 2.07364532 | -1624 |
| quarter:2025Q4 | 22 | -572 | 0.82389163 | -1160 |
| quarter:2026Q1 | 15 | 2170 | 3.67241379 | -406 |
| quarter:2026Q2 | 9 | 66 | 1.05418719 | -1044 |

### `mnq_be_freq_short_vwap_q3_2p1_30_50_120`

| Period | Trades | Net | PF | Max DD |
| --- | ---: | ---: | ---: | ---: |
| year:2024 | 34 | 2367 | 2.2955665 | -609 |
| year:2025 | 70 | 1236.5 | 1.1933693 | -1218 |
| year:2026 | 24 | 1632 | 2.07192118 | -798 |
| quarter:2024Q3 | 18 | 2199 | 4.61083744 | -304.5 |
| quarter:2024Q4 | 16 | 168 | 1.13793103 | -609 |
| quarter:2025Q1 | 13 | -598.5 | 0.60689655 | -1102.5 |
| quarter:2025Q2 | 13 | 721.5 | 1.78981938 | -798 |
| quarter:2025Q3 | 22 | 1692.5 | 2.11165846 | -1218 |
| quarter:2025Q4 | 22 | -579 | 0.76231527 | -945 |
| quarter:2026Q1 | 15 | 1612.5 | 3.64778325 | -304.5 |
| quarter:2026Q2 | 9 | 19.5 | 1.02134647 | -798 |

### `mnq_be_freq_short_vwap_q2_1p1_30_50_120`

| Period | Trades | Net | PF | Max DD |
| --- | ---: | ---: | ---: | ---: |
| year:2024 | 34 | 1338 | 2.09852217 | -406 |
| year:2025 | 70 | 501.5 | 1.11764016 | -930 |
| year:2026 | 24 | 1028 | 2.01280788 | -552 |
| quarter:2024Q3 | 18 | 1466 | 4.61083744 | -203 |
| quarter:2024Q4 | 16 | -128 | 0.84236453 | -406 |
| quarter:2025Q1 | 13 | -559 | 0.44926108 | -755 |
| quarter:2025Q2 | 13 | 441 | 1.72413793 | -552 |
| quarter:2025Q3 | 22 | 1205.5 | 2.18768473 | -812 |
| quarter:2025Q4 | 22 | -586 | 0.63916256 | -762 |
| quarter:2026Q1 | 15 | 1055 | 3.59852217 | -203 |
| quarter:2026Q2 | 9 | -27 | 0.95566502 | -552 |

## Interpretation

This is the first non-rejected breakeven-frequency candidate. The `4 MNQ` version has the best growth, while the `3 MNQ` version is the more practical risk version because drawdown and single-trade loss are lower.

It is still research, not a bot build instruction. Next gates are walk-forward/frozen holdout review, replay/mechanics validation, and only then an ACSIL implementation decision.
