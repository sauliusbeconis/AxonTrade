# MNQ Eval-Pass Wave Rider Cadence Scan

Status: exploratory scan for faster signal cadence; no accepted implementation
candidate yet.

## Goal

The previous best MNQ eval-pass lead is clean but sparse, averaging about one
signal every `11.7` trading days. This scan asked whether we can accept a
multi-day pass path in exchange for much faster signal frequency.

## Current Sparse Lead

`lookback_breakout_deep:lb40:buf2.5:delta600:cl0.5:start1000:end1230:skipfri0:filterabs1000`

- risk: `12 MNQ`, about `$726 / $750`
- signals: `43` across `507` trading days
- average signal wait: `11.8` trading days
- signal-start pass: `90.7%`
- two-day pass: `51.2%`
- signal-start fail: `2.3%`

## Fast Cadence Lead Found

`cadence:lb10:buf0:delta300:cl0.55:start1000:end1230:skipfri0:filternone`

- risk: `4 MNQ`, about `$350 / $650`
- signals: `505` across `507` trading days
- average signal wait: `1.0` trading day
- median pass time: `9` calendar days, `7` traded days
- calendar-start pass: `44.6%`
- calendar-start fail: `22.5%`
- timeout: `32.9%`
- full net: `$23630`
- latest-year net: `$1090`
- worst quarter: `-$2328`
- max trade-sequence drawdown: `-$5050`
- max consecutive losses: `6`

## Breakdown

Year:

| Year | Trades | Net | Wins | Losses |
| ---: | ---: | ---: | ---: | ---: |
| 2024 | 121 | 7668 | 86 | 35 |
| 2025 | 255 | 14872 | 178 | 77 |
| 2026 | 129 | 1090 | 84 | 45 |

Quarter:

| Quarter | Trades | Net | Wins | Losses |
| --- | ---: | ---: | ---: | ---: |
| 2024 Q3 | 56 | 4910 | 41 | 15 |
| 2024 Q4 | 65 | 2758 | 45 | 20 |
| 2025 Q1 | 62 | 6308 | 47 | 15 |
| 2025 Q2 | 64 | -134 | 41 | 23 |
| 2025 Q3 | 65 | 1544 | 42 | 23 |
| 2025 Q4 | 64 | 7154 | 48 | 16 |
| 2026 Q1 | 63 | -2328 | 38 | 25 |
| 2026 Q2 | 64 | 3718 | 45 | 19 |

Weekday:

| Day | Trades | Net | Wins | Losses |
| --- | ---: | ---: | ---: | ---: |
| Mon | 102 | 7404 | 73 | 29 |
| Tue | 103 | 5104 | 72 | 31 |
| Wed | 101 | 11350 | 77 | 24 |
| Thu | 99 | 378 | 64 | 35 |
| Fri | 100 | -606 | 62 | 38 |

## Interpretation

The fast-cadence idea works mechanically as a research concept: it can produce a
clear signal almost every trading day and pass in roughly one to two weeks when
it works.

It is not clean enough to promote:

- eval-fail rate is about `22.5%`;
- max trade-sequence drawdown is `-$5050`, far outside the eval drawdown;
- `2026 Q1` is a bad regime at `-$2328`;
- six consecutive losses is unacceptable without an additional regime gate.

The useful next research direction is not simply “trade more often.” It is a
hybrid cadence model:

- preserve the clean sparse lead as the A+ setup;
- search for a faster B setup with explicit regime vetoes;
- reject daily-frequency variants unless fail rate drops below about `10-12%`
  and quarter-level behavior improves materially.
