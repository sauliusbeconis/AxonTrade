# Sierra Signal Log Report

This report summarizes indicator-only Sierra Chart signal-log rows.
It is research-only and does not imply a tradable strategy.

## Source

- Signal log: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total rows | 78 |
| Candidate signals | 78 |
| Rejected signals | 0 |
| First row bar time | 2026-06-10 10:15:00 |
| Last row bar time | 2026-06-26 11:39:00 |
| Earliest bar time | 2026-06-10 10:15:00 |
| Latest bar time | 2026-06-26 11:39:00 |

## Symbols

| Symbol | Count |
| --- | ---: |
| ESU26-CME | 78 |

## Strategy IDs

| Strategy ID | Count |
| --- | ---: |
| delta_impulse_continue_10bar_2.5pt_50d | 78 |

## Event Types

| Event type | Count |
| --- | ---: |
| candidate_signal | 78 |

## Dates

| Date | Count |
| --- | ---: |
| 2026-06-10 | 6 |
| 2026-06-11 | 6 |
| 2026-06-12 | 6 |
| 2026-06-15 | 6 |
| 2026-06-16 | 6 |
| 2026-06-17 | 6 |
| 2026-06-18 | 6 |
| 2026-06-19 | 6 |
| 2026-06-22 | 6 |
| 2026-06-23 | 6 |
| 2026-06-24 | 6 |
| 2026-06-25 | 6 |
| 2026-06-26 | 6 |

## Candidate Directions

| Direction | Count |
| --- | ---: |
| long | 41 |
| short | 37 |

## Rejection Reasons

| Rejection reason | Count |
| --- | ---: |
| none | 0 |

## Candidates

| Time | Symbol | Direction | Entry | Stop | Target | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 2026-06-10 10:15:00 | ESU26-CME | long | 7447 | 7439 | 7457 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5; price_move=5.5; delta_sum=590; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 10:33:00 | ESU26-CME | long | 7458.25 | 7450.25 | 7468.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=11; price_move=15; delta_sum=451; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 11:27:00 | ESU26-CME | short | 7395.75 | 7403.75 | 7385.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=29; price_move=-14; delta_sum=-104; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 11:45:00 | ESU26-CME | long | 7388.75 | 7380.75 | 7398.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=35; price_move=5; delta_sum=215; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 12:03:00 | ESU26-CME | long | 7393.25 | 7385.25 | 7403.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=41; price_move=3.75; delta_sum=253; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 12:18:00 | ESU26-CME | long | 7384.5 | 7376.5 | 7394.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=46; price_move=11; delta_sum=190; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 10:18:00 | ESU26-CME | short | 7359.5 | 7367.5 | 7349.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=141; price_move=-23.5; delta_sum=-252; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 10:33:00 | ESU26-CME | short | 7372 | 7380 | 7362 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=146; price_move=-10.5; delta_sum=-475; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 10:51:00 | ESU26-CME | short | 7352.5 | 7360.5 | 7342.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=152; price_move=-24; delta_sum=-1487; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 11:06:00 | ESU26-CME | short | 7347.75 | 7355.75 | 7337.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=157; price_move=-27.5; delta_sum=-2016; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 11:48:00 | ESU26-CME | short | 7356.5 | 7364.5 | 7346.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=171; price_move=-9.25; delta_sum=-653; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 12:27:00 | ESU26-CME | short | 7358.5 | 7366.5 | 7348.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=184; price_move=-2.5; delta_sum=-976; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 10:15:00 | ESU26-CME | long | 7487.75 | 7479.75 | 7497.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=275; price_move=51.5; delta_sum=1409; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 10:30:00 | ESU26-CME | long | 7478.5 | 7470.5 | 7488.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=280; price_move=17.25; delta_sum=1352; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 10:45:00 | ESU26-CME | short | 7454.5 | 7462.5 | 7444.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=285; price_move=-33.25; delta_sum=-637; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 11:00:00 | ESU26-CME | long | 7504.75 | 7496.75 | 7514.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=290; price_move=26.25; delta_sum=1366; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 11:15:00 | ESU26-CME | long | 7513.5 | 7505.5 | 7523.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=295; price_move=59; delta_sum=2229; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 11:30:00 | ESU26-CME | long | 7511.75 | 7503.75 | 7521.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=300; price_move=7; delta_sum=1054; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 10:15:00 | ESU26-CME | short | 7610.5 | 7618.5 | 7600.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=410; price_move=-4.25; delta_sum=-226; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 10:30:00 | ESU26-CME | short | 7612.5 | 7620.5 | 7602.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=415; price_move=-3; delta_sum=-379; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 10:45:00 | ESU26-CME | long | 7617 | 7609 | 7627 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=420; price_move=6.5; delta_sum=2013; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 11:00:00 | ESU26-CME | long | 7625.25 | 7617.25 | 7635.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=425; price_move=12.75; delta_sum=2164; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 11:15:00 | ESU26-CME | long | 7626.5 | 7618.5 | 7636.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=430; price_move=9.5; delta_sum=2214; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 11:30:00 | ESU26-CME | long | 7634.75 | 7626.75 | 7644.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=435; price_move=9.5; delta_sum=1605; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 10:18:00 | ESU26-CME | short | 7622.75 | 7630.75 | 7612.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=546; price_move=-11.25; delta_sum=-583; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 10:33:00 | ESU26-CME | short | 7609.5 | 7617.5 | 7599.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=551; price_move=-14.5; delta_sum=-2967; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 10:48:00 | ESU26-CME | short | 7614.25 | 7622.25 | 7604.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=556; price_move=-8.5; delta_sum=-3166; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 11:09:00 | ESU26-CME | short | 7615.75 | 7623.75 | 7605.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=563; price_move=-3.25; delta_sum=-2062; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 11:24:00 | ESU26-CME | short | 7606.75 | 7614.75 | 7596.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=568; price_move=-6; delta_sum=-840; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 11:39:00 | ESU26-CME | short | 7609 | 7617 | 7599 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=573; price_move=-6.75; delta_sum=-1822; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 10:18:00 | ESU26-CME | long | 7596.25 | 7588.25 | 7606.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=681; price_move=3.25; delta_sum=1010; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 10:33:00 | ESU26-CME | long | 7587.75 | 7579.75 | 7597.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=686; price_move=3.75; delta_sum=1584; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 10:48:00 | ESU26-CME | short | 7576 | 7584 | 7566 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=691; price_move=-20.25; delta_sum=-2346; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 11:03:00 | ESU26-CME | short | 7572.5 | 7580.5 | 7562.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=696; price_move=-15.25; delta_sum=-2829; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 11:18:00 | ESU26-CME | long | 7582.75 | 7574.75 | 7592.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=701; price_move=6.75; delta_sum=245; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 11:33:00 | ESU26-CME | long | 7588.75 | 7580.75 | 7598.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=706; price_move=16.25; delta_sum=1835; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 10:15:00 | ESU26-CME | long | 7556.75 | 7548.75 | 7566.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=815; price_move=18.75; delta_sum=632; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 10:36:00 | ESU26-CME | long | 7561.25 | 7553.25 | 7571.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=822; price_move=6.25; delta_sum=118; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 10:54:00 | ESU26-CME | long | 7565.5 | 7557.5 | 7575.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=828; price_move=8.75; delta_sum=3234; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 11:09:00 | ESU26-CME | long | 7566.25 | 7558.25 | 7576.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=833; price_move=8.5; delta_sum=2632; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 11:51:00 | ESU26-CME | long | 7560 | 7552 | 7570 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=847; price_move=4.5; delta_sum=649; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 12:15:00 | ESU26-CME | long | 7561 | 7553 | 7571 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=855; price_move=13.75; delta_sum=298; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 10:30:00 | ESU26-CME | long | 7558.5 | 7550.5 | 7568.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=955; price_move=3.75; delta_sum=333; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 10:45:00 | ESU26-CME | long | 7563.75 | 7555.75 | 7573.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=960; price_move=4.25; delta_sum=557; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 11:00:00 | ESU26-CME | long | 7566.5 | 7558.5 | 7576.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=965; price_move=8; delta_sum=606; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 11:33:00 | ESU26-CME | short | 7562.25 | 7570.25 | 7552.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=976; price_move=-3.5; delta_sum=-193; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 12:39:00 | ESU26-CME | long | 7565.25 | 7557.25 | 7575.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=998; price_move=5.5; delta_sum=68; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 12:57:00 | ESU26-CME | short | 7556.25 | 7564.25 | 7546.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1004; price_move=-8.5; delta_sum=-234; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 10:30:00 | ESU26-CME | short | 7547.75 | 7555.75 | 7537.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1025; price_move=-43.5; delta_sum=-1218; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 10:45:00 | ESU26-CME | short | 7543.75 | 7551.75 | 7533.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1030; price_move=-36.75; delta_sum=-2216; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:03:00 | ESU26-CME | short | 7541.5 | 7549.5 | 7531.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1036; price_move=-13.75; delta_sum=-1483; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:18:00 | ESU26-CME | short | 7536.25 | 7544.25 | 7526.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1041; price_move=-5.5; delta_sum=-1591; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:36:00 | ESU26-CME | long | 7545.75 | 7537.75 | 7555.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1047; price_move=4.75; delta_sum=388; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:57:00 | ESU26-CME | long | 7542.5 | 7534.5 | 7552.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1054; price_move=2.75; delta_sum=1036; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 10:15:00 | ESU26-CME | long | 7482 | 7474 | 7492 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1155; price_move=28; delta_sum=3049; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 10:39:00 | ESU26-CME | short | 7468.75 | 7476.75 | 7458.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1163; price_move=-8.5; delta_sum=-565; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 10:54:00 | ESU26-CME | short | 7461.25 | 7469.25 | 7451.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1168; price_move=-18.5; delta_sum=-496; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 11:09:00 | ESU26-CME | short | 7454 | 7462 | 7444 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1173; price_move=-14.75; delta_sum=-1715; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 11:24:00 | ESU26-CME | short | 7441.75 | 7449.75 | 7431.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1178; price_move=-19.5; delta_sum=-3298; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 11:39:00 | ESU26-CME | short | 7442 | 7450 | 7432 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1183; price_move=-12; delta_sum=-673; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 10:15:00 | ESU26-CME | short | 7443.25 | 7451.25 | 7433.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1290; price_move=-5.5; delta_sum=-2638; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 10:36:00 | ESU26-CME | long | 7464 | 7456 | 7474 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1297; price_move=13.75; delta_sum=663; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 10:51:00 | ESU26-CME | long | 7485.75 | 7477.75 | 7495.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1302; price_move=30; delta_sum=1918; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 11:06:00 | ESU26-CME | long | 7483.75 | 7475.75 | 7493.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1307; price_move=19.75; delta_sum=741; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 11:45:00 | ESU26-CME | short | 7476 | 7484 | 7466 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1320; price_move=-14; delta_sum=-1477; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 12:00:00 | ESU26-CME | short | 7479.25 | 7487.25 | 7469.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1325; price_move=-10.75; delta_sum=-736; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 10:15:00 | ESU26-CME | long | 7436.75 | 7428.75 | 7446.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1425; price_move=17.75; delta_sum=1383; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 10:30:00 | ESU26-CME | long | 7460.75 | 7452.75 | 7470.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1430; price_move=39.5; delta_sum=4463; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 10:45:00 | ESU26-CME | long | 7451 | 7443 | 7461 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1435; price_move=14.25; delta_sum=2356; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 11:00:00 | ESU26-CME | short | 7456 | 7464 | 7446 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1440; price_move=-4.75; delta_sum=-1924; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 11:15:00 | ESU26-CME | short | 7424.75 | 7432.75 | 7414.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1445; price_move=-26.25; delta_sum=-3826; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 11:30:00 | ESU26-CME | short | 7449.75 | 7457.75 | 7439.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1450; price_move=-6.25; delta_sum=-830; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 10:15:00 | ESU26-CME | long | 7418.75 | 7410.75 | 7428.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1560; price_move=34; delta_sum=989; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 10:30:00 | ESU26-CME | long | 7425 | 7417 | 7435 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1565; price_move=14.75; delta_sum=544; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 10:48:00 | ESU26-CME | short | 7424.5 | 7432.5 | 7414.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1571; price_move=-7.25; delta_sum=-995; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 11:03:00 | ESU26-CME | short | 7418.25 | 7426.25 | 7408.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1576; price_move=-4.75; delta_sum=-2033; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 11:24:00 | ESU26-CME | long | 7436 | 7428 | 7446 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1583; price_move=17.25; delta_sum=348; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 11:39:00 | ESU26-CME | long | 7449.25 | 7441.25 | 7459.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1588; price_move=31; delta_sum=2022; first_target_points=5; runner_target_points=10; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |

## Interpretation

The overlay emitted candidate rows. Evaluate outcomes separately before treating any candidate as strategy evidence.
