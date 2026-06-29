# Sierra Delta Impulse 3-Min Fixed Row Robustness

This report checks whether the current fixed Sierra overlay row is broad enough
to keep collecting:

`5 / 10 / 8 / initial`

## Sources

- Outcome CSV:
  `data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv`
- Exit sweep:
  `reports/sierra-delta-impulse-3min-large-scaled-exit-sweep.csv`
- Main summary:
  `reports/sierra-delta-impulse-3min-large-sample-outcomes.md`
- CME 2026 trading-hours reference, retrieved 2026-06-29:
  `https://www.cmegroup.com/trading-hours.html`

## Fixed Row Result

| Metric | Value |
| --- | ---: |
| Trades | 78 |
| Net USD | 3104 |
| Average Net USD | 39.79 |
| Runner target hits | 47 |
| Full stops | 20 |
| Runner initial-stop exits | 9 |
| End/no-following exits | 2 |

Direction split:

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| Long | 41 | 4463 |
| Short | 37 | -1359 |

## Day Stability

| Date | Trades | Net USD | Cumulative Net USD |
| --- | ---: | ---: | ---: |
| 2026-06-10 | 6 | 258 | 258 |
| 2026-06-11 | 6 | -642 | -384 |
| 2026-06-12 | 6 | -642 | -1026 |
| 2026-06-15 | 6 | 258 | -768 |
| 2026-06-16 | 6 | 1008 | 240 |
| 2026-06-17 | 6 | -1392 | -1152 |
| 2026-06-18 | 6 | 1008 | -144 |
| 2026-06-19 | 6 | -1792 | -1936 |
| 2026-06-22 | 6 | -642 | -2578 |
| 2026-06-23 | 6 | 1008 | -1570 |
| 2026-06-24 | 6 | 1008 | -562 |
| 2026-06-25 | 6 | 1008 | 446 |
| 2026-06-26 | 6 | 2658 | 3104 |

The equity curve is still weak. It was down `-2578` after 2026-06-22 and
down `-1570` after 2026-06-23. The final positive result depends heavily on
the last three dates adding `4674`.

## Holiday Handling

2026-06-19 is listed by CME as a Juneteenth holiday date. That same date is the
only sample date with `end_of_session` and `no_following_bar` exits.

Excluding 2026-06-19 changes the fixed-row result to:

| Scope | Trades | Net USD | Long Net USD | Short Net USD |
| --- | ---: | ---: | ---: | ---: |
| All dates | 78 | 3104 | 4463 | -1359 |
| Exclude 2026-06-19 | 72 | 4896 | 6791 | -1895 |

Holiday/early-close dates should be flagged before any later acceptance test.
Excluding the date improves total net, but the short side is still negative.

## Time Windows

Excluding 2026-06-19:

| NY Time Window | Trades | Net USD |
| --- | ---: | ---: |
| 10:00-10:45 | 23 | -611 |
| 10:45-11:00 | 11 | 3973 |
| 11:00-11:30 | 20 | 910 |
| 11:30-12:00 | 13 | -1441 |
| 12:00-13:00 | 5 | 2065 |

The 10:45-11:00 window is the strongest segment, but it is too thin to promote
as a rule. The useful research lead is broader: avoid blind full-day routing and
test session-time gates only after a larger sample exists.

## Parameter Shelf

Top all-direction `initial` rows:

| First Target | Stop | Runner Target | Net USD |
| ---: | ---: | ---: | ---: |
| 5 | 10 | 8 | 3104 |
| 4 | 10 | 8 | 2279 |
| 4 | 10 | 5 | 1979 |
| 3 | 10 | 8 | 1279 |
| 3 | 10 | 5 | 979 |

Nearby cells around the current row:

| First Target | Stop | Runner Target | Net USD |
| ---: | ---: | ---: | ---: |
| 4 | 8 | 8 | -646 |
| 4 | 8 | 10 | -2946 |
| 4 | 10 | 8 | 2279 |
| 4 | 10 | 10 | -1221 |
| 5 | 8 | 8 | 54 |
| 5 | 8 | 10 | -2246 |
| 5 | 10 | 8 | 3104 |
| 5 | 10 | 10 | -396 |

This is not a broad plateau. The setup strongly prefers a `10` point stop and
an `8` point runner target in this sample. That is a parameter-fit warning.

## Fixed Row Rolling Windows

The earlier walk-forward file uses train-window parameter selection. This check
holds the current fixed row constant and only rolls dates.

Using `4` train dates, `2` holdout dates, and a `2` date step:

| Window | Train Dates | Train Net USD | Holdout Dates | Holdout Net USD |
| ---: | --- | ---: | --- | ---: |
| 1 | 2026-06-10 to 2026-06-15 | -768 | 2026-06-16 to 2026-06-17 | -384 |
| 3 | 2026-06-12 to 2026-06-17 | -768 | 2026-06-18 to 2026-06-19 | -784 |
| 5 | 2026-06-16 to 2026-06-19 | -1168 | 2026-06-22 to 2026-06-23 | 366 |
| 7 | 2026-06-18 to 2026-06-23 | -418 | 2026-06-24 to 2026-06-25 | 2016 |

Fixed-row rolling holdout total: `48` trades, `1214` net USD.

Excluding 2026-06-19:

| Window | Train Dates | Train Net USD | Holdout Dates | Holdout Net USD |
| ---: | --- | ---: | --- | ---: |
| 1 | 2026-06-10 to 2026-06-15 | -768 | 2026-06-16 to 2026-06-17 | -384 |
| 3 | 2026-06-12 to 2026-06-17 | -768 | 2026-06-18 to 2026-06-22 | 366 |
| 5 | 2026-06-16 to 2026-06-22 | -18 | 2026-06-23 to 2026-06-24 | 2016 |
| 7 | 2026-06-18 to 2026-06-24 | 2382 | 2026-06-25 to 2026-06-26 | 3666 |

Holiday-excluded fixed-row rolling holdout total: `48` trades, `5664` net USD.

This is better than selection-based walk-forward, but it still does not prove
stability. The early train windows are negative, and the later positive regime
dominates the result.

## Risk Gate Checks

Simple sequential daily gates on the fixed row:

| Gate | Trades | Net USD |
| --- | ---: | ---: |
| No gate | 78 | 3104 |
| First 3 signals/day | 39 | 2377 |
| Before 11:00 | 36 | 3148 |
| Stop after daily profit 500 | 30 | 5190 |
| Stop after daily profit 1000 | 60 | 5030 |
| Stop after daily loss 1000 | 60 | 1480 |

Profit gates look better in-sample, but they are especially easy to overfit.
Treat them as risk-control candidates, not as evidence of strategy quality.

## Conclusion

Keep collecting `5 / 10 / 8 / initial`, but do not promote it to live routing.
The current edge is still too dependent on:

- the last few dates,
- a narrow parameter shelf,
- holiday/early-close handling,
- and a still-negative short side.

Next research should add automatic holiday flags and repeat this fixed-row
holdout check on a larger export before any new default changes.
