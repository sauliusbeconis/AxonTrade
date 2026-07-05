# MNQ Eval-Pass Wave Rider Trailing Candidate Review

Status: focused robustness review for frozen faster-B MNQ candidates.

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique dates: `507`
- reviewed candidates: `6`
- trailing floor: `min(0, high_water - 1000)`
- pass target: `$1250` with `50%` consistency

## Candidate Summary

| Candidate | Qty | Target | Stop | Trades | Net | PF | DD | Worst 2 | Worst 3 | Max Loss Streak | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail | Median Pass Trades | Avg Gap | Max Gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `primary_fast_4mnq_650_450` | 4 | 650 | 450 | 86 | 16136 | 2.02685503 | -1800 | -900 | -1350 | 4 | 38.9% | 3.2% | 80.2% | 15.1% | 4 | 8.41176471d | 57d |
| `same_signal_shorter_window_4mnq_650_450` | 4 | 650 | 450 | 85 | 15486 | 1.98549065 | -1800 | -900 | -1350 | 4 | 36.3% | 3.2% | 80.0% | 15.3% | 4 | 8.51190476d | 57d |
| `lower_target_4mnq_600_450` | 4 | 600 | 450 | 86 | 14412 | 1.92455735 | -1800 | -900 | -1350 | 4 | 30.6% | 3.2% | 75.6% | 17.4% | 4 | 8.41176471d | 57d |
| `lower_target_lower_fail_4mnq_500_450` | 4 | 500 | 450 | 86 | 15112 | 2.17256363 | -1250 | -900 | -938 | 3 | 26.0% | 0.0% | 73.3% | 4.7% | 5 | 8.41176471d | 57d |
| `wide_stop_4mnq_500_700` | 4 | 500 | 700 | 86 | 18464 | 2.35884604 | -2038 | -1400 | -1438 | 3 | 36.1% | 5.9% | 74.4% | 20.9% | 3.5 | 8.41176471d | 57d |
| `smaller_size_3mnq_600_450` | 3 | 600 | 450 | 86 | 13452 | 1.89778757 | -2346 | -900 | -1350 | 5 | 28.8% | 3.2% | 76.7% | 12.8% | 5 | 8.41176471d | 57d |

## Frozen Holdout Comparison

| Candidate | Config | Windows | Trades | Net | PF | DD | Positive | Negative | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `primary_fast_4mnq_650_450` | 120x40 | 9 | 61 | 11662 | 2.05176768 | -1800 | 8 | 1 | 37.2% | 4.4% | 75.4% | 21.3% |
| `primary_fast_4mnq_650_450` | 180x40 | 8 | 50 | 10700 | 2.21590909 | -1350 | 5 | 3 | 39.7% | 5.0% | 78.0% | 16.0% |
| `primary_fast_4mnq_650_450` | 240x60 | 4 | 43 | 10550 | 2.50714286 | -1350 | 4 | 0 | 48.3% | 6.7% | 79.1% | 16.3% |
| `same_signal_shorter_window_4mnq_650_450` | 120x40 | 9 | 61 | 11662 | 2.05176768 | -1800 | 8 | 1 | 37.2% | 4.4% | 75.4% | 21.3% |
| `same_signal_shorter_window_4mnq_650_450` | 180x40 | 8 | 50 | 10700 | 2.21590909 | -1350 | 5 | 3 | 39.7% | 5.0% | 78.0% | 16.0% |
| `same_signal_shorter_window_4mnq_650_450` | 240x60 | 4 | 43 | 10550 | 2.50714286 | -1350 | 4 | 0 | 48.3% | 6.7% | 79.1% | 16.3% |
| `lower_target_4mnq_600_450` | 120x40 | 9 | 61 | 9912 | 1.89393939 | -1800 | 8 | 1 | 30.3% | 4.4% | 68.9% | 24.6% |
| `lower_target_4mnq_600_450` | 180x40 | 8 | 50 | 9200 | 2.04545455 | -1350 | 5 | 3 | 29.7% | 5.0% | 72.0% | 20.0% |
| `lower_target_4mnq_600_450` | 240x60 | 4 | 43 | 9200 | 2.31428571 | -1350 | 4 | 0 | 37.9% | 6.7% | 72.1% | 20.9% |
| `lower_target_lower_fail_4mnq_500_450` | 120x40 | 9 | 61 | 11162 | 2.26295542 | -1250 | 7 | 2 | 30.8% | 0.0% | 73.8% | 6.6% |
| `lower_target_lower_fail_4mnq_500_450` | 180x40 | 8 | 50 | 10950 | 2.67175573 | -1250 | 7 | 1 | 33.4% | 0.0% | 84.0% | 8.0% |
| `lower_target_lower_fail_4mnq_500_450` | 240x60 | 4 | 43 | 10300 | 2.98076923 | -1250 | 4 | 0 | 44.6% | 0.0% | 86.0% | 9.3% |
| `wide_stop_4mnq_500_700` | 120x40 | 9 | 61 | 10764 | 1.99777531 | -1638 | 6 | 3 | 35.0% | 5.0% | 72.1% | 23.0% |
| `wide_stop_4mnq_500_700` | 180x40 | 8 | 50 | 10602 | 2.33358491 | -1100 | 6 | 2 | 35.9% | 0.0% | 78.0% | 12.0% |
| `wide_stop_4mnq_500_700` | 240x60 | 4 | 43 | 9950 | 2.51908397 | -1100 | 4 | 0 | 47.9% | 0.0% | 86.0% | 7.0% |
| `smaller_size_3mnq_600_450` | 120x40 | 9 | 61 | 9339 | 1.87308933 | -2346 | 7 | 1 | 31.4% | 4.4% | 77.0% | 18.0% |
| `smaller_size_3mnq_600_450` | 180x40 | 8 | 50 | 7567.5 | 1.85334912 | -2346 | 5 | 3 | 30.6% | 5.0% | 76.0% | 16.0% |
| `smaller_size_3mnq_600_450` | 240x60 | 4 | 43 | 7567.5 | 2.07067063 | -2346 | 4 | 0 | 39.2% | 6.7% | 76.7% | 16.3% |

## Slippage Stress

| Candidate | Slip Ticks | Target | Stop | Net | DD | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `primary_fast_4mnq_650_450` | 1 | 650 | 450 | 16136 | -1800 | 38.9% | 3.2% | 80.2% | 15.1% |
| `primary_fast_4mnq_650_450` | 2 | 648 | 452 | 15964 | -1808 | 38.9% | 3.2% | 80.2% | 15.1% |
| `primary_fast_4mnq_650_450` | 3 | 646 | 454 | 15792 | -1816 | 38.9% | 3.2% | 80.2% | 15.1% |
| `primary_fast_4mnq_650_450` | 4 | 644 | 456 | 15620 | -1824 | 38.9% | 3.2% | 80.2% | 15.1% |
| `primary_fast_4mnq_650_450` | 5 | 642 | 458 | 15448 | -1832 | 38.9% | 3.2% | 77.9% | 17.4% |
| `primary_fast_4mnq_650_450` | 6 | 640 | 460 | 15276 | -1840 | 38.9% | 3.2% | 77.9% | 17.4% |
| `primary_fast_4mnq_650_450` | 8 | 636 | 464 | 14932 | -1856 | 38.9% | 3.2% | 77.9% | 17.4% |
| `same_signal_shorter_window_4mnq_650_450` | 1 | 650 | 450 | 15486 | -1800 | 36.3% | 3.2% | 80.0% | 15.3% |
| `same_signal_shorter_window_4mnq_650_450` | 2 | 648 | 452 | 15316 | -1808 | 36.3% | 3.2% | 80.0% | 15.3% |
| `same_signal_shorter_window_4mnq_650_450` | 3 | 646 | 454 | 15146 | -1816 | 36.3% | 3.2% | 78.8% | 15.3% |
| `same_signal_shorter_window_4mnq_650_450` | 4 | 644 | 456 | 14976 | -1824 | 36.3% | 3.2% | 78.8% | 15.3% |
| `same_signal_shorter_window_4mnq_650_450` | 5 | 642 | 458 | 14806 | -1832 | 36.3% | 3.2% | 76.5% | 17.6% |
| `same_signal_shorter_window_4mnq_650_450` | 6 | 640 | 460 | 14636 | -1840 | 36.3% | 3.2% | 76.5% | 17.6% |
| `same_signal_shorter_window_4mnq_650_450` | 8 | 636 | 464 | 14296 | -1856 | 36.3% | 3.2% | 76.5% | 17.6% |
| `lower_target_4mnq_600_450` | 1 | 600 | 450 | 14412 | -1800 | 30.6% | 3.2% | 75.6% | 17.4% |
| `lower_target_4mnq_600_450` | 2 | 598 | 452 | 14240 | -1808 | 30.6% | 3.2% | 75.6% | 17.4% |
| `lower_target_4mnq_600_450` | 3 | 596 | 454 | 14068 | -1816 | 30.6% | 3.2% | 75.6% | 17.4% |
| `lower_target_4mnq_600_450` | 4 | 594 | 456 | 13896 | -1824 | 30.6% | 3.2% | 73.3% | 17.4% |
| `lower_target_4mnq_600_450` | 5 | 592 | 458 | 13724 | -1832 | 30.6% | 3.2% | 73.3% | 17.4% |
| `lower_target_4mnq_600_450` | 6 | 590 | 460 | 13552 | -1840 | 30.6% | 3.4% | 72.1% | 18.6% |
| `lower_target_4mnq_600_450` | 8 | 586 | 464 | 13208 | -1856 | 30.6% | 3.4% | 72.1% | 18.6% |
| `lower_target_lower_fail_4mnq_500_450` | 1 | 500 | 450 | 15112 | -1250 | 26.0% | 0.0% | 73.3% | 4.7% |
| `lower_target_lower_fail_4mnq_500_450` | 2 | 498 | 452 | 14940 | -1264 | 24.1% | 0.0% | 70.9% | 4.7% |
| `lower_target_lower_fail_4mnq_500_450` | 3 | 496 | 454 | 14768 | -1278 | 24.1% | 0.0% | 70.9% | 4.7% |
| `lower_target_lower_fail_4mnq_500_450` | 4 | 494 | 456 | 14596 | -1292 | 24.1% | 0.0% | 70.9% | 4.7% |
| `lower_target_lower_fail_4mnq_500_450` | 5 | 492 | 458 | 14424 | -1306 | 24.1% | 0.0% | 70.9% | 4.7% |
| `lower_target_lower_fail_4mnq_500_450` | 6 | 490 | 460 | 14252 | -1320 | 24.1% | 0.0% | 70.9% | 4.7% |
| `lower_target_lower_fail_4mnq_500_450` | 8 | 486 | 464 | 13908 | -1348 | 24.1% | 0.0% | 70.9% | 4.7% |

## Primary Breakdown

| Bucket Type | Bucket | Trades | Net | Wins | Losses |
| --- | --- | ---: | ---: | ---: | ---: |
| year | 2024 | 22 | 3624 | 12 | 10 |
| year | 2025 | 42 | 5912 | 22 | 20 |
| year | 2026 | 22 | 6600 | 15 | 7 |
| quarter | (2024, 3) | 13 | 1074 | 6 | 7 |
| quarter | (2024, 4) | 9 | 2550 | 6 | 3 |
| quarter | (2025, 1) | 13 | 2262 | 7 | 6 |
| quarter | (2025, 2) | 6 | -500 | 2 | 4 |
| quarter | (2025, 3) | 11 | 2950 | 7 | 4 |
| quarter | (2025, 4) | 12 | 1200 | 6 | 6 |
| quarter | (2026, 1) | 13 | 2950 | 8 | 5 |
| quarter | (2026, 2) | 8 | 4100 | 7 | 1 |
| quarter | (2026, 3) | 1 | -450 | 0 | 1 |

## Interpretation

The primary `4 MNQ` `$650/$450` row remains the best replay candidate. It has the strongest frozen holdout pass profile and its target is aligned with the `$650` daily profit objective.

The `4 MNQ` `$500/$450` sibling is the main defensive fallback. It has lower trailing fail and smaller drawdown, but it usually needs more than two winning trades to pass because the target is below the `$625-$650` two-day eval geometry.

The wide-stop rows are rejected for eval use despite high paper net. They increase the chance of damaging the trailing floor and are less aligned with the goal of controlled two-to-several-trade passing.
