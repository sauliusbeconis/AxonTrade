# MGC Lookback Context Stress

Status: context/session stress diagnostics on the current MGC lookback break-even lead.

## Source

- rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- evaluated trades: `343`
- holdout windows: `120x40, 180x40, 240x60`
- minimum exclusion trades: `250`

## Frozen Lead

- strategy: `mgc_lb_be_sensitivity:lb10:buf0:cl0.45:end1030:mtf:delta125:breakeven:t25:s15:trig20`
- entry: `10` bar lookback breakout, `0` buffer, directional close-location `>= 0.45`, entry through `10:30`, Monday/Tuesday/Friday only, entry bar absolute delta `<= 125`
- management: `25` point target, `15` point initial stop, move stop to breakeven after `+20` points

| Cost | Trades | Net | Avg | PF | DD | Holdout Net | Holdout PF | Pos/Windows | Worst Window |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| base | 343 | 13298 | 38.7696793 | 1.76320018 | -677 | 32533 | 1.97453794 | 25/26 | -141 |
| stress | 343 | 11583 | 33.7696793 | 1.63663845 | -722 | 29283 | 1.84081316 | 25/26 | -261 |

## Weakest Context Buckets

| Rank | Section | Bucket | Trades | Base Avg | Base PF | Stress Avg | Stress PF | Stress DD |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | vwap_distance | VWAP distance 2-5 | 57 | 3.94736842 | 1.06910319 | -1.05263158 | 0.98235294 | -1062 |
| 2 | quarter | 2024 Q2 | 39 | 8.20512821 | 1.17362995 | 3.20512821 | 1.06466632 | -678 |
| 3 | entry_abs_delta | abs delta 50-75 | 96 | 9.35416667 | 1.15125484 | 4.35416667 | 1.06768135 | -763 |
| 4 | year | 2024 | 124 | 12.94354839 | 1.28538407 | 7.94354839 | 1.16706242 | -703 |
| 5 | quarter | 2025 Q1 | 38 | 13.57894737 | 1.24951644 | 8.57894737 | 1.15085609 | -545 |
| 6 | quarter | 2024 Q4 | 40 | 17.375 | 1.41993958 | 12.375 | 1.28513825 | -541 |
| 7 | weekday | Tuesday | 115 | 17.60869565 | 1.29788173 | 12.60869565 | 1.20468662 | -823 |
| 8 | day_range | day range 0-10 | 173 | 19.07514451 | 1.39332539 | 14.07514451 | 1.27717701 | -935 |
| 9 | quarter | 2024 Q3 | 40 | 24.675 | 1.57753072 | 19.675 | 1.4396648 | -529 |
| 10 | bar_range | bar range 0-3 | 258 | 28.14341085 | 1.56660164 | 23.14341085 | 1.4459298 | -867 |
| 11 | directional_close_location | directional close-location 0.65-0.75 | 57 | 28.77192982 | 1.53489889 | 23.77192982 | 1.42264504 | -789 |
| 12 | entry_time | 08:20-09:00 | 258 | 32.57364341 | 1.61253644 | 27.57364341 | 1.49689181 | -784 |
| 13 | weekday | Friday | 112 | 37.36607143 | 1.69426012 | 32.36607143 | 1.57603687 | -851 |
| 14 | entry_abs_delta | abs delta 25-50 | 80 | 37.5875 | 1.76030341 | 32.5875 | 1.62955808 | -840 |
| 15 | direction | long | 208 | 37.97596154 | 1.7733503 | 32.97596154 | 1.64325237 | -1189 |
| 16 | directional_close_location | directional close-location 0.75-1 | 253 | 39.05533597 | 1.76312944 | 34.05533597 | 1.63808043 | -900 |
| 17 | year | 2025 | 143 | 39.48951049 | 1.72101634 | 34.48951049 | 1.60441176 | -722 |
| 18 | direction | short | 135 | 39.99259259 | 1.74882108 | 34.99259259 | 1.62727393 | -952 |
| 19 | vwap_distance | VWAP distance >=10 | 154 | 40.19480519 | 1.70221214 | 35.19480519 | 1.58938669 | -530 |
| 20 | entry_abs_delta | abs delta 0-25 | 41 | 41.02439024 | 2.03126916 | 36.02439024 | 1.86072261 | -326 |

## Strongest Context Buckets

| Rank | Section | Bucket | Trades | Base Avg | Base PF | Stress Avg | Stress PF | Stress DD |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | bar_range | bar range 5-8 | 22 | 91.54545455 | 2.88576779 | 86.54545455 | 2.71069182 | -314 |
| 2 | quarter | 2026 Q2 | 37 | 86.59459459 | 2.7489083 | 81.59459459 | 2.5789749 | -699 |
| 3 | year | 2026 | 76 | 79.55263158 | 2.52368952 | 74.55263158 | 2.36926051 | -699 |
| 4 | quarter | 2026 Q1 | 38 | 78.78947368 | 2.50907258 | 73.78947368 | 2.35524408 | -542 |
| 5 | bar_range | bar range 3-5 | 53 | 68.56603774 | 2.23984988 | 63.56603774 | 2.10242147 | -542 |
| 6 | day_range | day range 20-35 | 47 | 64.10638298 | 2.27238176 | 59.10638298 | 2.11655949 | -321 |
| 7 | entry_abs_delta | abs delta 100-125 | 60 | 61.68333333 | 2.34288824 | 56.68333333 | 2.18049288 | -449 |
| 8 | weekday | Monday | 116 | 61.10344828 | 2.5415398 | 56.10344828 | 2.35104837 | -576 |
| 9 | entry_abs_delta | abs delta 75-100 | 66 | 60.75757576 | 2.27503975 | 55.75757576 | 2.12195122 | -362 |
| 10 | vwap_distance | VWAP distance 5-10 | 75 | 55.93333333 | 2.35585003 | 50.93333333 | 2.18119975 | -471 |
| 11 | quarter | 2025 Q3 | 38 | 53.86842105 | 2.2148368 | 48.86842105 | 2.05811966 | -338 |
| 12 | vwap_distance | VWAP distance 0-2 | 57 | 47.15789474 | 2.18990704 | 42.15789474 | 2.01649746 | -724 |
| 13 | quarter | 2025 Q2 | 38 | 46.63157895 | 1.78790574 | 41.63157895 | 1.67635742 | -668 |
| 14 | quarter | 2025 Q4 | 29 | 45.24137931 | 1.71693989 | 40.24137931 | 1.61259843 | -471 |
| 15 | day_range | day range 10-20 | 110 | 44.52727273 | 1.75238095 | 39.52727273 | 1.64414815 | -1289 |
| 16 | entry_time | 09:00-09:30 | 67 | 42.74626866 | 1.85187388 | 37.74626866 | 1.71846591 | -760 |
| 17 | entry_abs_delta | abs delta 0-25 | 41 | 41.02439024 | 2.03126916 | 36.02439024 | 1.86072261 | -326 |
| 18 | vwap_distance | VWAP distance >=10 | 154 | 40.19480519 | 1.70221214 | 35.19480519 | 1.58938669 | -530 |
| 19 | direction | short | 135 | 39.99259259 | 1.74882108 | 34.99259259 | 1.62727393 | -952 |
| 20 | year | 2025 | 143 | 39.48951049 | 1.72101634 | 34.48951049 | 1.60441176 | -722 |

## Live-Rule Exclusion Tests

| Rank | Exclusion | Trades | Base Net | Base Delta | Base PF | Base DD | Stress Net | Stress Delta | Stress PF | Stress DD | Stress Holdout | Pos/Windows | Worst Window |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | exclude VWAP distance 2-5 | 342 | 12935 | -363 | 1.73969234 | -792 | 11225 | -358 | 1.61479899 | -893 | 29092 | 26/26 | 216 |
| 2 | exclude 09:00-09:30 | 334 | 11229 | -2069 | 1.63866454 | -760 | 9559 | -2024 | 1.52084128 | -812 | 24719 | 26/26 | 31 |
| 3 | exclude bar range >=8 | 340 | 12791 | -507 | 1.74344667 | -677 | 11091 | -492 | 1.61702364 | -722 | 27553 | 25/26 | -160 |
| 4 | exclude directional close-location 0.45-0.55 | 342 | 12889 | -409 | 1.73765238 | -713 | 11179 | -404 | 1.61278299 | -810 | 29013 | 25/26 | -170 |
| 5 | exclude bar range 5-8 | 339 | 12034 | -1264 | 1.6905773 | -677 | 10339 | -1244 | 1.56804571 | -773 | 25617 | 25/26 | -661 |
| 6 | exclude VWAP distance 5-10 | 332 | 11508 | -1790 | 1.67658299 | -1125 | 9848 | -1735 | 1.55344498 | -1275 | 26934 | 25/26 | -261 |
| 7 | exclude 09:30-10:00 | 339 | 11600 | -1698 | 1.65337389 | -677 | 9905 | -1678 | 1.53442322 | -736 | 24453 | 25/26 | -322 |
| 8 | exclude day range >=35 | 330 | 11211 | -2087 | 1.64923558 | -816 | 9561 | -2022 | 1.53048882 | -856 | 23703 | 25/26 | -261 |
| 9 | exclude abs delta 100-125 | 338 | 11472 | -1826 | 1.64747714 | -827 | 9782 | -1801 | 1.52901411 | -872 | 25526 | 25/26 | -505 |
| 10 | exclude day range 0-10 | 321 | 13496 | 198 | 1.8854481 | -610 | 11891 | 308 | 1.74383836 | -718 | 28246 | 24/26 | -475 |
| 11 | exclude abs delta 50-75 | 337 | 13414 | 116 | 1.82269243 | -774 | 11729 | 146 | 1.6870314 | -869 | 28326 | 24/26 | -725 |
| 12 | exclude 10:00-10:30 | 340 | 12831 | -467 | 1.73639807 | -677 | 11131 | -452 | 1.6117951 | -722 | 28004 | 24/26 | -261 |
| 13 | exclude directional close-location 0.55-0.65 | 343 | 12141 | -1157 | 1.68119845 | -677 | 10426 | -1157 | 1.56014613 | -773 | 26304 | 24/26 | -661 |
| 14 | exclude abs delta 75-100 | 335 | 11519 | -1779 | 1.65620371 | -795 | 9844 | -1739 | 1.53727759 | -825 | 23119 | 24/26 | -268 |
| 15 | exclude day range 20-35 | 316 | 10784 | -2514 | 1.65600097 | -876 | 9204 | -2379 | 1.53686421 | -941 | 22716 | 24/26 | -661 |
| 16 | exclude abs delta 25-50 | 340 | 10464 | -2834 | 1.57799381 | -894 | 8764 | -2819 | 1.46363011 | -979 | 21772 | 24/26 | -261 |
| 17 | exclude abs delta 0-25 | 343 | 10438 | -2860 | 1.5494841 | -829 | 8723 | -2860 | 1.44042209 | -976 | 23695 | 24/26 | -621 |
| 18 | exclude directional close-location 0.65-0.75 | 341 | 12437 | -861 | 1.71255873 | -807 | 10732 | -851 | 1.58876454 | -887 | 25931 | 23/26 | -603 |
| 19 | exclude day range 10-20 | 305 | 9457 | -3841 | 1.59058265 | -962 | 7932 | -3651 | 1.47403335 | -1002 | 20196 | 23/26 | -547 |
| 20 | exclude bar range 3-5 | 334 | 9777 | -3521 | 1.53767048 | -1178 | 8107 | -3476 | 1.4274942 | -1248 | 19046 | 23/26 | -380 |
| 21 | exclude directional close-location 0.75-1 | 294 | 3949 | -9349 | 1.22607053 | -2053 | 2479 | -9104 | 1.13579097 | -2593 | 11748 | 22/26 | -791 |
| 22 | exclude 08:20-09:00 | 335 | 7402 | -5896 | 1.39582888 | -1588 | 5727 | -5856 | 1.29282135 | -2043 | 14233 | 21/26 | -1069 |
| 23 | exclude short | 273 | 6717 | -6581 | 1.45342244 | -1418 | 5352 | -6231 | 1.34598229 | -1630 | 14331 | 20/26 | -1353 |
| 24 | exclude VWAP distance 0-2 | 342 | 8949 | -4349 | 1.45831199 | -2131 | 7239 | -4344 | 1.35535811 | -2571 | 18655 | 19/26 | -1453 |

## Full-Sample Improvement Traps

| Rank | Exclusion | Trades | Base Delta | Stress Delta | Stress PF | Stress Holdout | Pos/Windows | Worst Window |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | exclude day range 0-10 | 321 | 198 | 308 | 1.74383836 | 28246 | 24/26 | -475 |
| 2 | exclude abs delta 50-75 | 337 | 116 | 146 | 1.6870314 | 28326 | 24/26 | -725 |

## Decision

Keep the frozen `10:30` break-even lead. No simple live-rule exclusion improved full-sample net, PF, drawdown, and holdout quality together.

The strongest contexts are Monday, 2026, wider entry-bar ranges, day range above `20`, and entry-bar absolute delta above `75`. The weakest contexts are VWAP distance `2-5`, entry-bar absolute delta `50-75`, Tuesday, early `2024`, and day range below `10`.

The top-ranked exclusion improves holdout cleanliness but still reduces full-sample net, so it is not a replacement:

- `exclude_vwap_distance_2_5`: stress net `11225` (`-358` versus lead), stress PF `1.61479899`, stress holdout `29092` with `26/26` positive windows.

Full-sample improvement rows are treated as traps unless they also preserve holdout quality. In this pass, the stress-net improvement rows lost holdout windows and worsened worst-window loss, so they are monitoring notes only.
