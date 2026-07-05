# MNQ Top-Runner Deep Validation

Status: final offline research battery for the MNQ Top Runner family on the current export.

## Scope

- source rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique trading dates: `507`
- instrument: `MNQ`, fixed `2 MNQ` sizing
- base cost model: `$0.50/side` commission plus `1` total slippage tick per contract
- same-bar handling: stop first
- tests added here: extended slippage, wider rolling holdouts, period attribution, Monte Carlo trade-order risk, parameter-neighborhood stability, and candidate overlap

## Frozen Candidate Scorecard

| Candidate | Label | Trades | /Wk | Net | PF | Win | Target | DD | Net/DD | Latest | Worst Q | Worst Month | Max Gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mnq_top_runner_lb20_cl90_t120_s70` | lower DD | 87 | 0.84937238 | 10135 | 2.08002984 | 57.5% | 40.2% | -1146 | 8.84380454 | 5548 | -1005 | -669 | 48 |
| `mnq_top_runner_lb20_cl80_t160_s70` | higher sample | 158 | 1.54253835 | 17334 | 1.85939514 | 51.3% | 27.8% | -1811 | 9.57150745 | 9197 | -325 | -856 | 20 |
| `mnq_top_runner_lb20_cl90_t160_s70` | high PF | 87 | 0.84937238 | 11772 | 2.15039578 | 54.0% | 29.9% | -1854 | 6.34951456 | 7089 | -1005 | -509 | 48 |

## Extended Slippage Stress

| Candidate | 1 tick Net/PF | 6 tick Net/PF | 12 tick Net/PF |
| --- | ---: | ---: | ---: |
| `mnq_top_runner_lb20_cl90_t160_s70` | 11772 / 2.15039578 | 11337 / 2.08664814 | 10815 / 2.0133046 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 10135 / 2.08002984 | 9700 / 2.01369004 | 9178 / 1.93739148 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 17334 / 1.85939514 | 16544 / 1.804865 | 15596 / 1.74206595 |

## Rolling Holdout Summary

| Candidate | Config | Windows | Positive | Negative | No Trade | Net | Worst | Median |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mnq_top_runner_lb20_cl80_t160_s70` | 120x40 | 9 | 6 | 3 | 0 | 8193 | -807 | 724 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 180x40 | 8 | 7 | 1 | 0 | 12322 | -158 | 1287.5 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 240x60 | 4 | 4 | 0 | 0 | 8055 | 1124 | 1900.5 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 320x60 | 3 | 3 | 0 | 0 | 9379 | 1173 | 2051 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 60x20 | 22 | 15 | 7 | 0 | 13716 | -792 | 412.5 |
| `mnq_top_runner_lb20_cl80_t160_s70` | 90x30 | 13 | 10 | 3 | 0 | 9169 | -877 | 836 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 120x40 | 9 | 6 | 3 | 0 | 5427 | -779 | 592 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 180x40 | 8 | 6 | 2 | 0 | 8340 | -217 | 1041.5 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 240x60 | 4 | 4 | 0 | 0 | 5850 | 444 | 1122.5 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 320x60 | 3 | 3 | 0 | 0 | 6373 | 956 | 1496 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 60x20 | 22 | 14 | 7 | 1 | 8017 | -669 | 367.5 |
| `mnq_top_runner_lb20_cl90_t120_s70` | 90x30 | 13 | 9 | 3 | 1 | 6134 | -849 | 582 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 120x40 | 9 | 7 | 2 | 0 | 5687 | -779 | 637 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 180x40 | 8 | 7 | 1 | 0 | 9240 | -217 | 711 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 240x60 | 4 | 4 | 0 | 0 | 6550 | 626 | 1251 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 320x60 | 3 | 3 | 0 | 0 | 7474 | 836 | 1376 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 60x20 | 22 | 14 | 7 | 1 | 8917 | -509 | 341.5 |
| `mnq_top_runner_lb20_cl90_t160_s70` | 90x30 | 13 | 9 | 3 | 1 | 6394 | -849 | 420 |

## Monte Carlo Trade-Order Risk

This shuffles the same trade outcomes to estimate path-risk sensitivity. It does not change the edge; it only changes trade order.

| Candidate | Chron DD | Median DD | P95 DD | P99 DD | P(DD <= -1000) | P(DD <= -1500) | P(DD <= -2000) | P95 Loss Streak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mnq_top_runner_lb20_cl90_t160_s70` | -1854 | -1497 | -2462 | -3018 | 95.9% | 49.9% | 15.4% | 8 |
| `mnq_top_runner_lb20_cl90_t120_s70` | -1146 | -1415 | -2238 | -2734 | 88.8% | 37.5% | 9.5% | 7 |
| `mnq_top_runner_lb20_cl80_t160_s70` | -1811 | -2034 | -3254 | -3925 | 100.0% | 90.0% | 52.2% | 9 |

## Parameter-Neighborhood Stability

- neighborhood rows tested: `1728`
- accepted by the deep lens: `0`
- accepted lens: at least `70` trades, positive net/latest year, PF `>= 1.70`, DD better than `-$2500`, and worst quarter better than `-$1500`
- live default row rank in neighborhood: `205` of `1728`
- live default row accepted by deep lens: `no`

| Rank | Strategy | Target / Stop | Trades | Net | PF | DD | Latest | Worst Q | Accepted |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `mnq_top_runner_deep_neighborhood:lb30:delta600:cl0.95:end1100` | 160 / 70 | 7 | 2987 | 11.55477032 | -283 | 1274 | 185 | no |
| 2 | `mnq_top_runner_deep_neighborhood:lb30:delta800:cl0.95:end1100` | 160 / 70 | 7 | 2987 | 11.55477032 | -283 | 1274 | 185 | no |
| 3 | `mnq_top_runner_deep_neighborhood:lb30:delta600:cl0.95:end1100` | 140 / 70 | 7 | 2687 | 10.49469965 | -283 | 1114 | 185 | no |
| 4 | `mnq_top_runner_deep_neighborhood:lb30:delta800:cl0.95:end1100` | 140 / 70 | 7 | 2687 | 10.49469965 | -283 | 1114 | 185 | no |
| 5 | `mnq_top_runner_deep_neighborhood:lb30:delta600:cl0.95:end1100` | 160 / 80 | 7 | 2947 | 10.12383901 | -323 | 1274 | 185 | no |
| 6 | `mnq_top_runner_deep_neighborhood:lb30:delta800:cl0.95:end1100` | 160 / 80 | 7 | 2947 | 10.12383901 | -323 | 1274 | 185 | no |
| 7 | `mnq_top_runner_deep_neighborhood:lb30:delta600:cl0.95:end1100` | 140 / 80 | 7 | 2647 | 9.19504644 | -323 | 1114 | 185 | no |
| 8 | `mnq_top_runner_deep_neighborhood:lb30:delta800:cl0.95:end1100` | 140 / 80 | 7 | 2647 | 9.19504644 | -323 | 1114 | 185 | no |
| 9 | `mnq_top_runner_deep_neighborhood:lb30:delta600:cl0.95:end1100` | 120 / 70 | 7 | 2287 | 9.08127208 | -283 | 954 | 185 | no |
| 10 | `mnq_top_runner_deep_neighborhood:lb30:delta800:cl0.95:end1100` | 120 / 70 | 7 | 2287 | 9.08127208 | -283 | 954 | 185 | no |
| 11 | `mnq_top_runner_deep_neighborhood:lb30:delta600:cl0.95:end1100` | 120 / 80 | 7 | 2247 | 7.95665635 | -323 | 954 | 154 | no |
| 12 | `mnq_top_runner_deep_neighborhood:lb30:delta800:cl0.95:end1100` | 120 / 80 | 7 | 2247 | 7.95665635 | -323 | 954 | 154 | no |
| 13 | `mnq_top_runner_deep_neighborhood:lb30:delta600:cl0.95:end1100` | 100 / 70 | 7 | 1887 | 7.66784452 | -283 | 794 | 114 | no |
| 14 | `mnq_top_runner_deep_neighborhood:lb30:delta800:cl0.95:end1100` | 100 / 70 | 7 | 1887 | 7.66784452 | -283 | 794 | 114 | no |
| 15 | `mnq_top_runner_deep_neighborhood:lb30:delta600:cl0.95:end1100` | 100 / 80 | 7 | 1847 | 6.71826625 | -323 | 794 | 74 | no |

## Implementation Alignment Finding

The original frozen candidate is a two-stage rule: a broad raw `10:00-12:30` lookback-breakout stream using close-location `0.65`, followed by a final `10:00-11:00` directional close-location filter. The raw stream applies the one-hour spacing before the final filter.

A direct strict ACSIL interpretation using only `10:00-11:00` and close-location `0.9` is not equivalent and tested worse.

| Rule | Trades | Net | PF | DD | Latest | Worst Q |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen filtered lower-DD rule | 87 | 10135 | 2.08002984 | -1146 | 5548 | -1005 |
| Direct strict rule, 120 / 70 | 120 | 8635 | 1.57398298 | -1712 | 6479 | -1691 |
| Direct strict rule, 160 / 70 | 120 | 10312 | 1.63748764 | -2257 | 7580 | -1691 |
| Direct strict CL 0.8 rule, 160 / 70 | 177 | 14604 | 1.59815687 | -2130 | 8709 | -728 |

## Candidate Overlap

| Left | Right | Left Trades | Right Trades | Overlap | Left Rate | Right Rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `mnq_top_runner_lb20_cl80_t160_s70` | `mnq_top_runner_lb20_cl90_t120_s70` | 158 | 87 | 87 | 55.1% | 100.0% |
| `mnq_top_runner_lb20_cl80_t160_s70` | `mnq_top_runner_lb20_cl90_t160_s70` | 158 | 87 | 87 | 55.1% | 100.0% |
| `mnq_top_runner_lb20_cl90_t120_s70` | `mnq_top_runner_lb20_cl90_t160_s70` | 87 | 87 | 87 | 100.0% | 100.0% |

## Worst Periods

| Candidate | Worst Year | Worst Quarter | Worst Month |
| --- | ---: | ---: | ---: |
| `mnq_top_runner_lb20_cl90_t160_s70` | `2025=2137` | `2025Q1=-1005` | `2026-01=-509` |
| `mnq_top_runner_lb20_cl90_t120_s70` | `2024=2129` | `2025Q1=-1005` | `2026-01=-669` |
| `mnq_top_runner_lb20_cl80_t160_s70` | `2025=3437` | `2025Q1=-325` | `2025-09=-856` |

## Decision

Offline research on the current MNQ export is complete enough to mark the Top Runner family as `100%` researched for this dataset. That means the available static-rule research budget is exhausted; it does not mean the bot has a 100% chance of making money.

The lower-DD `120 / 70` live build remains the correct first live-staging variant. The high-PF `160 / 70` variant has higher net/PF, but its drawdown and Monte Carlo path risk are materially larger. The `cl >= 0.8` higher-sample sibling is a research backup, not the current live default.

The ACSIL implementation must use the filtered frozen rule before inheriting the stronger research stats. After that alignment, the next gates are operational: fresh replay/mechanics validation, controlled live staging, forward sample, and aggregate account-risk tooling before account scaling.
