# MGC Final Validation

Status: final offline research battery for the frozen MGC Normal BreakEven bot on the current export.

## Scope

- source rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- unique active trading dates: `717`
- raw accepted setup candidates before one-trade-per-day sequencing: `2431`
- sequenced live-rule trades: `343`
- instrument: `MGC`, fixed `1 MGC` sizing
- base cost model: `$0.50/side` commission plus `1` total slippage tick per contract
- same-bar handling: stop first
- tests added here: extended slippage, wider rolling holdouts, period attribution, Monte Carlo trade-order risk, sensitivity digest, and context-exclusion review

## Implemented Rule

- strategy: `mgc_lb_be_sensitivity:lb10:buf0:cl0.45:end1030:mtf:delta125:breakeven:t25:s15:trig20`
- entry: `10` bar lookback breakout, `0` buffer, directional close-location `>= 0.45`, entry through `10:30`, Monday/Tuesday/Friday only, entry-bar absolute delta `<= 125`
- management: `25` point target, `15` point initial stop, move stop to breakeven after `+20` favorable points
- operational limits: one submitted trade per chart date, `$500` daily loss lock, `16:30` flatten, exact account whitelist for live routing

## Lead Scorecard

| Slip Ticks | Cost | Trades | /Wk | Net | Avg | PF | Win | Target | BE Stop | DD | Net/DD | Latest | Recent120 | Worst Q | Worst Month | Max Gap |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 343 | 2.86174017 | 13298 | 38.7696793 | 1.76320018 | 55.4% | 27.4% | 4.4% | -677 | 19.64254062 | 6046 | 5208 | -397 | -397 | 13 |
| 2 | 3 | 343 | 2.86174017 | 12955 | 37.7696793 | 1.73704273 | 55.4% | 27.4% | 4.4% | -686 | 18.88483965 | 5970 | 5138 | -402 | -402 | 13 |
| 4 | 5 | 343 | 2.86174017 | 12269 | 35.7696793 | 1.68603221 | 55.1% | 27.4% | 4.4% | -704 | 17.42755682 | 5818 | 4998 | -412 | -412 | 13 |
| 6 | 7 | 343 | 2.86174017 | 11583 | 33.7696793 | 1.63663845 | 54.2% | 27.4% | 4.4% | -722 | 16.04293629 | 5666 | 4858 | -422 | -422 | 13 |
| 8 | 9 | 343 | 2.86174017 | 10897 | 31.7696793 | 1.58861341 | 52.8% | 27.4% | 4.4% | -740 | 14.72567568 | 5514 | 4718 | -432 | -432 | 13 |
| 10 | 11 | 343 | 2.86174017 | 10211 | 29.7696793 | 1.54207146 | 52.5% | 27.4% | 4.4% | -784 | 13.02423469 | 5362 | 4578 | -442 | -442 | 13 |
| 12 | 13 | 343 | 2.86174017 | 9525 | 27.7696793 | 1.49705161 | 52.5% | 27.4% | 4.4% | -846 | 11.25886525 | 5210 | 4438 | -452 | -452 | 13 |

## Rolling Holdout Summary

Rows below use the wider holdout battery added in this pass. They are rolling trade-date windows, so aggregate net double-counts trades across windows and should be read as stability evidence, not a standalone P/L forecast.

| Slip | Config | Windows | Positive | Negative | No Trade | Net | Worst | Median |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 60x20 | 26 | 22 | 4 | 0 | 12994 | -142 | 394 |
| 1 | 90x30 | 16 | 15 | 1 | 0 | 12531 | -181 | 651 |
| 1 | 120x40 | 11 | 10 | 1 | 0 | 11996 | -141 | 1084 |
| 1 | 180x40 | 10 | 10 | 0 | 0 | 11757 | 399 | 1011.5 |
| 1 | 240x60 | 5 | 5 | 0 | 0 | 8780 | 704 | 1911 |
| 1 | 320x60 | 4 | 4 | 0 | 0 | 8631 | 1203 | 2115 |
| 6 | 60x20 | 26 | 21 | 5 | 0 | 11489 | -202 | 344 |
| 6 | 90x30 | 16 | 13 | 3 | 0 | 11146 | -271 | 561 |
| 6 | 120x40 | 11 | 10 | 1 | 0 | 10731 | -261 | 959 |
| 6 | 180x40 | 10 | 10 | 0 | 0 | 10612 | 279 | 904 |
| 6 | 240x60 | 5 | 5 | 0 | 0 | 7940 | 529 | 1741 |
| 6 | 320x60 | 4 | 4 | 0 | 0 | 7966 | 1033 | 1957.5 |

## Period Stress

| Slip | Worst Year | Worst Quarter | Worst Month |
| ---: | ---: | ---: | ---: |
| 1 | `2024=1605` | `2024Q1=-397` | `2024-03=-397` |
| 6 | `2024=985` | `2024Q1=-422` | `2024-03=-422` |

## Monte Carlo Trade-Order Risk

This shuffles the same trade outcomes to estimate path-risk sensitivity. It does not change the edge; it only changes trade order.

| Slip | Chron DD | Median DD | P95 DD | P99 DD | P(DD <= -500) | P(DD <= -750) | P(DD <= -1000) | P95 Loss Streak |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | -677 | -1131 | -1761 | -2137 | 100.0% | 97.9% | 70.6% | 9 |
| 6 | -722 | -1244 | -1959 | -2407 | 100.0% | 99.4% | 82.7% | 10 |

## Sensitivity Digest

- sensitivity rows available: `2700`
- rows passing the strict final lens: `197`
- final lens: at least `250` trades, positive stress net, stress PF `>= 1.50`, stress DD better than `-$1100`, at most one stress holdout loser, and stress worst holdout better than `-$800`
- implemented lead sensitivity rank: `16` of `2700` by the paired sensitivity sorter

| Label | Rank | Trades | Base Net | Base PF | Base DD | Stress Net | Stress PF | Stress DD | Stress Holdout | Stress Pos | Stress Worst |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| implemented risk-balanced lead | 16 | 343 | 13298 | 1.76320018 | -677 | 11583 | 1.63663845 | -722 | 29283 | 25/26 | -261 |
| higher-net growth monitor | 17 | 347 | 13449 | 1.75863042 | -816 | 11714 | 1.6329155 | -856 | 30147 | 25/26 | -261 |
| lowest-window-risk monitor | 2 | 348 | 12452 | 1.68421342 | -724 | 10712 | 1.56396757 | -810 | 26668 | 25/26 | -84 |
| old fixed-exit baseline | 317 | 338 | 10893 | 1.58479626 | -827 | 9203 | 1.47474852 | -872 | 24520 | 25/26 | -520 |

## Context Exclusion Review

The context-stress pass found weak buckets, but no simple exclusion improved full-sample net, PF, drawdown, and holdout quality together.

Best exclusion by the prior context sorter:

- `exclude_vwap_distance_2_5`: trades `342`, stress net `11225` (`-358` versus lead), stress PF `1.61479899`, stress holdout `29092`, stress worst window `216`

## Decision

MGC is now `100%` researched for the current one-minute order-flow export. This means the fixed-rule offline research budget is saturated for this dataset; it does not mean the bot is guaranteed to remain profitable.

The current `10:30 / cl0.45 / delta125 / 25-15 / BE+20` rule remains the live rule. The higher-net `10:45` row is only a monitor because it increases drawdown, while the lowest-window-risk `cl0.55 / delta150` row gives up too much net/PF to replace the live rule.

Next gate is operational, not more offline tuning: run the approved `1 MGC` controlled live setup, keep account-level risk small, collect forward sample, and revisit research only after a materially larger export or a live-vs-research behavior mismatch.

Current headline:

- base: `343` trades, `13298` net, `1.76320018` PF, `-677` DD, `2.86174017` trades/week
- six-tick stress: `11583` net, `1.63663845` PF, `-722` DD
