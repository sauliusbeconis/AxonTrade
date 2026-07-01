# VWAP Delta Execution Bot Normal-Risk Research

Status: historical research note, superseded by the later accepted 300-second
candidate in `reports/sierra-vwap-delta-execution-bot-space300-7-12-10-primary.md`.

This pass removes the LucidFlex mechanics/evaluation limits from research.
The `Daily Loss Lock USD = 200` and `Daily Profit Lock USD = 650` settings are
treated as evaluation-account sizing constraints only.

## Original Strong Candidate

The strongest pre-mechanics research path was:

- strategy: `vwap_delta_exhaustion_fade_2pt_10d_cl0.5`
- exit: `6 / 10 / 12 / initial`
- guard:
  - `lookback_directional_move_points <= -2.5`
  - `session_range_points >= 30`
  - `risk_to_average_bar_range <= 1.75`
- normal research health gate:
  - `daily_loss_limit_usd = 3600`
  - `maximum_equity_drawdown_usd = 4000`
  - no daily profit lock
  - no consecutive-loss pause

On the fresh historical research sample this produced:

| Scope | Trades | Net USD | Avg | PF | Max DD | Worst Day |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Fresh sample, fixed health gate | 526 | 63080.5 | 119.92 | 1.3449 | -15172 | 2026-03-09 -4128 |

Important correction: that fresh context file contains candidate dates from
`2025-10-13` through `2026-06-25`. It did not include the large April 2025
failure regime now present in the expanded export.

## Expanded Export Recheck

The expanded context files now cover:

| Artifact | Rows | Candidate Dates | First | Last |
| --- | ---: | ---: | --- | --- |
| Research artifact, 300s spacing | 5972 | 485 | 2024-08-09 | 2026-06-30 |
| Current bot-default artifact, 900s spacing | 4681 | 505 | 2024-07-12 | 2026-06-30 |

The 300-second artifact is useful research evidence, but it is not the current
Sierra bot default. The current bot default uses `900` seconds of raw candidate
spacing.

## Current Bot Spacing, Normal Risk

Using the current bot spacing (`900` seconds), the original guard and normal
`daily3600/dd4000` health gate remain positive but weaker after the expanded
2024-2026 data is included:

| Variant | Trades | Net USD | Avg | PF | Max DD | 2024 | 2025 | 2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Guard only | 1210 | 18917.5 | 15.63 | 1.0392 | -76625.5 | 11644 | -42735 | 50008.5 |
| Guard + `daily3600/dd4000` | 1140 | 32357.5 | 28.38 | 1.0727 | -65289.5 | 6436 | -29807 | 55728.5 |

The normal health gate is better than the evaluation-account lock, but it does
not fully solve the 2025 regime.

## Trend-Day Veto Retest

Two entry-known vetoes were retested with normal risk controls:

- opening-range veto:
  `directional_opening_range_breakout_points >= -60` and
  `session_range_points <= 120`
- session-open veto:
  `directional_open_distance_points >= -60` and
  `session_range_points <= 100`

For the current `900` second bot spacing:

| Variant | Health Gate | Trades | Net USD | Avg | PF | Max DD | 2024 | 2025 | 2026 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Guard + opening-range veto | `daily3600/dd4000` | 832 | 36876 | 44.32 | 1.1172 | -28866.5 | 11628 | -8180.5 | 33428.5 |
| Guard + session-open veto | `daily3600/dd4000` | 938 | 44609 | 47.56 | 1.1256 | -39297.5 | 11772 | -15219.5 | 48056.5 |
| Guard + session-open veto | `daily2400/dd4000` | 928 | 50629 | 54.56 | 1.1454 | -33441.5 | 11772 | -9363.5 | 48220.5 |

The best current-bot-spacing balance in this pass is:

`guard + session-open veto + daily2400/dd4000`

Monthly behavior for that row:

| Month | Trades | Net USD |
| --- | ---: | ---: |
| 2024-07 | 21 | -1372 |
| 2024-08 | 30 | 4540 |
| 2024-09 | 28 | 3904 |
| 2024-10 | 20 | 5360 |
| 2024-11 | 14 | 2052 |
| 2024-12 | 16 | -2712 |
| 2025-01 | 33 | 6494 |
| 2025-02 | 46 | -6072 |
| 2025-03 | 74 | 8432 |
| 2025-04 | 66 | -7187 |
| 2025-05 | 59 | -7888 |
| 2025-06 | 27 | -6526.5 |
| 2025-07 | 8 | -1256 |
| 2025-08 | 18 | 124 |
| 2025-09 | 10 | 1080 |
| 2025-10 | 35 | -2820 |
| 2025-11 | 56 | -6392 |
| 2025-12 | 36 | 12648 |
| 2026-01 | 22 | 5496 |
| 2026-02 | 54 | 7972 |
| 2026-03 | 100 | 9700 |
| 2026-04 | 47 | 2808.5 |
| 2026-05 | 43 | 8524 |
| 2026-06 | 65 | 13720 |

## Research-Artifact Spacing Check

The 300-second research artifact produces larger totals, but this would require
a deliberate Sierra setting change:

| Variant | Health Gate | Trades | Net USD | Avg | PF | Max DD | 2024 | 2025 | 2026 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Guard + `daily3600/dd4000` | normal | 1385 | 60492.5 | 43.68 | 1.1147 | -62097 | 19884 | -21414.5 | 62023 |
| Guard + session-open veto | `daily2400/dd10000` | 1159 | 75812 | 65.41 | 1.1784 | -33857 | 19200 | -4327 | 60939 |

This is promising, but it is not the current bot. Treat `300` second spacing as
a separate candidate, not as proof that the current Sierra defaults are already
matched to the strongest research row.

## Conclusion

Do not discard `AxonTradeVwapDeltaExecutionBot`.

The older expanded data shows a real failure regime, mostly in 2025, but the
current 2026 regime remains strongly positive. The next implementation research
candidate should use normal risk controls and a trend-day veto, not the
LucidFlex `200/650` lock.

Most practical next candidate:

- keep `Minimum Raw Candidate Spacing Seconds = 900` for now;
- keep `6 / 10 / 12 / initial`;
- keep the existing guard;
- add session-open trend-day veto:
  `directional_open_distance_points >= -60` and
  `session_range_points <= 100`;
- replace research defaults with normal health gate:
  `daily_loss_limit_usd = 2400`, `maximum_equity_drawdown_usd = 4000`,
  no profit lock.

This candidate is now reflected in the sim-only ACSIL execution source defaults.
The source still rejects live trade-service routing.

The 300-second spacing candidate deserves a separate replay/mechanics test only
after the 900-second vetoed candidate is frozen and compared.
