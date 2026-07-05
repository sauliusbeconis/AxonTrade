# MNQ Eval-Pass Wave Rider Trailing Walk-Forward

Status: chronological validation for the faster MNQ B setup under trailing drawdown rules.

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique dates: `507`
- base signals: `505`
- candidate rows: `6336`
- minimum training trades: `16`
- trailing floor: `min(0, high_water - 1000)`
- pass target: `$1250` with `50%` consistency

## Adaptive Walk-Forward Summary

Each window selects the best candidate on the training dates, then scores that exact candidate on the following unseen holdout dates.

| Config | Windows | Holdout Trades | Holdout Net | Avg | PF | Max DD | Positive | Negative | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail | Median Pass Trades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 120x40 | 9 | 92 | 7256 | 78.86956522 | 1.36977017 | -2893 | 6 | 3 | 29.4% | 21.7% | 47.8% | 45.7% | 5 |
| 180x40 | 8 | 60 | 7062 | 117.7 | 1.67052791 | -1417.5 | 5 | 3 | 25.0% | 3.8% | 68.3% | 15.0% | 6 |
| 240x60 | 4 | 42 | 5619 | 133.78571429 | 1.82620203 | -2008 | 4 | 0 | 35.0% | 11.7% | 66.7% | 28.6% | 4.5 |

## Frozen Candidate Benchmarks

These rows freeze one candidate upfront and evaluate the same chronological holdout slices. This is the cleaner comparison when deciding whether to build a bot.

| Config | Candidate | Windows | Holdout Trades | Holdout Net | Avg | PF | Max DD | Positive | Negative | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail | Median Pass Trades |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 120x40 | `b_best_4mnq_650_450` | 9 | 61 | 11662 | 191.18032787 | 2.05176768 | -1800 | 8 | 1 | 37.2% | 4.4% | 75.4% | 21.3% | 4 |
| 180x40 | `b_best_4mnq_650_450` | 8 | 50 | 10700 | 214 | 2.21590909 | -1350 | 5 | 3 | 39.7% | 5.0% | 78.0% | 16.0% | 4 |
| 240x60 | `b_best_4mnq_650_450` | 4 | 43 | 10550 | 245.34883721 | 2.50714286 | -1350 | 4 | 0 | 48.3% | 6.7% | 79.1% | 16.3% | 3 |
| 120x40 | `b_shorter_4mnq_650_450` | 9 | 61 | 11662 | 191.18032787 | 2.05176768 | -1800 | 8 | 1 | 37.2% | 4.4% | 75.4% | 21.3% | 4 |
| 180x40 | `b_shorter_4mnq_650_450` | 8 | 50 | 10700 | 214 | 2.21590909 | -1350 | 5 | 3 | 39.7% | 5.0% | 78.0% | 16.0% | 4 |
| 240x60 | `b_shorter_4mnq_650_450` | 4 | 43 | 10550 | 245.34883721 | 2.50714286 | -1350 | 4 | 0 | 48.3% | 6.7% | 79.1% | 16.3% | 3 |
| 120x40 | `b_lower_target_4mnq_600_450` | 9 | 61 | 9912 | 162.49180328 | 1.89393939 | -1800 | 8 | 1 | 30.3% | 4.4% | 68.9% | 24.6% | 4 |
| 180x40 | `b_lower_target_4mnq_600_450` | 8 | 50 | 9200 | 184 | 2.04545455 | -1350 | 5 | 3 | 29.7% | 5.0% | 72.0% | 20.0% | 4 |
| 240x60 | `b_lower_target_4mnq_600_450` | 4 | 43 | 9200 | 213.95348837 | 2.31428571 | -1350 | 4 | 0 | 37.9% | 6.7% | 72.1% | 20.9% | 4 |
| 120x40 | `b_smaller_3mnq_651_450` | 9 | 61 | 7464 | 122.36065574 | 1.61959905 | -2295 | 7 | 2 | 31.1% | 9.2% | 72.1% | 24.6% | 4.5 |
| 180x40 | `b_smaller_3mnq_651_450` | 8 | 50 | 5386.5 | 107.73 | 1.52715796 | -2295 | 5 | 3 | 32.2% | 10.3% | 70.0% | 26.0% | 4 |
| 240x60 | `b_smaller_3mnq_651_450` | 4 | 43 | 5233.5 | 121.70930233 | 1.62170349 | -2295 | 4 | 0 | 38.3% | 13.8% | 67.4% | 27.9% | 4 |

## All-Candidate Frozen Leaderboard

This ranks every frozen row from the faster B candidate pool across the same holdout slices. It is a robustness screen, not a license to keep optimizing on holdout data.

| Rank | Qty | Target | Stop | Trades | Total Net | Min Config Net | Min Cal Pass | Max Cal Fail | Min Sig Pass | Max Sig Fail | Positive Windows | Max DD | Strategy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 4 | 650 | 450 | 154 | 32912 | 10550 | 37.2% | 6.7% | 75.4% | 21.3% | 17/21 | -1800 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 2 | 4 | 650 | 450 | 154 | 32912 | 10550 | 37.2% | 6.7% | 75.4% | 21.3% | 17/21 | -1800 | `cadence_trailing:tue_wed:short:1000_1130:none` |
| 3 | 4 | 500 | 700 | 154 | 31316 | 9950 | 35.0% | 5.0% | 72.1% | 23.0% | 16/21 | -1638 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 4 | 4 | 500 | 700 | 154 | 31316 | 9950 | 35.0% | 5.0% | 72.1% | 23.0% | 16/21 | -1638 | `cadence_trailing:tue_wed:short:1000_1130:none` |
| 5 | 4 | 500 | 450 | 154 | 32412 | 10300 | 30.8% | 0.0% | 73.8% | 9.3% | 18/21 | -1250 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 6 | 4 | 500 | 450 | 154 | 32412 | 10300 | 30.8% | 0.0% | 73.8% | 9.3% | 18/21 | -1250 | `cadence_trailing:tue_wed:short:1000_1130:none` |
| 7 | 3 | 600 | 450 | 154 | 24474 | 7567.5 | 30.6% | 6.7% | 76.0% | 18.0% | 16/21 | -2346 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 8 | 3 | 600 | 450 | 154 | 24474 | 7567.5 | 30.6% | 6.7% | 76.0% | 18.0% | 16/21 | -2346 | `cadence_trailing:tue_wed:short:1000_1130:none` |
| 9 | 4 | 426 | 700 | 154 | 24544 | 7508 | 30.0% | 0.6% | 72.0% | 19.7% | 16/21 | -1248 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 10 | 4 | 426 | 700 | 154 | 24544 | 7508 | 30.0% | 0.6% | 72.0% | 19.7% | 16/21 | -1248 | `cadence_trailing:tue_wed:short:1000_1130:none` |
| 11 | 6 | 651 | 648 | 314 | 41304 | 13023 | 56.9% | 34.4% | 60.2% | 39.0% | 18/21 | -4209 | `cadence_trailing:tue_wed:both:1000_1230:move_le125` |
| 12 | 5 | 650 | 800 | 319 | 39257.5 | 12452.5 | 54.7% | 37.2% | 59.1% | 39.7% | 15/21 | -6300 | `cadence_trailing:tue_wed:both:1000_1045:none` |
| 13 | 5 | 650 | 650 | 226 | 35222.5 | 10345 | 54.4% | 30.8% | 60.3% | 36.3% | 16/21 | -2892.5 | `cadence_trailing:no_thu_fri:short:1000_1230:none` |
| 14 | 5 | 650 | 750 | 226 | 42737.5 | 13350 | 53.4% | 28.3% | 61.5% | 34.1% | 17/21 | -3147.5 | `cadence_trailing:no_thu_fri:short:1000_1230:none` |
| 15 | 5 | 650 | 800 | 226 | 39587.5 | 12550 | 53.4% | 28.3% | 61.5% | 34.1% | 17/21 | -3397.5 | `cadence_trailing:no_thu_fri:short:1000_1230:none` |

## Selected Candidate Counts

| Config | Count | Qty | Target | Stop | Strategy |
| --- | ---: | ---: | ---: | ---: | --- |
| 120x40 | 2 | 4 | 650 | 450 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 120x40 | 1 | 4 | 350 | 650 | `cadence_trailing:tue_wed:both:1000_1045:none` |
| 120x40 | 1 | 3 | 325.5 | 399 | `cadence_trailing:tue_wed:both:1000_1045:none` |
| 120x40 | 1 | 3 | 651 | 499.5 | `cadence_trailing:no_thu_fri:short:1000_1230:none` |
| 120x40 | 1 | 3 | 651 | 649.5 | `cadence_trailing:no_thu_fri:short:1000_1230:move125_bar60` |
| 120x40 | 1 | 4 | 650 | 700 | `cadence_trailing:no_thu_fri:short:1000_1230:none` |
| 120x40 | 1 | 4 | 500 | 750 | `cadence_trailing:no_thu_fri:short:1000_1230:none` |
| 120x40 | 1 | 4 | 550 | 750 | `cadence_trailing:no_thu_fri:short:1000_1230:none` |
| 180x40 | 2 | 4 | 650 | 450 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 180x40 | 1 | 3 | 325.5 | 399 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 180x40 | 1 | 3 | 600 | 399 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 180x40 | 1 | 3 | 651 | 649.5 | `cadence_trailing:no_thu_fri:short:1000_1230:move125_bar60` |
| 180x40 | 1 | 4 | 500 | 450 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 180x40 | 1 | 3 | 400.5 | 549 | `cadence_trailing:no_thu_fri:short:1000_1230:none` |
| 180x40 | 1 | 4 | 550 | 750 | `cadence_trailing:no_thu_fri:short:1000_1230:none` |
| 240x60 | 1 | 3 | 651 | 450 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 240x60 | 1 | 3 | 550.5 | 399 | `cadence_trailing:tue_wed:short:1000_1230:none` |
| 240x60 | 1 | 4 | 426 | 450 | `cadence_trailing:no_thu_fri:short:1000_1230:move125_bar60` |
| 240x60 | 1 | 4 | 500 | 450 | `cadence_trailing:tue_wed:short:1000_1230:none` |

## Interpretation

The adaptive selector is a bias check, not a live plan. In this run it stayed profitable overall, but it changed candidates frequently and trailed the locked `4 MNQ` `$650/$450` benchmark on holdout net, drawdown, trailing pass rate, and trailing fail rate.

The conclusion is to reject dynamic optimization for this setup and advance only the frozen Tuesday/Wednesday short-only `4 MNQ` `$650/$450` row to replay/mechanics validation.
