# MNQ Eval-Pass Wave Rider Walk-Forward

Status: walk-forward validation for the filtered lookback-breakout MNQ eval-pass family.

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique dates: `507`
- minimum training trades: `12`
- maximum quantity in selection pool: `12` MNQ

## Summary

| Config | Windows | Holdout Trades | Holdout Net | Avg | PF | Max DD | Positive Windows | Negative Windows | Signal Pass | 2-Day | Signal Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 120x40 | 9 | 56 | -9449 | -168.73214286 | 0.57606891 | -12228 | 4 | 5 | 12.5% | 10.7% | 76.8% |
| 180x40 | 8 | 39 | -6065 | -155.51282051 | 0.5859503 | -6065 | 2 | 5 | 30.8% | 15.4% | 66.7% |
| 240x60 | 4 | 17 | 2342 | 137.76470588 | 1.66009019 | -1638 | 3 | 0 | 70.6% | 17.6% | 5.9% |

## Locked Candidate Benchmarks

These rows do not reselect parameters in each window. They freeze a candidate upfront and evaluate only the same chronological holdout slices used above.

| Config | Candidate | Windows | Holdout Trades | Holdout Net | Avg | PF | Max DD | Positive Windows | Negative Windows | Signal Pass | 2-Day | Signal Fail |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 120x40 | `new_practical_10mnq_650_650` | 9 | 28 | 5225 | 186.60714286 | 1.89316239 | -1300 | 6 | 2 | 89.3% | 32.1% | 3.6% |
| 180x40 | `new_practical_10mnq_650_650` | 8 | 27 | 3275 | 121.2962963 | 1.50384615 | -1950 | 4 | 3 | 77.8% | 25.9% | 14.8% |
| 240x60 | `new_practical_10mnq_650_650` | 4 | 15 | 1975 | 131.66666667 | 1.60769231 | -1300 | 3 | 0 | 80.0% | 26.7% | 6.7% |
| 120x40 | `new_best_10mnq_625_650` | 9 | 28 | 5400 | 192.85714286 | 1.92307692 | -1350 | 6 | 3 | 89.3% | 35.7% | 3.6% |
| 180x40 | `new_best_10mnq_625_650` | 8 | 27 | 3500 | 129.62962963 | 1.53846154 | -1950 | 4 | 4 | 77.8% | 29.6% | 14.8% |
| 240x60 | `new_best_10mnq_625_650` | 4 | 15 | 2375 | 158.33333333 | 1.73076923 | -1350 | 3 | 1 | 80.0% | 33.3% | 6.7% |
| 120x40 | `new_practical_5mnq_650_650` | 9 | 33 | 8270 | 250.60606061 | 2.59038462 | -650 | 7 | 2 | 84.8% | 30.3% | 0.0% |
| 180x40 | `new_practical_5mnq_650_650` | 8 | 30 | 6110 | 203.66666667 | 2.175 | -650 | 5 | 2 | 73.3% | 20.0% | 0.0% |
| 240x60 | `new_practical_5mnq_650_650` | 4 | 18 | 5575 | 309.72222222 | 3.85897436 | -650 | 4 | 0 | 83.3% | 33.3% | 0.0% |
| 120x40 | `new_balanced_5mnq_625_650` | 9 | 33 | 8542.5 | 258.86363636 | 2.64278846 | -700 | 6 | 3 | 90.9% | 33.3% | 0.0% |
| 180x40 | `new_balanced_5mnq_625_650` | 8 | 30 | 6667.5 | 222.25 | 2.28221154 | -700 | 5 | 3 | 83.3% | 26.7% | 0.0% |
| 240x60 | `new_balanced_5mnq_625_650` | 4 | 18 | 5542.5 | 307.91666667 | 3.84230769 | -650 | 4 | 0 | 83.3% | 33.3% | 0.0% |
| 120x40 | `new_fast_12mnq_702_798` | 9 | 33 | 10464 | 317.09090909 | 2.63909774 | -1596 | 8 | 1 | 87.9% | 48.5% | 3.0% |
| 180x40 | `new_fast_12mnq_702_798` | 8 | 30 | 6858 | 228.6 | 1.95488722 | -1692 | 5 | 3 | 76.7% | 40.0% | 10.0% |
| 240x60 | `new_fast_12mnq_702_798` | 4 | 18 | 4434 | 246.33333333 | 2.1112782 | -1596 | 3 | 1 | 77.8% | 38.9% | 5.6% |
| 120x40 | `old_balanced_5mnq_650_800` | 9 | 52 | 5277.5 | 101.49038462 | 1.40110203 | -4810 | 6 | 3 | 71.2% | 19.2% | 21.2% |
| 180x40 | `old_balanced_5mnq_650_800` | 8 | 40 | 1172.5 | 29.3125 | 1.09936441 | -4810 | 5 | 3 | 62.5% | 17.5% | 25.0% |
| 240x60 | `old_balanced_5mnq_650_800` | 4 | 27 | 5900 | 218.51851852 | 2.15178136 | -950 | 3 | 1 | 88.9% | 22.2% | 0.0% |
| 120x40 | `old_balanced_5mnq_625_800` | 9 | 52 | 4652.5 | 89.47115385 | 1.35360061 | -4910 | 6 | 3 | 71.2% | 19.2% | 21.2% |
| 180x40 | `old_balanced_5mnq_625_800` | 8 | 40 | 722.5 | 18.0625 | 1.06122881 | -4910 | 5 | 3 | 62.5% | 17.5% | 25.0% |
| 240x60 | `old_balanced_5mnq_625_800` | 4 | 27 | 5525 | 204.62962963 | 2.07857491 | -975 | 3 | 1 | 88.9% | 22.2% | 0.0% |
| 120x40 | `old_fast_12mnq_702_798` | 9 | 55 | 7248 | 131.78181818 | 1.45413534 | -3990 | 6 | 3 | 72.7% | 32.7% | 16.4% |
| 180x40 | `old_fast_12mnq_702_798` | 8 | 47 | 3132 | 66.63829787 | 1.20656905 | -3990 | 6 | 2 | 68.1% | 27.7% | 27.7% |
| 240x60 | `old_fast_12mnq_702_798` | 4 | 29 | 1656 | 57.10344828 | 1.17293233 | -3990 | 3 | 1 | 65.5% | 27.6% | 20.7% |
| 120x40 | `old_lower_stop_10mnq_650_650` | 9 | 55 | 5260 | 95.63636364 | 1.36783217 | -3250 | 6 | 1 | 65.5% | 25.5% | 21.8% |
| 180x40 | `old_lower_stop_10mnq_650_650` | 8 | 47 | 2660 | 56.59574468 | 1.20461538 | -3250 | 6 | 2 | 66.0% | 21.3% | 31.9% |
| 240x60 | `old_lower_stop_10mnq_650_650` | 4 | 29 | 1975 | 68.10344828 | 1.25320513 | -3250 | 3 | 1 | 65.5% | 20.7% | 20.7% |

## Selected Candidate Counts

| Config | Count | Qty | Target | Stop | Strategy |
| --- | ---: | ---: | ---: | ---: | --- |
| 120x40 | 1 | 12 | 702 | 798 | `lookback_breakout:lb20:buf0:delta0:cl0.55:end1230:skipfri1:filterbarrange24_75` |
| 120x40 | 1 | 10 | 700 | 650 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` |
| 120x40 | 1 | 6 | 702 | 798 | `lookback_breakout:lb20:buf0:delta0:cl0.55:end1230:skipfri1:filterbarrange24_75` |
| 120x40 | 1 | 12 | 702 | 648 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 120x40 | 1 | 12 | 702 | 798 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 120x40 | 1 | 6 | 651 | 498 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterbarrange24_75_vwapdist103_45` |
| 120x40 | 1 | 5 | 700 | 800 | `lookback_breakout:lb40:buf0:delta0:cl0.55:end1230:skipfri1:filterbarrange24_75_vwapdist103_45` |
| 120x40 | 1 | 8 | 700 | 648 | `lookback_breakout:lb10:buf0:delta0:cl0.55:end1230:skipfri0:filterabsdelta1172` |
| 180x40 | 1 | 5 | 700 | 650 | `lookback_breakout:lb10:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 180x40 | 1 | 5 | 650 | 800 | `lookback_breakout:lb20:buf0:delta0:cl0.55:end1230:skipfri0:filterabsdelta1172_barrange24_75` |
| 180x40 | 1 | 12 | 702 | 798 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 180x40 | 1 | 12 | 630 | 798 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 180x40 | 1 | 5 | 625 | 650 | `lookback_breakout:lb40:buf0:delta0:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 180x40 | 1 | 6 | 627 | 648 | `lookback_breakout:lb10:buf0:delta0:cl0.55:end1230:skipfri1:filterabsdelta1000_lbmove103_75` |
| 180x40 | 1 | 5 | 700 | 500 | `lookback_breakout:lb10:buf0:delta0:cl0.55:end1230:skipfri1:filterabsdelta1172_barrange24_75` |
| 180x40 | 1 | 8 | 628 | 800 | `lookback_breakout:lb20:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1172_lbmove103_75` |
| 240x60 | 1 | 10 | 650 | 650 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` |
| 240x60 | 1 | 12 | 630 | 798 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` |
| 240x60 | 1 | 5 | 700 | 800 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 240x60 | 1 | 5 | 625 | 650 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |

## Interpretation

This is a chronological selection test. Each window selects the best candidate on the training dates, then evaluates that exact candidate on the following holdout dates.

The adaptive selection result is currently weaker than the locked candidate benchmarks. That means the next MNQ eval-pass path should freeze one candidate family instead of changing parameters window by window.

A deployable eval-pass bot would need positive holdout behavior across multiple window sizes, reasonable selected-candidate stability, replay mechanics, and live chart data validation.
