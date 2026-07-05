# MNQ Eval-Pass Combined A+B Research

Status: combined sparse A+ and faster-B policy research for MNQ eval pass.

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique dates: `507`
- eval trailing floor: `min(0, high_water - 1000)`
- pass target: `$1250` with `50%` consistency
- calendar attempts use `30` calendar days and `12` max trade days

## Overlap

- A+ signals: `43`
- B signals: `86`
- exact same-bar overlap: `1`
- same-date overlap: `7` (`16.3%` of A+, `8.1%` of B)

## Policy Summary

| Policy | Trades | A+ | B | Net | Win | PF | DD | Worst 2 | Worst 3 | Max Loss Streak | Cal Pass | Cal Fail | Cal Med Days | Cal Med Trades | Sig Pass | Sig Fail | Sig Med Days | Sig Med Trades | Avg Gap | Max Gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `a_plus_only` | 43 | 43 | 0 | 14982 | 74.4% | 2.816 | -1500 | -1500 | -774 | 2 | 29.4% | 3.0% | 16 | 2 | 90.7% | 4.7% | 33 | 2 | 16.61904762d | 82d |
| `b_fast_only` | 86 | 0 | 86 | 16136 | 57.0% | 2.02685503 | -1800 | -900 | -1350 | 4 | 38.9% | 3.2% | 16 | 2 | 80.2% | 15.1% | 29 | 4 | 8.41176471d | 57d |
| `b_defensive_only` | 86 | 0 | 86 | 15112 | 65.1% | 2.17256363 | -1250 | -900 | -938 | 3 | 26.0% | 0.0% | 21.5 | 3 | 73.3% | 4.7% | 36 | 5 | 8.41176471d | 57d |
| `ab_take_all_fast` | 129 | 43 | 86 | 31118 | 62.8% | 2.29853113 | -1950 | -1500 | -1950 | 3 | 53.3% | 10.1% | 16 | 3 | 82.9% | 10.1% | 21 | 4 | 5.90909091d | 24d |
| `ab_earliest_one_per_day_fast` | 122 | 36 | 86 | 28988 | 62.3% | 2.29042023 | -1950 | -1500 | -1950 | 3 | 52.5% | 5.5% | 17 | 3 | 85.2% | 8.2% | 21.5 | 4 | 5.90909091d | 24d |
| `ab_a_priority_one_per_day_fast` | 122 | 43 | 79 | 28768 | 62.3% | 2.24731183 | -2100 | -1500 | -1950 | 4 | 53.3% | 10.1% | 16 | 3 | 81.1% | 11.5% | 21 | 4 | 5.90909091d | 24d |
| `ab_earliest_one_per_day_defensive` | 122 | 36 | 86 | 27964 | 68.0% | 2.42397393 | -1950 | -1500 | -1950 | 3 | 50.3% | 2.8% | 19 | 3 | 91.8% | 3.3% | 25.5 | 5 | 5.90909091d | 24d |

## Frozen Holdout

| Policy | Config | Windows | Trades | Net | PF | DD | Positive | Negative | Cal Pass | Cal Fail | Sig Pass | Sig Fail |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `a_plus_only` | 120x40 | 9 | 26 | 11496 | 4.0656 | -774 | 6 | 1 | 27.8% | 0.0% | 96.2% | 0.0% |
| `a_plus_only` | 180x40 | 8 | 23 | 7842 | 2.74266667 | -1500 | 6 | 2 | 22.8% | 4.7% | 82.6% | 8.7% |
| `a_plus_only` | 240x60 | 4 | 12 | 5760 | 4.84 | -774 | 4 | 0 | 17.5% | 0.0% | 91.7% | 0.0% |
| `b_fast_only` | 120x40 | 9 | 61 | 11662 | 2.05176768 | -1800 | 8 | 1 | 37.2% | 4.4% | 75.4% | 21.3% |
| `b_fast_only` | 180x40 | 8 | 50 | 10700 | 2.21590909 | -1350 | 5 | 3 | 39.7% | 5.0% | 78.0% | 16.0% |
| `b_fast_only` | 240x60 | 4 | 43 | 10550 | 2.50714286 | -1350 | 4 | 0 | 48.3% | 6.7% | 79.1% | 16.3% |
| `b_defensive_only` | 120x40 | 9 | 61 | 11162 | 2.26295542 | -1250 | 7 | 2 | 30.8% | 0.0% | 73.8% | 6.6% |
| `b_defensive_only` | 180x40 | 8 | 50 | 10950 | 2.67175573 | -1250 | 7 | 1 | 33.4% | 0.0% | 84.0% | 8.0% |
| `b_defensive_only` | 240x60 | 4 | 43 | 10300 | 2.98076923 | -1250 | 4 | 0 | 44.6% | 0.0% | 86.0% | 9.3% |
| `ab_earliest_one_per_day_fast` | 120x40 | 9 | 83 | 23206 | 2.73984106 | -1350 | 9 | 0 | 53.6% | 4.4% | 86.7% | 8.4% |
| `ab_earliest_one_per_day_fast` | 180x40 | 8 | 69 | 18590 | 2.57542373 | -1950 | 7 | 1 | 52.2% | 8.8% | 82.6% | 14.5% |
| `ab_earliest_one_per_day_fast` | 240x60 | 4 | 52 | 17084 | 3.44057143 | -1350 | 4 | 0 | 57.5% | 6.7% | 84.6% | 13.5% |
| `ab_a_priority_one_per_day_fast` | 120x40 | 9 | 83 | 21658 | 2.50528218 | -2100 | 9 | 0 | 53.6% | 10.8% | 81.9% | 13.3% |
| `ab_a_priority_one_per_day_fast` | 180x40 | 8 | 69 | 17042 | 2.32622568 | -2100 | 7 | 1 | 50.9% | 15.9% | 75.4% | 20.3% |
| `ab_a_priority_one_per_day_fast` | 240x60 | 4 | 52 | 15460 | 2.92049689 | -2100 | 4 | 0 | 55.0% | 16.2% | 76.9% | 21.2% |
| `ab_earliest_one_per_day_defensive` | 120x40 | 9 | 83 | 22706 | 3.04779942 | -938 | 9 | 0 | 55.6% | 0.0% | 97.6% | 0.0% |
| `ab_earliest_one_per_day_defensive` | 180x40 | 8 | 69 | 18840 | 2.97277487 | -1950 | 8 | 0 | 52.2% | 4.4% | 89.9% | 5.8% |
| `ab_earliest_one_per_day_defensive` | 240x60 | 4 | 52 | 16834 | 4.23730769 | -900 | 4 | 0 | 58.3% | 0.0% | 96.2% | 0.0% |

## Combined Candidate Breakdown

| Bucket Type | Bucket | Trades | Net | Wins | Losses |
| --- | --- | ---: | ---: | ---: | ---: |
| year | 2024 | 34 | 6432 | 20 | 14 |
| year | 2025 | 58 | 13100 | 35 | 23 |
| year | 2026 | 30 | 9456 | 21 | 9 |
| quarter | (2024, 3) | 17 | 1026 | 8 | 9 |
| quarter | (2024, 4) | 17 | 5406 | 12 | 5 |
| quarter | (2025, 1) | 18 | 4416 | 11 | 7 |
| quarter | (2025, 2) | 15 | 3082 | 9 | 6 |
| quarter | (2025, 3) | 12 | 3676 | 8 | 4 |
| quarter | (2025, 4) | 13 | 1926 | 7 | 6 |
| quarter | (2026, 1) | 16 | 5128 | 11 | 5 |
| quarter | (2026, 2) | 13 | 4778 | 10 | 3 |
| quarter | (2026, 3) | 1 | -450 | 0 | 1 |

## Eval Time Estimate

For the build candidate `ab_earliest_one_per_day_fast`:

- from a random calendar start, historical pass rate was `52.5%` within the `30`-day eval horizon, with fail rate `5.5%`;
- successful random-start attempts had median pass time `17` calendar days and `3` trade days;
- from a valid signal start, historical pass rate was `85.2%`, fail rate `8.2%`, and median pass time `21.5` calendar days / `4` trade days.

Practical expectation: if the account is started on a random day, a reasonable planning estimate is about `2-3` calendar weeks when it passes. If started on a valid signal day, the median historical pass path was about `4` traded signals, not a guaranteed two-day pass.

## Decision

The build candidate is `ab_earliest_one_per_day_fast`: one combined bot, A+ and B signals both enabled, exactly one trade per day, earliest valid signal wins, exact same-bar ties choose B for lower per-trade risk.

`ab_take_all_fast` is rejected for eval routing because it improves calendar pass rate but pushes fail rate to an unacceptable level.
