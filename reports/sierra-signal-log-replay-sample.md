# Sierra Signal Log Report

This report summarizes indicator-only Sierra Chart signal-log rows.
It is research-only and does not imply a tradable strategy.

## Source

- Signal log: `data/processed/AxonTrade_ES_overlay_signal_log_replay_sample.csv`

## Summary

| Metric | Value |
| --- | ---: |
| Total rows | 808 |
| Candidate signals | 2 |
| Rejected signals | 806 |
| First row bar time | 2026-06-18 16:14:35 |
| Last row bar time | 2026-06-17 16:14:54 |
| Earliest bar time | 2026-06-16 16:14:33 |
| Latest bar time | 2026-06-19 12:59:58 |

## Symbols

| Symbol | Count |
| --- | ---: |
| ESU26-CME | 808 |

## Strategy IDs

| Strategy ID | Count |
| --- | ---: |
| liquidity_sweep_absorption_reversal | 808 |

## Event Types

| Event type | Count |
| --- | ---: |
| candidate_signal | 2 |
| rejected_signal | 806 |

## Dates

| Date | Count |
| --- | ---: |
| 2026-06-16 | 1 |
| 2026-06-17 | 706 |
| 2026-06-18 | 1 |
| 2026-06-19 | 100 |

## Candidate Directions

| Direction | Count |
| --- | ---: |
| long | 2 |

## Rejection Reasons

| Rejection reason | Count |
| --- | ---: |
| duplicate_signal | 3 |
| insufficient_context | 241 |
| no_absorption | 105 |
| no_setup | 220 |
| outside_session | 237 |

## Candidates

| Time | Symbol | Direction | Entry | Stop | Target | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 2026-06-17 10:42:28 | ESU26-CME | long | 7581.25 | 7579.25 | 7590.5 | long absorption reversal; sweep_bar_index=32970; sweep_delta=-10; sweep_ratio=1.256410256; confirmation_close_location=1 |
| 2026-06-19 12:59:58 | ESU26-CME | long | 7556.75 | 7553.75 | 7559.75 | long absorption reversal; sweep_bar_index=43046; sweep_delta=-43; sweep_ratio=999999; confirmation_close_location=1 |

## Interpretation

The overlay emitted candidate rows. Evaluate outcomes separately before treating any candidate as strategy evidence.
