# MNQ Eval-Pass Wave Rider Cadence Validation

Status: faster B setup under validation; not implementation-ready.

This validates frozen rows from
`reports/mnq-eval-pass-wave-rider-cadence-refine.md`.

## Candidate A: Low-Fail Short-Only B Setup

| Metric | Value |
| --- | ---: |
| Strategy | `cadence_refine:no_thu_fri:short:1000_1230:none` |
| Quantity | `4` MNQ |
| Target / stop | `$350 / $650` |
| Target / stop points | `44.5 / 80.5` |
| Trades | `129` |
| Full-sample net | `$17496` |
| Latest-year net | `$4200` |
| Worst quarter | `$350` |
| Trade-sequence max DD | `-$2118` |
| Calendar-start pass / fail / timeout | `30.4% / 4.1% / 65.5%` |
| Signal-start pass / fail | `66.7% / 13.2%` |
| Median pass time | `21.5` calendar days, `4` traded days |
| Median signal gap | `3.5` trading days |
| Max signal gap | `14` trading days |

Slippage stress keeps the same target/stop point distances and changes only
transaction cost from `1` to `6` total slippage ticks per contract.

| Slip Ticks | Target | Stop | Net | Latest-Year Net | Calendar Pass | Calendar Fail | Signal Pass | Signal Fail |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 350 | 650 | 17496 | 4200 | 30.4% | 4.1% | 66.7% | 13.2% |
| 2 | 348 | 652 | 17238 | 4136 | 30.4% | 4.1% | 66.7% | 13.2% |
| 3 | 346 | 654 | 16980 | 4072 | 30.4% | 4.1% | 66.7% | 13.2% |
| 4 | 344 | 656 | 16722 | 4008 | 30.4% | 4.1% | 66.7% | 13.2% |
| 5 | 342 | 658 | 16464 | 3944 | 30.4% | 4.1% | 65.9% | 13.2% |
| 6 | 340 | 660 | 16206 | 3880 | 30.4% | 4.1% | 65.9% | 13.2% |

Rolling holdout:

| Window | Windows | Positive | Negative | Net | Worst Window | Trades | Max DD | Signal Pass | Signal Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `120x40` | 9 | 7 | 2 | 10074 | -1100 | 91 | -2118 | 62.6% | 12.1% |
| `180x40` | 8 | 7 | 1 | 8774 | -1550 | 73 | -2118 | 58.9% | 8.2% |
| `240x60` | 4 | 4 | 0 | 7924 | 1632 | 62 | -1168 | 64.5% | 1.6% |

Breakdown:

| Bucket | Trades | Net | Wins | Losses |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 34 | 6022 | 28 | 6 |
| 2025 | 63 | 7274 | 47 | 16 |
| 2026 | 32 | 4200 | 25 | 7 |
| 2024 Q3 | 19 | 4960 | 17 | 2 |
| 2024 Q4 | 15 | 1062 | 11 | 4 |
| 2025 Q1 | 20 | 2000 | 15 | 5 |
| 2025 Q2 | 10 | 500 | 7 | 3 |
| 2025 Q3 | 14 | 2732 | 11 | 3 |
| 2025 Q4 | 19 | 2042 | 14 | 5 |
| 2026 Q1 | 16 | 1600 | 12 | 4 |
| 2026 Q2 | 15 | 2250 | 12 | 3 |

## Candidate B: Higher-Pass Tuesday/Wednesday Setup

| Metric | Value |
| --- | ---: |
| Strategy | `cadence_refine:tue_wed:both:1000_1045:none` |
| Quantity | `3` MNQ |
| Target / stop | `$351 / $499.5` |
| Trades | `178` |
| Full-sample net | `$14191.5` |
| Latest-year net | `$6270` |
| Worst quarter | `-$498` |
| Trade-sequence max DD | `-$2781` |
| Calendar-start pass / fail / timeout | `40.0% / 11.6% / 48.3%` |
| Signal-start pass / fail | `59.0% / 17.4%` |
| Median pass time | `21` calendar days, `6` traded days |
| Median signal gap | `4` trading days |

This row passes more often from random calendar starts but is less clean:

- slippage at `6` total ticks degrades calendar pass/fail to `33.7% / 12.8%`;
- rolling holdouts have `6/9`, `6/8`, and `3/4` positive windows;
- signal-start failure is materially worse than the short-only row.

## Candidate C: Lower-Fail Tuesday/Wednesday Setup

| Metric | Value |
| --- | ---: |
| Strategy | `cadence_refine:tue_wed:both:1000_1230:move_le125` |
| Quantity | `3` MNQ |
| Target / stop | `$351 / $499.5` |
| Trades | `172` |
| Full-sample net | `$13821` |
| Latest-year net | `$4312.5` |
| Worst quarter | `-$483` |
| Trade-sequence max DD | `-$2592` |
| Calendar-start pass / fail / timeout | `36.9% / 9.7% / 53.5%` |
| Signal-start pass / fail | `61.0% / 15.1%` |
| Median pass time | `20` calendar days, `6` traded days |

This row is a compromise between A and B, but slippage stress pushes fail rate
above `12%` and lowers calendar pass to about `30.6%` at `6` total ticks.

## Interpretation

The short-only B setup is the cleanest faster-cadence lead so far. It is not a
two-day pass strategy. It is a wait-for-signal, multi-trade eval path:

- activate only after a valid setup appears;
- expect a median `4` traded days to pass after the first signal;
- expect a median `21.5` calendar days because signals are not daily;
- accept that many random calendar starts timeout rather than fail.

The useful result is the low eval-fail rate, not speed. This is worth deeper
walk-forward and replay validation, but not ACSIL implementation yet.
