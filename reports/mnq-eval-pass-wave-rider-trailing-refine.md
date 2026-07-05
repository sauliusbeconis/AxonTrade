# MNQ Eval-Pass Wave Rider Trailing Refinement

Status: trailing-drawdown refinement for the faster MNQ B setup.

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique dates: `507`
- base signals: `505`
- trailing floor: `min(0, high_water - 1000)`
- pass target: `$1250` with `50%` consistency
- calendar attempts use a `30` calendar-day horizon and `12` max trade days

## Best Trailing-Aware Row

| Metric | Value |
| --- | ---: |
| Strategy | `cadence_trailing:tue_wed:short:1000_1230:none` |
| Quantity | `4` MNQ |
| Target / stop | `$650 / $450` |
| Target / stop points | `82 / 55.5` |
| Trades | `86` |
| Full-sample net | `$16136` |
| Latest-year net | `$6600` |
| Worst quarter | `$-500` |
| Trade-sequence max DD | `$-1800` |
| Fixed calendar pass / fail | `38.9% / 1.4%` |
| Trailing calendar pass / fail / timeout | `38.9% / 3.2% / 58.0%` |
| Trailing signal pass / fail / timeout | `80.2% / 15.1% / 4.7%` |
| Trailing median pass time | `16` calendar days, `2` trade days |

## Strict Rows

Rows shown here have trailing calendar pass `>=30%`, trailing calendar fail `<=8%`, trailing signal fail `<=18%`, and at least `75` trades.

| Rank | Qty | Target | Stop | Trades | Latest Net | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail | DD | Worst Q | Strategy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 4 | 650 | 450 | 86 | 6600 | 38.9% | 3.2% | 80.2% | 15.1% | -1800 | -500 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 2 | 4 | 650 | 450 | 85 | 6600 | 36.3% | 3.2% | 80.0% | 15.3% | -1800 | -500 | `cadence_trailing:tue_wed:short:1000_1130:none` |
| 3 | 3 | 651 | 450 | 86 | 3960 | 32.5% | 6.5% | 76.7% | 17.4% | -2295 | -916.5 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 4 | 4 | 600 | 450 | 86 | 5850 | 30.6% | 3.2% | 75.6% | 17.4% | -1800 | -600 | `cadence_trailing:tue_wed:short:1000_1230:none` |

## Top Ranked Rows

| Rank | Qty | Target | Stop | Trades | Latest Net | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail | DD | Worst Q | Strategy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 4 | 650 | 450 | 86 | 6600 | 38.9% | 3.2% | 80.2% | 15.1% | -1800 | -500 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 2 | 4 | 650 | 450 | 85 | 6600 | 36.3% | 3.2% | 80.0% | 15.3% | -1800 | -500 | `cadence_trailing:tue_wed:short:1000_1130:none` |
| 3 | 3 | 651 | 450 | 86 | 3960 | 32.5% | 6.5% | 76.7% | 17.4% | -2295 | -916.5 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 4 | 4 | 600 | 450 | 86 | 5850 | 30.6% | 3.2% | 75.6% | 17.4% | -1800 | -600 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 5 | 5 | 650 | 800 | 178 | 11665 | 57.6% | 33.9% | 61.8% | 35.4% | -6300 | -2300 | `cadence_trailing:tue_wed:both:1000_1045:none` |
| 6 | 4 | 550 | 700 | 178 | 9270 | 55.4% | 33.1% | 61.8% | 36.0% | -5890 | -2200 | `cadence_trailing:tue_wed:both:1000_1045:none` |
| 7 | 4 | 550 | 750 | 178 | 8620 | 55.2% | 34.5% | 60.1% | 37.6% | -6788 | -2750 | `cadence_trailing:tue_wed:both:1000_1045:none` |
| 8 | 5 | 350 | 800 | 178 | 8365 | 55.0% | 29.0% | 61.2% | 33.1% | -5850 | -1850 | `cadence_trailing:tue_wed:both:1000_1045:none` |
| 9 | 5 | 650 | 800 | 129 | 6057.5 | 54.6% | 29.2% | 68.2% | 31.0% | -4647.5 | -107.5 | `cadence_trailing:no_thu_fri:short:1000_1230:none` |
| 10 | 5 | 425 | 800 | 178 | 7690 | 54.0% | 32.5% | 59.0% | 36.0% | -6100 | -2100 | `cadence_trailing:tue_wed:both:1000_1045:none` |
| 11 | 5 | 650 | 800 | 127 | 6057.5 | 53.8% | 30.0% | 67.7% | 31.5% | -4647.5 | -107.5 | `cadence_trailing:no_thu_fri:short:1000_1130:none` |
| 12 | 5 | 475 | 800 | 178 | 6990 | 53.6% | 33.3% | 58.4% | 37.1% | -5500 | -1500 | `cadence_trailing:tue_wed:both:1000_1045:none` |

## Best Row Slippage Stress

| Slip Ticks | Target | Stop | Net | Latest Net | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 650 | 450 | 16136 | 6600 | 38.9% | 3.2% | 80.2% | 15.1% |
| 2 | 648 | 452 | 15964 | 6556 | 38.9% | 3.2% | 80.2% | 15.1% |
| 3 | 646 | 454 | 15792 | 6512 | 38.9% | 3.2% | 80.2% | 15.1% |
| 4 | 644 | 456 | 15620 | 6468 | 38.9% | 3.2% | 80.2% | 15.1% |
| 5 | 642 | 458 | 15448 | 6424 | 38.9% | 3.2% | 77.9% | 17.4% |
| 6 | 640 | 460 | 15276 | 6380 | 38.9% | 3.2% | 77.9% | 17.4% |

## Best Row Rolling Holdout

| Window | Windows | Positive | Negative | Net | Worst Window | Trades | Max DD | Trail Sig Pass | Trail Sig Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 120x40 | 9 | 8 | 1 | 11662 | -250 | 61 | -1800 | 75.4% | 21.3% |
| 180x40 | 8 | 5 | 3 | 10700 | -950 | 50 | -1350 | 78.0% | 16.0% |
| 240x60 | 4 | 4 | 0 | 10550 | 550 | 43 | -1350 | 79.1% | 16.3% |

Best row year breakdown:

| Bucket | Trades | Net | Wins | Losses |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 22 | 3624 | 12 | 10 |
| 2025 | 42 | 5912 | 22 | 20 |
| 2026 | 22 | 6600 | 15 | 7 |

Best row quarter breakdown:

| Bucket | Trades | Net | Wins | Losses |
| --- | ---: | ---: | ---: | ---: |
| (2024, 3) | 13 | 1074 | 6 | 7 |
| (2024, 4) | 9 | 2550 | 6 | 3 |
| (2025, 1) | 13 | 2262 | 7 | 6 |
| (2025, 2) | 6 | -500 | 2 | 4 |
| (2025, 3) | 11 | 2950 | 7 | 4 |
| (2025, 4) | 12 | 1200 | 6 | 6 |
| (2026, 1) | 13 | 2950 | 8 | 5 |
| (2026, 2) | 8 | 4100 | 7 | 1 |
| (2026, 3) | 1 | -450 | 0 | 1 |

Best row weekday breakdown:

| Bucket | Trades | Net | Wins | Losses |
| --- | ---: | ---: | ---: | ---: |
| Tue | 48 | 7936 | 26 | 22 |
| Wed | 38 | 8200 | 23 | 15 |

## Interpretation

The faster B setup improved materially after optimizing against trailing drawdown instead of fixed loss. The best row is a Tuesday/Wednesday short-only setup with a larger target than stop, so two winning days can satisfy the eval objective while a stopped trade remains below half the max-loss limit.

Follow-up trailing walk-forward validation improved the case for the locked row: `120x40`, `180x40`, and `240x60` frozen holdout slices all stayed positive, while adaptive selection was weaker and less stable. The all-candidate frozen leaderboard ranked the same `4 MNQ` `$650/$450` row `#1` of `6336` faster B rows under the robustness screen. See `reports/mnq-eval-pass-wave-rider-trailing-walk-forward.md`.

This is still not implementation-ready. It has only `86` trades, one negative rolling holdout window in the `120x40` view, and a negative `2025 Q2` quarter. It should be treated as the best B research lead for replay/mechanics validation, not a bot build instruction.
