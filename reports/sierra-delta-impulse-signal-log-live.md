# Sierra Signal Log Report

This report summarizes indicator-only Sierra Chart signal-log rows.
It is research-only and does not imply a tradable strategy.

## Source

- Signal log: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total rows | 163 |
| Candidate signals | 163 |
| Rejected signals | 0 |
| First row bar time | 2026-03-23 10:24:00 |
| Last row bar time | 2026-06-26 11:39:00 |
| Earliest bar time | 2026-03-23 10:24:00 |
| Latest bar time | 2026-06-26 11:39:00 |

## Symbols

| Symbol | Count |
| --- | ---: |
| ESU26-CME | 163 |

## Strategy IDs

| Strategy ID | Count |
| --- | ---: |
| delta_impulse_continue_10bar_2.5pt_50d | 163 |

## Event Types

| Event type | Count |
| --- | ---: |
| candidate_signal | 163 |

## Dates

| Date | Count |
| --- | ---: |
| 2026-03-23 | 3 |
| 2026-03-25 | 3 |
| 2026-03-27 | 1 |
| 2026-04-02 | 1 |
| 2026-04-07 | 2 |
| 2026-04-23 | 1 |
| 2026-04-24 | 2 |
| 2026-05-01 | 3 |
| 2026-05-04 | 1 |
| 2026-05-05 | 1 |
| 2026-05-13 | 3 |
| 2026-05-14 | 4 |
| 2026-05-15 | 2 |
| 2026-05-18 | 3 |
| 2026-05-20 | 6 |
| 2026-05-21 | 3 |
| 2026-05-22 | 2 |
| 2026-05-26 | 1 |
| 2026-05-27 | 3 |
| 2026-05-28 | 1 |
| 2026-05-29 | 2 |
| 2026-06-01 | 6 |
| 2026-06-02 | 3 |
| 2026-06-03 | 4 |
| 2026-06-04 | 6 |
| 2026-06-05 | 6 |
| 2026-06-08 | 6 |
| 2026-06-09 | 6 |
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
| long | 95 |
| short | 68 |

## Rejection Reasons

| Rejection reason | Count |
| --- | ---: |
| none | 0 |

## Candidates

| Time | Symbol | Direction | Entry | Stop | Target | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 2026-03-23 10:24:00 | ESU26-CME | long | 6742.75 | 6732.75 | 6750.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=558; price_move=20; delta_sum=55; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-03-23 10:51:00 | ESU26-CME | short | 6738.75 | 6748.75 | 6730.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=566; price_move=-2.5; delta_sum=-51; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-03-23 15:27:00 | ESU26-CME | short | 6702.25 | 6712.25 | 6694.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=629; price_move=-4.75; delta_sum=-81; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-03-25 10:27:00 | ESU26-CME | long | 6705.5 | 6695.5 | 6713.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=735; price_move=3.75; delta_sum=309; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-03-25 10:45:00 | ESU26-CME | long | 6712.5 | 6702.5 | 6720.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=740; price_move=16.75; delta_sum=298; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-03-25 11:51:00 | ESU26-CME | long | 6690.25 | 6680.25 | 6698.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=755; price_move=20.25; delta_sum=210; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-03-27 10:57:00 | ESU26-CME | long | 6519.75 | 6509.75 | 6527.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=915; price_move=4.75; delta_sum=119; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-04-02 10:36:00 | ESU26-CME | long | 6667.25 | 6657.25 | 6675.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=1314; price_move=60.25; delta_sum=65; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-04-07 14:45:00 | ESU26-CME | short | 6663 | 6673 | 6655 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1546; price_move=-21.75; delta_sum=-50; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-04-07 15:03:00 | ESU26-CME | short | 6649.75 | 6659.75 | 6641.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=1550; price_move=-27.5; delta_sum=-91; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-04-23 13:15:00 | ESU26-CME | short | 7177.75 | 7187.75 | 7169.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=2609; price_move=-42.25; delta_sum=-61; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-04-24 11:48:00 | ESU26-CME | long | 7250.25 | 7240.25 | 7258.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=2690; price_move=24.25; delta_sum=63; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-04-24 12:03:00 | ESU26-CME | long | 7250.75 | 7240.75 | 7258.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=2695; price_move=21; delta_sum=56; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-01 10:24:00 | ESU26-CME | long | 7351.75 | 7341.75 | 7359.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=3108; price_move=8; delta_sum=84; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-01 11:00:00 | ESU26-CME | short | 7328.5 | 7338.5 | 7320.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=3119; price_move=-21; delta_sum=-53; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-01 15:09:00 | ESU26-CME | long | 7327 | 7317 | 7335 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=3174; price_move=4.5; delta_sum=70; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-04 12:18:00 | ESU26-CME | short | 7275.75 | 7285.75 | 7267.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=3237; price_move=-8.25; delta_sum=-56; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-05 10:24:00 | ESU26-CME | long | 7340.5 | 7330.5 | 7348.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=3305; price_move=9.5; delta_sum=68; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-13 12:39:00 | ESU26-CME | long | 7521 | 7511 | 7529 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=3909; price_move=14; delta_sum=50; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-13 12:54:00 | ESU26-CME | long | 7524.5 | 7514.5 | 7532.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=3913; price_move=9.5; delta_sum=77; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-13 13:09:00 | ESU26-CME | long | 7530 | 7520 | 7538 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=3918; price_move=10; delta_sum=62; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-14 10:42:00 | ESU26-CME | long | 7573.75 | 7563.75 | 7581.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=3980; price_move=15.25; delta_sum=52; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-14 10:57:00 | ESU26-CME | long | 7575.25 | 7565.25 | 7583.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=3985; price_move=14.25; delta_sum=59; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-14 11:12:00 | ESU26-CME | long | 7581 | 7571 | 7589 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=3989; price_move=9.25; delta_sum=68; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-14 14:09:00 | ESU26-CME | long | 7579.5 | 7569.5 | 7587.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4042; price_move=3.5; delta_sum=50; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-15 10:18:00 | ESU26-CME | long | 7521.75 | 7511.75 | 7529.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4088; price_move=42.75; delta_sum=74; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-15 10:33:00 | ESU26-CME | long | 7521.25 | 7511.25 | 7529.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4093; price_move=21.75; delta_sum=83; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-18 13:39:00 | ESU26-CME | long | 7466.25 | 7456.25 | 7474.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4278; price_move=3.75; delta_sum=58; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-18 15:09:00 | ESU26-CME | long | 7459.25 | 7449.25 | 7467.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4305; price_move=21.25; delta_sum=61; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-18 15:24:00 | ESU26-CME | long | 7448.5 | 7438.5 | 7456.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4310; price_move=11.25; delta_sum=92; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-20 11:18:00 | ESU26-CME | long | 7503.5 | 7493.5 | 7511.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4489; price_move=26; delta_sum=52; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-20 11:36:00 | ESU26-CME | long | 7497.5 | 7487.5 | 7505.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4495; price_move=14; delta_sum=61; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-20 13:24:00 | ESU26-CME | long | 7496.25 | 7486.25 | 7504.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4531; price_move=5.25; delta_sum=118; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-20 13:39:00 | ESU26-CME | long | 7501.5 | 7491.5 | 7509.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4536; price_move=14.5; delta_sum=122; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-20 14:09:00 | ESU26-CME | short | 7498.75 | 7508.75 | 7490.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=4545; price_move=-3.25; delta_sum=-202; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-20 15:39:00 | ESU26-CME | long | 7510 | 7500 | 7518 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4567; price_move=9; delta_sum=58; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-21 12:12:00 | ESU26-CME | long | 7490.5 | 7480.5 | 7498.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4631; price_move=5.75; delta_sum=60; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-21 13:15:00 | ESU26-CME | long | 7513.75 | 7503.75 | 7521.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4649; price_move=28.75; delta_sum=50; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-21 13:30:00 | ESU26-CME | long | 7520.75 | 7510.75 | 7528.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4654; price_move=37; delta_sum=88; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-22 14:03:00 | ESU26-CME | short | 7566.5 | 7576.5 | 7558.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=4796; price_move=-9.75; delta_sum=-60; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-22 14:18:00 | ESU26-CME | short | 7567.25 | 7577.25 | 7559.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=4800; price_move=-6.25; delta_sum=-60; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-26 10:15:00 | ESU26-CME | long | 7608 | 7598 | 7616 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=4895; price_move=5; delta_sum=50; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-27 10:18:00 | ESU26-CME | long | 7602.75 | 7592.75 | 7610.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5013; price_move=8.5; delta_sum=52; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-27 10:36:00 | ESU26-CME | long | 7602.5 | 7592.5 | 7610.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5019; price_move=6.75; delta_sum=85; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-27 13:06:00 | ESU26-CME | short | 7579.75 | 7589.75 | 7571.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5068; price_move=-12.5; delta_sum=-64; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-28 10:42:00 | ESU26-CME | short | 7619.25 | 7629.25 | 7611.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5144; price_move=-8.25; delta_sum=-70; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-29 10:54:00 | ESU26-CME | long | 7657.25 | 7647.25 | 7665.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5267; price_move=3.5; delta_sum=111; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-05-29 11:09:00 | ESU26-CME | long | 7662.25 | 7652.25 | 7670.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5272; price_move=13; delta_sum=105; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-01 10:15:00 | ESU26-CME | short | 7652 | 7662 | 7644 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5383; price_move=-5; delta_sum=-68; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-01 10:36:00 | ESU26-CME | short | 7644.5 | 7654.5 | 7636.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5390; price_move=-8; delta_sum=-95; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-01 10:51:00 | ESU26-CME | short | 7645 | 7655 | 7637 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5395; price_move=-8.75; delta_sum=-66; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-01 12:09:00 | ESU26-CME | short | 7655 | 7665 | 7647 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5420; price_move=-9; delta_sum=-55; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-01 13:45:00 | ESU26-CME | long | 7688.75 | 7678.75 | 7696.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5451; price_move=26.25; delta_sum=51; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-01 14:00:00 | ESU26-CME | long | 7686.75 | 7676.75 | 7694.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5456; price_move=16; delta_sum=50; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-02 11:12:00 | ESU26-CME | long | 7689.75 | 7679.75 | 7697.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5528; price_move=11; delta_sum=59; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-02 11:27:00 | ESU26-CME | long | 7689.25 | 7679.25 | 7697.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5533; price_move=3.25; delta_sum=54; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-02 11:48:00 | ESU26-CME | short | 7686.5 | 7696.5 | 7678.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5540; price_move=-4.25; delta_sum=-50; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-03 13:15:00 | ESU26-CME | short | 7630.75 | 7640.75 | 7622.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5701; price_move=-2.75; delta_sum=-51; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-03 14:30:00 | ESU26-CME | long | 7648.75 | 7638.75 | 7656.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5726; price_move=4.75; delta_sum=58; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-03 14:45:00 | ESU26-CME | long | 7647.75 | 7637.75 | 7655.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5731; price_move=8; delta_sum=61; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-03 15:42:00 | ESU26-CME | long | 7644.5 | 7634.5 | 7652.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5750; price_move=5; delta_sum=54; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-04 10:15:00 | ESU26-CME | long | 7625.5 | 7615.5 | 7633.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5776; price_move=7.75; delta_sum=181; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-04 11:00:00 | ESU26-CME | long | 7636.5 | 7626.5 | 7644.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5791; price_move=9.75; delta_sum=51; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-04 11:15:00 | ESU26-CME | long | 7650 | 7640 | 7658 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5796; price_move=19.25; delta_sum=105; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-04 11:30:00 | ESU26-CME | long | 7647.5 | 7637.5 | 7655.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5801; price_move=11; delta_sum=76; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-04 12:30:00 | ESU26-CME | long | 7654.75 | 7644.75 | 7662.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5821; price_move=9; delta_sum=62; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-04 12:48:00 | ESU26-CME | long | 7659.25 | 7649.25 | 7667.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5827; price_move=3; delta_sum=97; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-05 10:57:00 | ESU26-CME | long | 7585.25 | 7575.25 | 7593.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=5924; price_move=7.25; delta_sum=76; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-05 11:36:00 | ESU26-CME | short | 7555.25 | 7565.25 | 7547.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5937; price_move=-20.25; delta_sum=-52; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-05 11:51:00 | ESU26-CME | short | 7553.75 | 7563.75 | 7545.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5942; price_move=-12.75; delta_sum=-68; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-05 12:09:00 | ESU26-CME | short | 7542 | 7552 | 7534 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5948; price_move=-9.5; delta_sum=-57; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-05 12:24:00 | ESU26-CME | short | 7540.25 | 7550.25 | 7532.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5953; price_move=-13.75; delta_sum=-98; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-05 12:39:00 | ESU26-CME | short | 7522 | 7532 | 7514 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=5958; price_move=-20; delta_sum=-109; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-08 10:27:00 | ESU26-CME | long | 7509.5 | 7499.5 | 7517.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6049; price_move=16.75; delta_sum=79; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-08 10:42:00 | ESU26-CME | long | 7511.25 | 7501.25 | 7519.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6054; price_move=9.25; delta_sum=78; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-08 10:57:00 | ESU26-CME | long | 7534.75 | 7524.75 | 7542.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6059; price_move=25.25; delta_sum=123; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-08 11:12:00 | ESU26-CME | long | 7533 | 7523 | 7541 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6064; price_move=21.75; delta_sum=185; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-08 13:09:00 | ESU26-CME | short | 7487.5 | 7497.5 | 7479.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6103; price_move=-18.75; delta_sum=-129; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-08 13:24:00 | ESU26-CME | short | 7490 | 7500 | 7482 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6108; price_move=-17; delta_sum=-50; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-09 10:15:00 | ESU26-CME | short | 7484.5 | 7494.5 | 7476.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6180; price_move=-64.5; delta_sum=-243; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-09 10:30:00 | ESU26-CME | short | 7500 | 7510 | 7492 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6185; price_move=-30.5; delta_sum=-170; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-09 10:45:00 | ESU26-CME | short | 7446.25 | 7456.25 | 7438.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6190; price_move=-38.25; delta_sum=-229; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-09 11:00:00 | ESU26-CME | short | 7453.25 | 7463.25 | 7445.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6195; price_move=-46.75; delta_sum=-399; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-09 11:21:00 | ESU26-CME | short | 7428.25 | 7438.25 | 7420.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6202; price_move=-9.25; delta_sum=-185; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-09 11:36:00 | ESU26-CME | short | 7389.25 | 7399.25 | 7381.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6207; price_move=-65.25; delta_sum=-179; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 10:15:00 | ESU26-CME | long | 7447 | 7437 | 7455 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6315; price_move=5.5; delta_sum=590; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 10:33:00 | ESU26-CME | long | 7458.25 | 7448.25 | 7466.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6321; price_move=15; delta_sum=451; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 11:27:00 | ESU26-CME | short | 7395.75 | 7405.75 | 7387.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6339; price_move=-14; delta_sum=-104; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 11:45:00 | ESU26-CME | long | 7388.75 | 7378.75 | 7396.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6345; price_move=5; delta_sum=215; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 12:03:00 | ESU26-CME | long | 7393.25 | 7383.25 | 7401.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6351; price_move=3.75; delta_sum=253; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-10 12:18:00 | ESU26-CME | long | 7384.5 | 7374.5 | 7392.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6356; price_move=11; delta_sum=190; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 10:18:00 | ESU26-CME | short | 7359.5 | 7369.5 | 7351.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6451; price_move=-23.5; delta_sum=-252; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 10:33:00 | ESU26-CME | short | 7372 | 7382 | 7364 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6456; price_move=-10.5; delta_sum=-475; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 10:51:00 | ESU26-CME | short | 7352.5 | 7362.5 | 7344.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6462; price_move=-24; delta_sum=-1487; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 11:06:00 | ESU26-CME | short | 7347.75 | 7357.75 | 7339.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6467; price_move=-27.5; delta_sum=-2016; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 11:48:00 | ESU26-CME | short | 7356.5 | 7366.5 | 7348.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6481; price_move=-9.25; delta_sum=-653; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-11 12:27:00 | ESU26-CME | short | 7358.5 | 7368.5 | 7350.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6494; price_move=-2.5; delta_sum=-976; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 10:15:00 | ESU26-CME | long | 7487.75 | 7477.75 | 7495.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6585; price_move=51.5; delta_sum=1409; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 10:30:00 | ESU26-CME | long | 7478.5 | 7468.5 | 7486.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6590; price_move=17.25; delta_sum=1352; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 10:45:00 | ESU26-CME | short | 7454.5 | 7464.5 | 7446.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6595; price_move=-33.25; delta_sum=-637; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 11:00:00 | ESU26-CME | long | 7504.75 | 7494.75 | 7512.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6600; price_move=26.25; delta_sum=1366; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 11:15:00 | ESU26-CME | long | 7513.5 | 7503.5 | 7521.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6605; price_move=59; delta_sum=2229; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-12 11:30:00 | ESU26-CME | long | 7511.75 | 7501.75 | 7519.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6610; price_move=7; delta_sum=1054; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 10:15:00 | ESU26-CME | short | 7610.5 | 7620.5 | 7602.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6720; price_move=-4.25; delta_sum=-226; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 10:30:00 | ESU26-CME | short | 7612.5 | 7622.5 | 7604.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6725; price_move=-3; delta_sum=-379; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 10:45:00 | ESU26-CME | long | 7617 | 7607 | 7625 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6730; price_move=6.5; delta_sum=2013; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 11:00:00 | ESU26-CME | long | 7625.25 | 7615.25 | 7633.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6735; price_move=12.75; delta_sum=2164; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 11:15:00 | ESU26-CME | long | 7626.5 | 7616.5 | 7634.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6740; price_move=9.5; delta_sum=2214; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-15 11:30:00 | ESU26-CME | long | 7634.75 | 7624.75 | 7642.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6745; price_move=9.5; delta_sum=1605; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 10:18:00 | ESU26-CME | short | 7622.75 | 7632.75 | 7614.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6856; price_move=-11.25; delta_sum=-583; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 10:33:00 | ESU26-CME | short | 7609.5 | 7619.5 | 7601.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6861; price_move=-14.5; delta_sum=-2967; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 10:48:00 | ESU26-CME | short | 7614.25 | 7624.25 | 7606.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6866; price_move=-8.5; delta_sum=-3166; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 11:09:00 | ESU26-CME | short | 7615.75 | 7625.75 | 7607.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6873; price_move=-3.25; delta_sum=-2062; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 11:24:00 | ESU26-CME | short | 7606.75 | 7616.75 | 7598.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6878; price_move=-6; delta_sum=-840; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-16 11:39:00 | ESU26-CME | short | 7609 | 7619 | 7601 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=6883; price_move=-6.75; delta_sum=-1822; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 10:18:00 | ESU26-CME | long | 7596.25 | 7586.25 | 7604.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6991; price_move=3.25; delta_sum=1010; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 10:33:00 | ESU26-CME | long | 7587.75 | 7577.75 | 7595.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=6996; price_move=3.75; delta_sum=1584; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 10:48:00 | ESU26-CME | short | 7576 | 7586 | 7568 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7001; price_move=-20.25; delta_sum=-2346; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 11:03:00 | ESU26-CME | short | 7572.5 | 7582.5 | 7564.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7006; price_move=-15.25; delta_sum=-2829; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 11:18:00 | ESU26-CME | long | 7582.75 | 7572.75 | 7590.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7011; price_move=6.75; delta_sum=245; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-17 11:33:00 | ESU26-CME | long | 7588.75 | 7578.75 | 7596.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7016; price_move=16.25; delta_sum=1835; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 10:15:00 | ESU26-CME | long | 7556.75 | 7546.75 | 7564.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7125; price_move=18.75; delta_sum=632; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 10:36:00 | ESU26-CME | long | 7561.25 | 7551.25 | 7569.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7132; price_move=6.25; delta_sum=118; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 10:54:00 | ESU26-CME | long | 7565.5 | 7555.5 | 7573.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7138; price_move=8.75; delta_sum=3234; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 11:09:00 | ESU26-CME | long | 7566.25 | 7556.25 | 7574.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7143; price_move=8.5; delta_sum=2632; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 11:51:00 | ESU26-CME | long | 7560 | 7550 | 7568 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7157; price_move=4.5; delta_sum=649; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-18 12:15:00 | ESU26-CME | long | 7561 | 7551 | 7569 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7165; price_move=13.75; delta_sum=298; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 10:30:00 | ESU26-CME | long | 7558.5 | 7548.5 | 7566.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7265; price_move=3.75; delta_sum=333; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 10:45:00 | ESU26-CME | long | 7563.75 | 7553.75 | 7571.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7270; price_move=4.25; delta_sum=557; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 11:00:00 | ESU26-CME | long | 7566.5 | 7556.5 | 7574.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7275; price_move=8; delta_sum=606; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 11:33:00 | ESU26-CME | short | 7562.25 | 7572.25 | 7554.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7286; price_move=-3.5; delta_sum=-193; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 12:39:00 | ESU26-CME | long | 7565.25 | 7555.25 | 7573.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7308; price_move=5.5; delta_sum=68; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-19 12:57:00 | ESU26-CME | short | 7556.25 | 7566.25 | 7548.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7314; price_move=-8.5; delta_sum=-234; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 10:30:00 | ESU26-CME | short | 7547.75 | 7557.75 | 7539.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7335; price_move=-43.5; delta_sum=-1218; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 10:45:00 | ESU26-CME | short | 7543.75 | 7553.75 | 7535.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7340; price_move=-36.75; delta_sum=-2216; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:03:00 | ESU26-CME | short | 7541.5 | 7551.5 | 7533.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7346; price_move=-13.75; delta_sum=-1483; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:18:00 | ESU26-CME | short | 7536.25 | 7546.25 | 7528.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7351; price_move=-5.5; delta_sum=-1591; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:36:00 | ESU26-CME | long | 7545.75 | 7535.75 | 7553.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7357; price_move=4.75; delta_sum=388; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-22 11:57:00 | ESU26-CME | long | 7542.5 | 7532.5 | 7550.5 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7364; price_move=2.75; delta_sum=1036; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 10:15:00 | ESU26-CME | long | 7482 | 7472 | 7490 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7465; price_move=28; delta_sum=3049; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 10:39:00 | ESU26-CME | short | 7468.75 | 7478.75 | 7460.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7473; price_move=-8.5; delta_sum=-565; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 10:54:00 | ESU26-CME | short | 7461.25 | 7471.25 | 7453.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7478; price_move=-18.5; delta_sum=-496; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 11:09:00 | ESU26-CME | short | 7454 | 7464 | 7446 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7483; price_move=-14.75; delta_sum=-1715; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 11:24:00 | ESU26-CME | short | 7441.75 | 7451.75 | 7433.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7488; price_move=-19.5; delta_sum=-3298; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-23 11:39:00 | ESU26-CME | short | 7442 | 7452 | 7434 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7493; price_move=-12; delta_sum=-673; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 10:15:00 | ESU26-CME | short | 7443.25 | 7453.25 | 7435.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7600; price_move=-5.5; delta_sum=-2638; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 10:36:00 | ESU26-CME | long | 7464 | 7454 | 7472 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7607; price_move=13.75; delta_sum=663; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 10:51:00 | ESU26-CME | long | 7485.75 | 7475.75 | 7493.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7612; price_move=30; delta_sum=1918; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 11:06:00 | ESU26-CME | long | 7483.75 | 7473.75 | 7491.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7617; price_move=19.75; delta_sum=741; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 11:45:00 | ESU26-CME | short | 7476 | 7486 | 7468 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7630; price_move=-14; delta_sum=-1477; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-24 12:00:00 | ESU26-CME | short | 7479.25 | 7489.25 | 7471.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7635; price_move=-10.75; delta_sum=-736; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 10:15:00 | ESU26-CME | long | 7436.75 | 7426.75 | 7444.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7735; price_move=17.75; delta_sum=1383; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 10:30:00 | ESU26-CME | long | 7460.75 | 7450.75 | 7468.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7740; price_move=39.5; delta_sum=4463; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 10:45:00 | ESU26-CME | long | 7451 | 7441 | 7459 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7745; price_move=14.25; delta_sum=2356; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 11:00:00 | ESU26-CME | short | 7456 | 7466 | 7448 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7750; price_move=-4.75; delta_sum=-1924; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 11:15:00 | ESU26-CME | short | 7424.75 | 7434.75 | 7416.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7755; price_move=-26.25; delta_sum=-3826; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-25 11:30:00 | ESU26-CME | short | 7449.75 | 7459.75 | 7441.75 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7760; price_move=-6.25; delta_sum=-830; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 10:15:00 | ESU26-CME | long | 7418.75 | 7408.75 | 7426.75 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7870; price_move=34; delta_sum=989; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 10:30:00 | ESU26-CME | long | 7425 | 7415 | 7433 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7875; price_move=14.75; delta_sum=544; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 10:48:00 | ESU26-CME | short | 7424.5 | 7434.5 | 7416.5 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7881; price_move=-7.25; delta_sum=-995; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 11:03:00 | ESU26-CME | short | 7418.25 | 7428.25 | 7410.25 | short delta impulse continuation; lookback_bars=10; price_reference_bar_index=7886; price_move=-4.75; delta_sum=-2033; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 11:24:00 | ESU26-CME | long | 7436 | 7426 | 7444 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7893; price_move=17.25; delta_sum=348; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |
| 2026-06-26 11:39:00 | ESU26-CME | long | 7449.25 | 7439.25 | 7457.25 | long delta impulse continuation; lookback_bars=10; price_reference_bar_index=7898; price_move=31; delta_sum=2022; first_target_points=5; runner_target_points=8; runner_stop_mode=initial; minimum_spacing_seconds=900; max_signals_per_day=6 |

## Interpretation

The overlay emitted candidate rows. Evaluate outcomes separately before treating any candidate as strategy evidence.
