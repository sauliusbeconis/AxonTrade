# Sierra Signal Log Report

This report summarizes indicator-only Sierra Chart signal-log rows.
It is research-only and does not imply a tradable strategy.

## Source

- Signal log: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total rows | 30 |
| Candidate signals | 30 |
| Rejected signals | 0 |
| First row bar time | 2026-06-22 10:30:00 |
| Last row bar time | 2026-06-26 11:39:00 |
| Earliest bar time | 2026-06-22 10:30:00 |
| Latest bar time | 2026-06-26 11:39:00 |

## Symbols

| Symbol | Count |
| --- | ---: |
| ESU26-CME | 30 |

## Strategy IDs

| Strategy ID | Count |
| --- | ---: |
| delta_impulse_continue_10bar_2.5pt_50d | 30 |

## Event Types

| Event type | Count |
| --- | ---: |
| candidate_signal | 30 |

## Dates

| Date | Count |
| --- | ---: |
| 2026-06-22 | 6 |
| 2026-06-23 | 6 |
| 2026-06-24 | 6 |
| 2026-06-25 | 6 |
| 2026-06-26 | 6 |

## Candidate Directions

| Direction | Count |
| --- | ---: |
| long | 13 |
| short | 17 |

## Rejection Reasons

| Rejection reason | Count |
| --- | ---: |
| none | 0 |

## Candidates

| Time | Symbol | Direction | Entry | Stop | Target | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 2026-06-22 10:30:00 | ESU26-CME | short | 7547.75 | 7552.75 | 7532.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=10; price_move=-43.5; delta_sum=-1218; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 10:45:00 | ESU26-CME | short | 7543.75 | 7548.75 | 7528.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=15; price_move=-36.75; delta_sum=-2216; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:03:00 | ESU26-CME | short | 7541.5 | 7546.5 | 7526.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=21; price_move=-13.75; delta_sum=-1483; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:18:00 | ESU26-CME | short | 7536.25 | 7541.25 | 7521.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=26; price_move=-5.5; delta_sum=-1591; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:36:00 | ESU26-CME | long | 7545.75 | 7540.75 | 7560.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=32; price_move=4.75; delta_sum=388; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:57:00 | ESU26-CME | long | 7542.5 | 7537.5 | 7557.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=39; price_move=2.75; delta_sum=1036; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 10:15:00 | ESU26-CME | long | 7482 | 7477 | 7497 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=140; price_move=28; delta_sum=3049; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 10:39:00 | ESU26-CME | short | 7468.75 | 7473.75 | 7453.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=148; price_move=-8.5; delta_sum=-565; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 10:54:00 | ESU26-CME | short | 7461.25 | 7466.25 | 7446.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=153; price_move=-18.5; delta_sum=-496; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 11:09:00 | ESU26-CME | short | 7454 | 7459 | 7439 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=158; price_move=-14.75; delta_sum=-1715; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 11:24:00 | ESU26-CME | short | 7441.75 | 7446.75 | 7426.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=163; price_move=-19.5; delta_sum=-3298; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 11:39:00 | ESU26-CME | short | 7442 | 7447 | 7427 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=168; price_move=-12; delta_sum=-673; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 10:15:00 | ESU26-CME | short | 7443.25 | 7448.25 | 7428.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=275; price_move=-5.5; delta_sum=-2638; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 10:36:00 | ESU26-CME | long | 7464 | 7459 | 7479 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=282; price_move=13.75; delta_sum=663; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 10:51:00 | ESU26-CME | long | 7485.75 | 7480.75 | 7500.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=287; price_move=30; delta_sum=1918; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 11:06:00 | ESU26-CME | long | 7483.75 | 7478.75 | 7498.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=292; price_move=19.75; delta_sum=741; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 11:45:00 | ESU26-CME | short | 7476 | 7481 | 7461 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=305; price_move=-14; delta_sum=-1477; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 12:00:00 | ESU26-CME | short | 7479.25 | 7484.25 | 7464.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=310; price_move=-10.75; delta_sum=-736; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 10:15:00 | ESU26-CME | long | 7436.75 | 7431.75 | 7451.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=410; price_move=17.75; delta_sum=1383; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 10:30:00 | ESU26-CME | long | 7460.75 | 7455.75 | 7475.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=415; price_move=39.5; delta_sum=4463; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 10:45:00 | ESU26-CME | long | 7451 | 7446 | 7466 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=420; price_move=14.25; delta_sum=2356; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 11:00:00 | ESU26-CME | short | 7456 | 7461 | 7441 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=425; price_move=-4.75; delta_sum=-1924; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 11:15:00 | ESU26-CME | short | 7424.75 | 7429.75 | 7409.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=430; price_move=-26.25; delta_sum=-3826; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 11:30:00 | ESU26-CME | short | 7449.75 | 7454.75 | 7434.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=435; price_move=-6.25; delta_sum=-830; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 10:15:00 | ESU26-CME | long | 7418.75 | 7413.75 | 7433.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=545; price_move=34; delta_sum=989; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 10:30:00 | ESU26-CME | long | 7425 | 7420 | 7440 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=550; price_move=14.75; delta_sum=544; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 10:48:00 | ESU26-CME | short | 7424.5 | 7429.5 | 7409.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=556; price_move=-7.25; delta_sum=-995; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 11:03:00 | ESU26-CME | short | 7418.25 | 7423.25 | 7403.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=561; price_move=-4.75; delta_sum=-2033; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 11:24:00 | ESU26-CME | long | 7436 | 7431 | 7451 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=568; price_move=17.25; delta_sum=348; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 11:39:00 | ESU26-CME | long | 7449.25 | 7444.25 | 7464.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=573; price_move=31; delta_sum=2022; first_target_points=5; runner_target_points=15; runner_stop_mode=breakeven; minimum_spacing_seconds=900; max_signals_per_day=6 |

## Interpretation

The overlay emitted candidate rows. Evaluate outcomes separately before treating any candidate as strategy evidence.
