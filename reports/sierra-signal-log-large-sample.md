# Sierra Signal Log Report

This report summarizes indicator-only Sierra Chart signal-log rows.
It is research-only and does not imply a tradable strategy.

## Source

- Signal log: `data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total rows | 43048 |
| Candidate signals | 23 |
| Rejected signals | 43025 |
| First row bar time | 2026-05-21 09:30:00 |
| Last row bar time | 2026-06-19 12:59:58 |
| Earliest bar time | 2026-05-21 09:30:00 |
| Latest bar time | 2026-06-19 12:59:58 |

## Symbols

| Symbol | Count |
| --- | ---: |
| ESU26-CME | 43048 |

## Strategy IDs

| Strategy ID | Count |
| --- | ---: |
| liquidity_sweep_absorption_reversal | 43048 |

## Event Types

| Event type | Count |
| --- | ---: |
| candidate_signal | 23 |
| rejected_signal | 43025 |

## Dates

| Date | Count |
| --- | ---: |
| 2026-05-21 | 507 |
| 2026-05-22 | 394 |
| 2026-05-25 | 51 |
| 2026-05-26 | 212 |
| 2026-05-27 | 260 |
| 2026-05-28 | 282 |
| 2026-05-29 | 340 |
| 2026-06-01 | 397 |
| 2026-06-02 | 227 |
| 2026-06-03 | 514 |
| 2026-06-04 | 399 |
| 2026-06-05 | 1367 |
| 2026-06-08 | 1087 |
| 2026-06-09 | 4480 |
| 2026-06-10 | 4367 |
| 2026-06-11 | 7236 |
| 2026-06-12 | 6157 |
| 2026-06-15 | 1740 |
| 2026-06-16 | 2260 |
| 2026-06-17 | 7267 |
| 2026-06-18 | 3236 |
| 2026-06-19 | 268 |

## Candidate Directions

| Direction | Count |
| --- | ---: |
| long | 12 |
| short | 11 |

## Rejection Reasons

| Rejection reason | Count |
| --- | ---: |
| duplicate_signal | 151 |
| insufficient_context | 5232 |
| no_absorption | 11532 |
| no_setup | 15845 |
| outside_session | 10264 |
| risk_limit | 1 |

## Candidates

| Time | Symbol | Direction | Entry | Stop | Target | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 2026-05-21 11:10:50 | ESU26-CME | long | 7472.25 | 7467.25 | 7483.875 | long absorption reversal; sweep_bar_index=163; sweep_delta=-2; sweep_ratio=1.4; confirmation_close_location=1 |
| 2026-05-21 13:12:42 | ESU26-CME | short | 7496.75 | 7501.75 | 7483.875 | short absorption reversal; sweep_bar_index=261; sweep_delta=1; sweep_ratio=999999; confirmation_close_location=0 |
| 2026-05-22 10:31:37 | ESU26-CME | long | 7552 | 7548.75 | 7562.625 | long absorption reversal; sweep_bar_index=615; sweep_delta=-1; sweep_ratio=999999; confirmation_close_location=1 |
| 2026-05-22 13:37:14 | ESU26-CME | short | 7573.5 | 7579.75 | 7562.625 | short absorption reversal; sweep_bar_index=766; sweep_delta=3; sweep_ratio=999999; confirmation_close_location=0 |
| 2026-05-25 11:10:55 | ESU26-CME | long | 7620.75 | 7618.25 | 7622.375 | long absorption reversal; sweep_bar_index=917; sweep_delta=-165; sweep_ratio=16; confirmation_close_location=1 |
| 2026-05-25 11:14:19 | ESU26-CME | short | 7624.75 | 7627.25 | 7622.375 | short absorption reversal; sweep_bar_index=933; sweep_delta=3; sweep_ratio=999999; confirmation_close_location=0 |
| 2026-05-26 11:02:56 | ESU26-CME | short | 7602.25 | 7605.5 | 7594.375 | short absorption reversal; sweep_bar_index=1038; sweep_delta=3; sweep_ratio=999999; confirmation_close_location=0 |
| 2026-05-26 12:17:53 | ESU26-CME | long | 7585.75 | 7583 | 7594.375 | long absorption reversal; sweep_bar_index=1103; sweep_delta=-2; sweep_ratio=3; confirmation_close_location=1 |
| 2026-05-27 11:25:16 | ESU26-CME | long | 7588.25 | 7585 | 7596.625 | long absorption reversal; sweep_bar_index=1297; sweep_delta=-1; sweep_ratio=1.5; confirmation_close_location=1 |
| 2026-05-29 10:51:24 | ESU26-CME | long | 7653 | 7646.5 | 7661 | long absorption reversal; sweep_bar_index=1793; sweep_delta=-2; sweep_ratio=999999; confirmation_close_location=1 |
| 2026-06-01 11:31:21 | ESU26-CME | short | 7657 | 7661.25 | 7649.125 | short absorption reversal; sweep_bar_index=2241; sweep_delta=8; sweep_ratio=999999; confirmation_close_location=0 |
| 2026-06-03 12:57:17 | ESU26-CME | long | 7638.25 | 7633 | 7656.625 | long absorption reversal; sweep_bar_index=3008; sweep_delta=-13; sweep_ratio=2.083333333; confirmation_close_location=1 |
| 2026-06-04 10:32:05 | ESU26-CME | short | 7626.75 | 7629.25 | 7616.25 | short absorption reversal; sweep_bar_index=3354; sweep_delta=1; sweep_ratio=1.5; confirmation_close_location=0 |
| 2026-06-08 11:18:08 | ESU26-CME | short | 7529.5 | 7533.75 | 7511.25 | short absorption reversal; sweep_bar_index=5388; sweep_delta=2; sweep_ratio=2; confirmation_close_location=0 |
| 2026-06-08 13:15:04 | ESU26-CME | long | 7495.5 | 7488 | 7511.25 | long absorption reversal; sweep_bar_index=5655; sweep_delta=-2; sweep_ratio=3; confirmation_close_location=1 |
| 2026-06-10 10:30:57 | ESU26-CME | short | 7451.25 | 7453.75 | 7424.625 | short absorption reversal; sweep_bar_index=11476; sweep_delta=5; sweep_ratio=3.5; confirmation_close_location=0 |
| 2026-06-10 11:10:45 | ESU26-CME | long | 7397.5 | 7395.5 | 7424.625 | long absorption reversal; sweep_bar_index=12005; sweep_delta=-6; sweep_ratio=7; confirmation_close_location=1 |
| 2026-06-11 10:58:10 | ESU26-CME | long | 7344.75 | 7341.25 | 7370.625 | long absorption reversal; sweep_bar_index=16756; sweep_delta=-4; sweep_ratio=5; confirmation_close_location=1 |
| 2026-06-11 13:29:26 | ESU26-CME | short | 7395.75 | 7400.5 | 7370.625 | short absorption reversal; sweep_bar_index=18995; sweep_delta=37; sweep_ratio=6.285714286; confirmation_close_location=0 |
| 2026-06-12 10:54:39 | ESU26-CME | short | 7487.25 | 7490.75 | 7458.75 | short absorption reversal; sweep_bar_index=24693; sweep_delta=9; sweep_ratio=1.28125; confirmation_close_location=0 |
| 2026-06-17 10:42:16 | ESU26-CME | long | 7581.25 | 7579.25 | 7590.5 | long absorption reversal; sweep_bar_index=32970; sweep_delta=-10; sweep_ratio=1.256410256; confirmation_close_location=1 |
| 2026-06-19 10:46:47 | ESU26-CME | short | 7563 | 7564.75 | 7559.75 | short absorption reversal; sweep_bar_index=42906; sweep_delta=31; sweep_ratio=1.356321839; confirmation_close_location=0 |
| 2026-06-19 12:59:30 | ESU26-CME | long | 7557 | 7554.25 | 7559.75 | long absorption reversal; sweep_bar_index=43032; sweep_delta=-26; sweep_ratio=1.928571429; confirmation_close_location=1 |

## Interpretation

The overlay emitted candidate rows. Evaluate outcomes separately before treating any candidate as strategy evidence.
