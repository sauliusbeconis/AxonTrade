# Sierra Delta Impulse 3-Min Fixed Row Robustness

This report checks whether the current fixed Sierra overlay row is broad enough
to keep collecting:

`5 / 10 / 8 / initial`

## Sources

- Outcome CSV:
  `data/processed/AxonTrade_ES_delta_impulse_3min_larger_scaled_outcomes_all_5_10_8_initial.csv`
- Exit sweep:
  `reports/sierra-delta-impulse-3min-larger-scaled-exit-sweep.csv`
- Main summary:
  `reports/sierra-delta-impulse-3min-large-sample-outcomes.md`
- Holiday calendar:
  `config/research/cme_equity_index_holidays_2026.csv`
- CME trading-hours reference, retrieved 2026-06-29:
  `https://www.cmegroup.com/trading-hours.html`

## Fixed Row Result

| Metric | Value |
| --- | ---: |
| Trades | 169 |
| Net USD | -16358 |
| Average Net USD | -96.79 |
| Runner target hits | 90 |
| Full stops | 59 |
| Runner initial-stop exits | 16 |
| End/no-following exits | 3 |

Direction split:

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| Long | 100 | -8025 |
| Short | 69 | -8333 |

## Day Stability

| Date | Trades | Net USD | Cumulative Net USD |
| --- | ---: | ---: | ---: |
| 2026-03-23 | 3 | -1521 | -1521 |
| 2026-03-25 | 3 | 129 | -1392 |
| 2026-03-27 | 1 | 593 | -799 |
| 2026-04-02 | 1 | 593 | -206 |
| 2026-04-07 | 2 | -464 | -670 |
| 2026-04-23 | 1 | -307 | -977 |
| 2026-04-24 | 2 | -2114 | -3091 |
| 2026-05-01 | 3 | -2421 | -5512 |
| 2026-05-04 | 1 | -307 | -5819 |
| 2026-05-05 | 1 | -1057 | -6876 |
| 2026-05-13 | 3 | 1779 | -5097 |
| 2026-05-14 | 4 | 2372 | -2725 |
| 2026-05-15 | 2 | -2114 | -4839 |
| 2026-05-18 | 3 | -1521 | -6360 |
| 2026-05-20 | 6 | -867 | -7227 |
| 2026-05-21 | 3 | 129 | -7098 |
| 2026-05-22 | 2 | 1186 | -5912 |
| 2026-05-26 | 1 | -307 | -6219 |
| 2026-05-27 | 3 | -3171 | -9390 |
| 2026-05-28 | 1 | -1057 | -10447 |
| 2026-05-29 | 2 | 1186 | -9261 |
| 2026-06-01 | 6 | -3942 | -13203 |
| 2026-06-02 | 3 | -1521 | -14724 |
| 2026-06-03 | 4 | -4228 | -18952 |
| 2026-06-04 | 6 | 1908 | -17044 |
| 2026-06-05 | 6 | 1908 | -15136 |
| 2026-06-08 | 6 | -3042 | -18178 |
| 2026-06-09 | 6 | -642 | -18820 |
| 2026-06-10 | 6 | 258 | -18562 |
| 2026-06-11 | 6 | -642 | -19204 |
| 2026-06-12 | 6 | -642 | -19846 |
| 2026-06-15 | 6 | 258 | -19588 |
| 2026-06-16 | 6 | 1008 | -18580 |
| 2026-06-17 | 6 | -1392 | -19972 |
| 2026-06-18 | 6 | 1008 | -18964 |
| 2026-06-19 | 6 | -1792 | -20756 |
| 2026-06-22 | 6 | -642 | -21398 |
| 2026-06-23 | 6 | 1008 | -20390 |
| 2026-06-24 | 6 | 1008 | -19382 |
| 2026-06-25 | 6 | 1008 | -18374 |
| 2026-06-26 | 6 | 2658 | -15716 |
| 2026-06-29 | 6 | -642 | -16358 |

The equity curve was down `-21398` at its weakest point and finished at `-16358`.

## Holiday Handling

Supplied holiday/early-close dates: `2026-06-19`. These dates are excluded in the holiday-adjusted diagnostics below.

| Scope | Trades | Net USD | Long Net USD | Short Net USD |
| --- | ---: | ---: | ---: | ---: |
| All dates | 169 | -16358 | -8025 | -8333 |
| Exclude holidays | 163 | -14566 | -5697 | -8869 |

Holiday/early-close dates are calendar-driven for later acceptance tests.

## Time Windows

| NY Time Window | Trades | Net USD |
| --- | ---: | ---: |
| 10:00-10:45 | 44 | -7358 |
| 10:45-11:00 | 21 | 1653 |
| 11:00-11:30 | 32 | -5174 |
| 11:30-12:00 | 23 | 1189 |
| 12:00-13:00 | 16 | 3488 |

The time-window table is diagnostic only. Do not promote a thin time slice as a rule without a larger sample.

## Parameter Shelf

Top all-direction `initial` rows:

| First Target | Stop | Runner Target | Net USD |
| ---: | ---: | ---: | ---: |
| 4 | 5 | 15 | -9595.5 |
| 4 | 2 | 10 | -10833 |
| 4 | 5 | 8 | -10883 |
| 4 | 2 | 8 | -11233 |
| 4 | 5 | 10 | -11333 |

Nearby cells around the current row:

| First Target | Stop | Runner Target | Net USD |
| ---: | ---: | ---: | ---: |
| 4 | 8 | 8 | -12108 |
| 4 | 8 | 10 | -14008 |
| 4 | 10 | 8 | -13383 |
| 4 | 10 | 10 | -16583 |
| 5 | 8 | 8 | -15058 |
| 5 | 8 | 10 | -16958 |
| 5 | 10 | 8 | -16358 |
| 5 | 10 | 10 | -19558 |

A narrow profitable neighborhood is a parameter-fit warning. A broader plateau would be stronger evidence.

## Fixed Row Rolling Windows

This check holds the current fixed row constant and rolls dates using `4` train dates, `2` holdout dates, and a `2` date step.

| Window | Train Dates | Train Net USD | Holdout Dates | Holdout Net USD |
| ---: | --- | ---: | --- | ---: |
| 1 | 2026-03-23 to 2026-04-02 | -206 | 2026-04-07 to 2026-04-23 | -771 |
| 3 | 2026-03-27 to 2026-04-23 | 415 | 2026-04-24 to 2026-05-01 | -4535 |
| 5 | 2026-04-07 to 2026-05-01 | -5306 | 2026-05-04 to 2026-05-05 | -1364 |
| 7 | 2026-04-24 to 2026-05-05 | -5899 | 2026-05-13 to 2026-05-14 | 4151 |
| 9 | 2026-05-04 to 2026-05-14 | 2787 | 2026-05-15 to 2026-05-18 | -3635 |
| 11 | 2026-05-13 to 2026-05-18 | 516 | 2026-05-20 to 2026-05-21 | -738 |
| 13 | 2026-05-15 to 2026-05-21 | -4373 | 2026-05-22 to 2026-05-26 | 879 |
| 15 | 2026-05-20 to 2026-05-26 | 141 | 2026-05-27 to 2026-05-28 | -4228 |
| 17 | 2026-05-22 to 2026-05-28 | -3349 | 2026-05-29 to 2026-06-01 | -2756 |
| 19 | 2026-05-27 to 2026-06-01 | -6984 | 2026-06-02 to 2026-06-03 | -5749 |
| 21 | 2026-05-29 to 2026-06-03 | -8505 | 2026-06-04 to 2026-06-05 | 3816 |
| 23 | 2026-06-02 to 2026-06-05 | -1933 | 2026-06-08 to 2026-06-09 | -3684 |
| 25 | 2026-06-04 to 2026-06-09 | 132 | 2026-06-10 to 2026-06-11 | -384 |
| 27 | 2026-06-08 to 2026-06-11 | -4068 | 2026-06-12 to 2026-06-15 | -384 |
| 29 | 2026-06-10 to 2026-06-15 | -768 | 2026-06-16 to 2026-06-17 | -384 |
| 31 | 2026-06-12 to 2026-06-17 | -768 | 2026-06-18 to 2026-06-19 | -784 |
| 33 | 2026-06-16 to 2026-06-19 | -1168 | 2026-06-22 to 2026-06-23 | 366 |
| 35 | 2026-06-18 to 2026-06-23 | -418 | 2026-06-24 to 2026-06-25 | 2016 |
| 37 | 2026-06-22 to 2026-06-25 | 2382 | 2026-06-26 to 2026-06-29 | 2016 |

Fixed-row rolling holdout total: `161` trades, `-16152` net USD.

Excluding holiday dates:

| Window | Train Dates | Train Net USD | Holdout Dates | Holdout Net USD |
| ---: | --- | ---: | --- | ---: |
| 1 | 2026-03-23 to 2026-04-02 | -206 | 2026-04-07 to 2026-04-23 | -771 |
| 3 | 2026-03-27 to 2026-04-23 | 415 | 2026-04-24 to 2026-05-01 | -4535 |
| 5 | 2026-04-07 to 2026-05-01 | -5306 | 2026-05-04 to 2026-05-05 | -1364 |
| 7 | 2026-04-24 to 2026-05-05 | -5899 | 2026-05-13 to 2026-05-14 | 4151 |
| 9 | 2026-05-04 to 2026-05-14 | 2787 | 2026-05-15 to 2026-05-18 | -3635 |
| 11 | 2026-05-13 to 2026-05-18 | 516 | 2026-05-20 to 2026-05-21 | -738 |
| 13 | 2026-05-15 to 2026-05-21 | -4373 | 2026-05-22 to 2026-05-26 | 879 |
| 15 | 2026-05-20 to 2026-05-26 | 141 | 2026-05-27 to 2026-05-28 | -4228 |
| 17 | 2026-05-22 to 2026-05-28 | -3349 | 2026-05-29 to 2026-06-01 | -2756 |
| 19 | 2026-05-27 to 2026-06-01 | -6984 | 2026-06-02 to 2026-06-03 | -5749 |
| 21 | 2026-05-29 to 2026-06-03 | -8505 | 2026-06-04 to 2026-06-05 | 3816 |
| 23 | 2026-06-02 to 2026-06-05 | -1933 | 2026-06-08 to 2026-06-09 | -3684 |
| 25 | 2026-06-04 to 2026-06-09 | 132 | 2026-06-10 to 2026-06-11 | -384 |
| 27 | 2026-06-08 to 2026-06-11 | -4068 | 2026-06-12 to 2026-06-15 | -384 |
| 29 | 2026-06-10 to 2026-06-15 | -768 | 2026-06-16 to 2026-06-17 | -384 |
| 31 | 2026-06-12 to 2026-06-17 | -768 | 2026-06-18 to 2026-06-22 | 366 |
| 33 | 2026-06-16 to 2026-06-22 | -18 | 2026-06-23 to 2026-06-24 | 2016 |
| 35 | 2026-06-18 to 2026-06-24 | 2382 | 2026-06-25 to 2026-06-26 | 3666 |

Holiday-excluded fixed-row rolling holdout total: `149` trades, `-13718` net USD.

This separates fixed-row behavior from train-window optimizer selection, but it still does not prove stability.

## Risk Gate Checks

| Gate | Trades | Net USD |
| --- | ---: | ---: |
| No gate | 169 | -16358 |
| First 3 signals/day | 107 | -12199 |
| Before 11:00 | 67 | -5919 |
| Stop after daily profit 500 | 89 | -8123 |
| Stop after daily profit 1000 | 139 | -13298 |
| Stop after daily loss 1000 | 116 | -9412 |

Profit gates are especially easy to overfit. Treat them as risk-control candidates, not as evidence of strategy quality.

## Conclusion

Reject `5 / 10 / 8 / initial` as a fixed row for the current sample. The sample is now large enough for the configured minimum trade count, and both the full result and robustness checks are negative.
