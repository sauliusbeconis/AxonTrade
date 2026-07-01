# VWAP Delta Execution Bot Failure Attribution

Status: research lead, not live-ready.

## Bot Defaults Rebuilt

This rebuild used the current `AxonTradeVwapDeltaExecutionBot` defaults:

- Strategy: `vwap_delta_exhaustion_fade_2pt_10d_cl0.5`
- Raw candidate spacing: `900` seconds
- Max raw candidates per day: `20`
- Context guard: `lookback_directional_move_points <= -2.5`, `session_range_points >= 30`, `risk_to_average_bar_range <= 1.75`
- Exit: `first_target=6`, `stop=10`, `runner_target=12`, `runner_stop=initial`
- Bot daily locks: `daily_loss=200`, `daily_profit=650`
- Cost model: ES, `slippage_ticks_per_contract=1`

## Main Result

| Scope | Trades | Net | Avg | PF | Max DD | 2024 | 2025 | 2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw VWAP/delta, bot spacing | 4681 | -209029.5 | -44.65 | 0.8913 | -253791 | -93362.5 | -145958 | 30291 |
| Context guard only | 1210 | 18917.5 | 15.63 | 1.0392 | -76625.5 | 11644 | -42735 | 50008.5 |
| Context guard + `200/650` daily lock | 306 | 608 | 1.99 | 1.005 | -12056 | -2824 | -7496 | 10928 |

The current-year edge is real after the context guard. Every 2026 month is positive under guard-only:

| Month | Trades | Net |
| --- | ---: | ---: |
| 2026-01 | 30 | 6440 |
| 2026-02 | 66 | 6388 |
| 2026-03 | 114 | 6652 |
| 2026-04 | 51 | 6280.5 |
| 2026-05 | 44 | 9392 |
| 2026-06 | 92 | 14856 |

## What Fails

The context guard works in 2024 and 2026 but fails in 2025. The main damage is not evenly spread:

| Month | Guarded Trades | Net | Avg |
| --- | ---: | ---: | ---: |
| 2025-04 | 138 | -36291 | -262.98 |
| 2025-10 | 54 | -10028 | -185.70 |
| 2025-05 | 63 | -8216 | -130.41 |
| 2025-11 | 84 | -5988 | -71.29 |
| 2025-02 | 57 | -5911.5 | -103.71 |
| 2025-06 | 28 | -5658.5 | -202.09 |

April 2025 is the primary failure cluster. It had much larger directional/range context than the profitable 2026 sample:

| Feature | 2025-04 Median | 2026 Median |
| --- | ---: | ---: |
| `session_range_points` | 86.75 | 64.75 |
| `directional_open_distance_points` | -39.25 | -27.75 |
| `directional_opening_range_breakout_points` | -60.75 | -42.25 |
| `lookback_directional_move_points` | -26.75 | -18.75 |

Interpretation: the bot is a fade. In 2025-04 it often faded after price had already moved too far directionally from the open/opening range. The guard correctly removes low-range and high-risk setups, but it does not yet veto strong trend-day continuation conditions.

## Candidate Failure Vetoes

Two simple entry-known vetoes improve the profile:

| Extra Veto | Trades | Net | Max DD | 2024 | 2025 | 2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `directional_opening_range_breakout_points >= -60` and `session_range_points <= 120` | 869 | 37192 | -31906.5 | 14068 | -9976.5 | 33100.5 |
| `directional_open_distance_points >= -60` and `session_range_points <= 100` | 973 | 41789 | -43505.5 | 14212 | -18955.5 | 46532.5 |

The opening-range veto is cleaner statistically, but `directional_opening_range_breakout_points` is not currently in the execution bot. The session-open approximation is easier to implement.

## Daily Lock Finding

The current bot daily lock (`loss=200`, `profit=650`) is too restrictive for evaluating the strategy edge. It cuts 2026 guard-only net from `50008.5` to `10928`, and it turns 2024 from `11644` to `-2824`.

For the session-open approximation veto, a looser `loss=2000`, `profit=5000` lock produced:

- All net: `40390.5`
- 2025 net: `-9833.5`
- 2026 net: `40188`
- Max DD: `-31501.5`

## Conclusion

The recency argument is valid: the setup is profitable in 2026, and that matters more than a blanket two-year average.

The failure mode is also clear enough to keep researching instead of discarding the bot: the bot fails mostly when it fades strong directional/trend-day extension, especially April 2025. A trend-day veto plus looser daily locks is the next sensible test.
