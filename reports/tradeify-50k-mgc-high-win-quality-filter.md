# Tradeify 50K MGC Quality-Filter Research

Status: development/validation test of a simple pre-entry logistic gate on the frozen MGC strategy. No NinjaTrader code is included.

## Method

- source bars: `813388`; frozen outcomes: `343`;
- frozen management profile: `fixed:t8:s15:trig0`; minimum development win rate: `65.0%`;
- final-period process status: `previously_inspected`;
- chronological active-date split: `296 / 148 / 149`;
- coefficients fit only on the first 50%; regularization and probability threshold selected only on the next 25%; final 25% excluded from selection;
- model inputs are available at entry: direction, weekday, time, close location, delta, range/body, VWAP distance/slope, five-bar move/delta, session range, and relative volume;
- label: positive net trade after Tradeify fee and two total slippage ticks;
- purpose: reject weak entries, not predict price or alter the frozen stop/target.

## Decision

Development-selected model: `mfg_logit_l2_0.25` at probability `>= 0.7`.

| Sample | Trades | Net | PF | Win | DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 86 | 2299.68 | 1.93051712 | 76.7% | -401.72 |
| Validation | 44 | 777.72 | 1.4712198 | 72.7% | -308.24 |
| Final holdout | 68 | 1709.84 | 1.73961415 | 77.9% | -542.96 |
| Full base | 198 | 4787.24 | 1.7440951 | 76.3% | -542.96 |
| Full, six-tick stress | 198 | 3995.24 | 1.60325906 | 75.8% | -574.96 |
| Final holdout, six-tick stress | 68 | 1437.84 | 1.60622312 | 77.9% | -574.96 |

Final-period threshold neighborhood:

| Threshold | Trades | Net | PF | Win | DD |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.65 | 77 | 2162.76 | 1.87706008 | 79.2% | -697.08 |
| 0.675 | 71 | 1707.48 | 1.69243122 | 77.5% | -697.08 |
| 0.7 | 68 | 1709.84 | 1.73961415 | 77.9% | -542.96 |
| 0.725 | 63 | 1560.44 | 1.7232027 | 77.8% | -542.96 |
| 0.75 | 56 | 1489.28 | 1.80525997 | 78.6% | -391.2 |

Frozen standardized logistic coefficients:

- intercept: `0.81363911`;
- `direction_long`: coefficient `0.0583787`, mean `0.58988764`, scale `0.49185385`;
- `weekday_monday`: coefficient `0.1263485`, mean `0.33707865`, scale `0.472712`;
- `weekday_tuesday`: coefficient `-0.14564598`, mean `0.33707865`, scale `0.472712`;
- `time_minutes`: coefficient `-0.25028284`, mean `526.91011236`, scale `18.98588503`;
- `directional_close_location`: coefficient `0.30729904`, mean `0.82950953`, scale `0.13580856`;
- `abs_delta`: coefficient `0.28633956`, mean `58.08426966`, scale `31.17923322`;
- `bar_range`: coefficient `0.66241121`, mean `1.96797753`, scale `1.42447994`;
- `aligned_body`: coefficient `-0.81888235`, mean `1.32977528`, scale `0.89408855`;
- `abs_vwap_distance`: coefficient `0.37597185`, mean `7.72078652`, scale `7.39858516`;
- `day_range_so_far`: coefficient `0.33366238`, mean `8.92696629`, scale `6.42255093`;
- `aligned_prior_5_move`: coefficient `0.17288455`, mean `2.99775281`, scale `1.86167603`;
- `aligned_prior_5_delta`: coefficient `-0.3941398`, mean `118.51685393`, scale `107.09096337`;
- `aligned_vwap_slope_5`: coefficient `-0.42505455`, mean `0.09269663`, scale `0.13575642`;
- `volume_ratio_20`: coefficient `0.04497441`, mean `1.69972387`, scale `1.19482169`;

## Account Policies

| Policy | Dev Historical Pass/Fail/Lock | Dev MC Pass/Fail/Lock | Full Historical Pass/Fail/Lock | Median Days | Holdout MC Pass/Fail/Lock | Funded Lock Pass/Fail/Lock; Days |
| --- | --- | --- | --- | ---: | --- | --- |
| `adaptive_3_2_1_dd500_1000` | 98.9% / 0.0% / 0.0% | 66.9% / 0.0% / 4.2% | 99.4% / 0.0% / 0.0% | 215 | 80.5% / 0.0% / 8.2% | 100.0% / 0.0% / 0.0%; 126 |
| `adaptive_3_2_1_dd250_1000` | 100.0% / 0.0% / 0.0% | 65.0% / 0.0% / 3.2% | 100.0% / 0.0% / 0.0% | 233 | 81.6% / 0.0% / 6.2% | 100.0% / 0.0% / 0.0%; 142 |
| `adaptive_3_2_1_dd250_750` | 95.2% / 0.0% / 0.0% | 60.5% / 0.0% / 1.7% | 97.3% / 0.0% / 0.0% | 240 | 77.0% / 0.0% / 3.8% | 100.0% / 0.0% / 0.0%; 156 |
| `fixed_2_mgc` | 100.0% / 0.0% / 0.0% | 60.3% / 0.0% / 7.2% | 100.0% / 0.0% / 0.0% | 258 | 83.5% / 0.0% / 10.8% | 100.0% / 0.0% / 0.0%; 190 |
| `adaptive_2_to_1_dd1000` | 100.0% / 0.0% / 0.0% | 57.7% / 0.0% / 1.9% | 100.0% / 0.0% / 0.0% | 258 | 81.4% / 0.0% / 4.9% | 100.0% / 0.0% / 0.0%; 190 |
| `adaptive_2_to_1_dd750` | 100.0% / 0.0% / 0.0% | 53.6% / 0.0% / 1.0% | 100.0% / 0.0% / 0.0% | 259 | 77.7% / 0.0% / 2.8% | 100.0% / 0.0% / 0.0%; 190 |
| `fixed_3_mgc` | 100.0% / 0.0% / 0.0% | 72.8% / 0.0% / 23.2% | 100.0% / 0.0% / 0.0% | 174 | 72.9% / 0.0% / 27.0% | 100.0% / 0.0% / 0.0%; 120 |
| `adaptive_2_to_1_dd500` | 74.2% / 0.0% / 0.0% | 47.0% / 0.0% / 0.6% | 85.4% / 0.0% / 0.0% | 285 | 72.1% / 0.0% / 1.4% | 100.0% / 0.0% / 0.0%; 202 |
| `adaptive_2_to_1_dd250` | 32.3% / 0.0% / 0.0% | 35.1% / 0.0% / 0.2% | 54.6% / 0.0% / 0.0% | 295 | 62.3% / 0.0% / 0.9% | 100.0% / 0.0% / 0.0%; 239 |
| `fixed_1_mgc` | 0.0% / 0.0% / 0.0% | 3.4% / 0.0% / 0.1% | 0.0% / 0.0% / 0.0% | 0 | 35.2% / 0.0% / 0.3% | 44.8% / 0.0% / 0.0%; 329.5 |

Verdict: `PROVISIONAL_GATES_PASS_REQUIRES_INDEPENDENT_REPLAY`.

The numerical gates pass, but the final period is no longer independent because an earlier model iteration exposed its behavior. Keep this as the frozen NinjaTrader research lead and require independent Playback/replay evidence before implementation approval.
