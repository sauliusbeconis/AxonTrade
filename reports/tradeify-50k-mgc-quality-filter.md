# Tradeify 50K MGC Quality-Filter Research

Status: development/validation test of a simple pre-entry logistic gate on the frozen MGC strategy. No NinjaTrader code is included.

## Method

- source bars: `813388`; frozen outcomes: `343`;
- frozen management profile: `breakeven:t25:s15:trig20`; minimum development win rate: `58.0%`;
- final-period process status: `previously_inspected`;
- chronological active-date split: `296 / 148 / 149`;
- coefficients fit only on the first 50%; regularization and probability threshold selected only on the next 25%; final 25% excluded from selection;
- model inputs are available at entry: direction, weekday, time, close location, delta, range/body, VWAP distance/slope, five-bar move/delta, session range, and relative volume;
- label: positive net trade after Tradeify fee and two total slippage ticks;
- purpose: reject weak entries, not predict price or alter the frozen stop/target.

## Decision

Development-selected model: `mfg_logit_l2_0.5` at probability `>= 0.45`.

| Sample | Trades | Net | PF | Win | DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 156 | 4324.28 | 1.63652636 | 59.6% | -657.84 |
| Validation | 51 | 2404.88 | 1.92869721 | 58.8% | -554.08 |
| Final holdout | 57 | 4013.16 | 2.35522957 | 52.6% | -466.48 |
| Full base | 264 | 10742.32 | 1.87022371 | 58.0% | -657.84 |
| Full, six-tick stress | 264 | 9686.32 | 1.75715545 | 55.7% | -685.84 |
| Final holdout, six-tick stress | 57 | 3785.16 | 2.23325644 | 52.6% | -482.48 |

Final-period threshold neighborhood:

| Threshold | Trades | Net | PF | Win | DD |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.4 | 63 | 4588.44 | 2.46895889 | 52.4% | -466.48 |
| 0.425 | 58 | 4009.04 | 2.35195727 | 51.7% | -466.48 |
| 0.45 | 57 | 4013.16 | 2.35522957 | 52.6% | -466.48 |
| 0.475 | 51 | 3587.88 | 2.35448944 | 52.9% | -466.48 |
| 0.5 | 49 | 3346.12 | 2.26518852 | 53.1% | -466.48 |

Frozen standardized logistic coefficients:

- intercept: `0.23095117`;
- `direction_long`: coefficient `0.16628948`, mean `0.58988764`, scale `0.49185385`;
- `weekday_monday`: coefficient `0.1490609`, mean `0.33707865`, scale `0.472712`;
- `weekday_tuesday`: coefficient `0.00410903`, mean `0.33707865`, scale `0.472712`;
- `time_minutes`: coefficient `-0.11491778`, mean `526.91011236`, scale `18.98588503`;
- `directional_close_location`: coefficient `0.23408575`, mean `0.82950953`, scale `0.13580856`;
- `abs_delta`: coefficient `0.21638418`, mean `58.08426966`, scale `31.17923322`;
- `bar_range`: coefficient `-0.13385021`, mean `1.96797753`, scale `1.42447994`;
- `aligned_body`: coefficient `-0.3175705`, mean `1.32977528`, scale `0.89408855`;
- `abs_vwap_distance`: coefficient `-0.0307367`, mean `7.72078652`, scale `7.39858516`;
- `day_range_so_far`: coefficient `0.28131842`, mean `8.92696629`, scale `6.42255093`;
- `aligned_prior_5_move`: coefficient `0.25060303`, mean `2.99775281`, scale `1.86167603`;
- `aligned_prior_5_delta`: coefficient `-0.3743765`, mean `118.51685393`, scale `107.09096337`;
- `aligned_vwap_slope_5`: coefficient `-0.06681485`, mean `0.09269663`, scale `0.13575642`;
- `volume_ratio_20`: coefficient `0.25345067`, mean `1.69972387`, scale `1.19482169`;

## Account Policies

| Policy | Dev Historical Pass/Fail/Lock | Dev MC Pass/Fail/Lock | Full Historical Pass/Fail/Lock | Median Days | Holdout MC Pass/Fail/Lock | Funded Lock Pass/Fail/Lock; Days |
| --- | --- | --- | --- | ---: | --- | --- |
| `adaptive_2_to_1_dd1000` | 100.0% / 0.0% / 0.0% | 87.5% / 0.0% / 8.2% | 100.0% / 0.0% / 0.0% | 117 | 93.6% / 0.0% / 6.3% | 100.0% / 0.0% / 0.0%; 84 |
| `adaptive_2_to_1_dd750` | 100.0% / 0.0% / 0.0% | 85.8% / 0.0% / 5.3% | 100.0% / 0.0% / 0.0% | 138 | 95.9% / 0.0% / 3.9% | 100.0% / 0.0% / 0.0%; 88 |
| `adaptive_3_2_1_dd250_750` | 100.0% / 0.0% / 0.0% | 83.4% / 0.0% / 6.4% | 100.0% / 0.0% / 0.0% | 132 | 95.7% / 0.0% / 4.1% | 100.0% / 0.0% / 0.0%; 89 |
| `adaptive_2_to_1_dd500` | 100.0% / 0.0% / 0.0% | 83.0% / 0.0% / 3.1% | 100.0% / 0.0% / 0.0% | 139 | 97.0% / 0.0% / 2.5% | 100.0% / 0.0% / 0.0%; 92 |
| `adaptive_2_to_1_dd250` | 100.0% / 0.0% / 0.0% | 78.1% / 0.0% / 1.7% | 100.0% / 0.0% / 0.0% | 197 | 98.0% / 0.0% / 1.4% | 100.0% / 0.0% / 0.0%; 134 |
| `fixed_1_mgc` | 100.0% / 0.0% / 0.0% | 70.9% / 0.0% / 0.8% | 100.0% / 0.0% / 0.0% | 234 | 97.5% / 0.0% / 0.9% | 100.0% / 0.0% / 0.0%; 170 |
| `adaptive_3_2_1_dd250_1000` | 100.0% / 0.0% / 0.0% | 84.7% / 0.0% / 10.5% | 100.0% / 0.0% / 0.0% | 110 | 93.5% / 0.0% / 6.4% | 100.0% / 0.0% / 0.0%; 72 |
| `fixed_2_mgc` | 100.0% / 0.0% / 0.0% | 84.5% / 0.0% / 14.9% | 100.0% / 0.0% / 0.0% | 113 | 88.2% / 0.0% / 11.8% | 100.0% / 0.0% / 0.0%; 83 |
| `adaptive_3_2_1_dd500_1000` | 100.0% / 0.0% / 0.0% | 82.2% / 0.0% / 13.2% | 100.0% / 0.0% / 0.0% | 94 | 90.6% / 0.0% / 9.3% | 100.0% / 0.0% / 0.0%; 70 |
| `fixed_3_mgc` | 89.2% / 0.0% / 10.8% | 68.3% / 0.0% / 31.7% | 94.0% / 0.0% / 6.0% | 78 | 76.5% / 0.0% / 23.5% | 94.0% / 0.0% / 6.0%; 56 |

Verdict: `REJECT_AFTER_HOLDOUT`.

The filter does not replace the fixed 1 MGC safety baseline. A good development fit is insufficient without stable holdout and account-path behavior.
