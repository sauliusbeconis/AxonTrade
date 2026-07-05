# MGC Lookback Breakout Walk-Forward

Status: chronological validation for the refined MGC lookback-breakout normal lead.

## Source

- rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- unique dates: `717`
- candidates: `1008`
- windows: `120x40, 180x40, 240x60`
- minimum training trades for adaptive selection: `25`
- instrument: `MGC`, one-minute Sierra order-flow export

## Adaptive Walk-Forward Summary

Each window selects the best nearby lookback candidate on the training dates, then scores that exact candidate on the following unseen holdout dates.

| Config | Windows | Trades | Net | Avg | PF | Max DD | Pos Windows | Neg Windows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 120x40 | 11 | 482 | 910 | 1.8879668 | 1.0289477 | -1778 | 6 | 5 |
| 180x40 | 10 | 392 | -1761 | -4.49234694 | 0.94070707 | -3499 | 5 | 5 |
| 240x60 | 5 | 258 | -1226 | -4.75193798 | 0.94119622 | -2969 | 2 | 3 |

## Frozen Current Lead

These rows freeze the current refined lead upfront and evaluate the same rolling holdout slices.

| Config | Trades | Net | Avg | PF | Max DD | Pos Windows | Neg Windows | Worst Window |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 120x40 | 433 | 6542 | 15.10854503 | 1.2223204 | -1337 | 8 | 3 | -423 |
| 180x40 | 393 | 6590 | 16.76844784 | 1.23656532 | -1337 | 8 | 2 | -209 |
| 240x60 | 293 | 3865 | 13.19112628 | 1.17563392 | -1337 | 5 | 0 | 203 |

## Frozen Leaderboard

This ranks nearby frozen candidates on the same holdout slices. It is a robustness screen, not permission to keep optimizing on holdout data.

| Rank | Target | Stop | Trades | Net | Min Config Net | Min PF | Max DD | Pos/Windows | Worst Window | Strategy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 25 | 15 | 1039 | 19159 | 5299 | 1.24526269 | -1561 | 23/26 | -594 | `mgc_lookback_breakout_walk_base:lb10:buf0:delta0:cl0.5:end1030:filterabsdelta100:maxday1_gap0` |
| 2 | 25 | 15 | 1234 | 17735 | 5085 | 1.17169794 | -1808 | 23/26 | -986 | `mgc_lookback_breakout_walk_base:lb5:buf0:delta0:cl0.55:end1030:filterstart0900_nofri:maxday2_gap15` |
| 3 | 25 | 15 | 1036 | 18461 | 5071 | 1.23639064 | -1472 | 23/26 | -493 | `mgc_lookback_breakout_walk_base:lb10:buf0:delta0:cl0.55:end1030:filterabsdelta100:maxday1_gap0` |
| 4 | 25 | 15 | 912 | 14638 | 4089 | 1.18839889 | -1809 | 23/26 | -949 | `mgc_lookback_breakout_walk_base:lb10:buf0:delta0:cl0.55:end1030:filterstart0900_nofri:maxday1_gap0` |
| 5 | 25 | 15 | 915 | 14398 | 4064 | 1.18711325 | -1809 | 23/26 | -949 | `mgc_lookback_breakout_walk_base:lb10:buf0:delta0:cl0.5:end1030:filterstart0900_nofri:maxday1_gap0` |
| 6 | 25 | 15 | 915 | 14398 | 4064 | 1.18711325 | -1809 | 23/26 | -949 | `mgc_lookback_breakout_walk_base:lb10:buf0:delta0:cl0.5:end1330:filterstart0900_nofri:maxday1_gap0` |
| 7 | 25 | 15 | 915 | 14443 | 4024 | 1.18506199 | -1809 | 23/26 | -949 | `mgc_lookback_breakout_walk_base:lb10:buf0:delta0:cl0.55:end1330:filterstart0900_nofri:maxday1_gap0` |
| 8 | 25 | 15 | 1901 | 21804 | 6735 | 1.14538267 | -2849 | 22/26 | -1850 | `mgc_lookback_breakout_walk_base:lb10:buf0.5:delta0:cl0.55:end1330:filternone:maxday2_gap15` |
| 9 | 20 | 12 | 1419 | 23158 | 6057 | 1.24447046 | -1978 | 22/26 | -1092 | `mgc_lookback_breakout_walk_base:lb5:buf0:delta0:cl0.5:end1030:filternofri_bar8:maxday2_gap15` |
| 10 | 25 | 15 | 1186 | 21981 | 5894 | 1.24627305 | -1680 | 22/26 | -834 | `mgc_lookback_breakout_walk_base:lb10:buf0.5:delta0:cl0.55:end1030:filtervwapdist20:maxday2_gap15` |
| 11 | 25 | 15 | 1187 | 21175 | 5531 | 1.23268374 | -1432 | 22/26 | -834 | `mgc_lookback_breakout_walk_base:lb10:buf0.5:delta0:cl0.5:end1030:filtervwapdist20:maxday2_gap15` |
| 12 | 25 | 15 | 1239 | 17517 | 5091 | 1.16866834 | -1808 | 22/26 | -986 | `mgc_lookback_breakout_walk_base:lb5:buf0:delta0:cl0.5:end1030:filterstart0900_nofri:maxday2_gap15` |
| 13 | 30 | 15 | 1168 | 18147 | 4604 | 1.19492781 | -1282 | 22/26 | -684 | `mgc_lookback_breakout_walk_base:lb10:buf0.5:delta0:cl0.5:end1030:filtervwapdist20:maxday2_gap15` |
| 14 | 30 | 15 | 1039 | 17560 | 4531 | 1.22974348 | -1474 | 22/26 | -1077 | `mgc_lookback_breakout_walk_base:lb10:buf0:delta0:cl0.5:end1030:filterabsdelta100:maxday1_gap0` |
| 15 | 25 | 15 | 915 | 15270 | 4296 | 1.2254235 | -1574 | 22/26 | -829 | `mgc_lookback_breakout_walk_base:lb5:buf0.5:delta0:cl0.5:end1030:filterstart0900_nofri:maxday1_gap0` |

## Selection Stability

| Config | Distinct Selected Candidates | Most Common Selection |
| --- | ---: | --- |
| 120x40 | 11 | `mgc_lookback_breakout_walk_base:lb10:buf0:delta0:cl0.5:end1330:filtervwapdist20:maxday2_gap15` (1) |
| 180x40 | 10 | `mgc_lookback_breakout_walk_base:lb5:buf0:delta0:cl0.55:end1030:filterstart0900_nofri:maxday1_gap0` (1) |
| 240x60 | 5 | `mgc_lookback_breakout_walk_base:lb10:buf0:delta0:cl0.55:end1030:filterbar8:maxday1_gap0` (1) |

## Interpretation

A deployable MGC normal bot needs positive frozen holdout behavior across multiple window sizes, acceptable negative-window behavior, and then replay/mechanics validation. Adaptive selection is included to detect whether the edge is stable enough to choose from recent history; the frozen current lead remains the cleaner implementation candidate if it survives.
