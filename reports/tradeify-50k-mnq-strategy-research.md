# Tradeify 50K MNQ Strategy Research

Status: fresh strategy discovery for Tradeify Select and a future NinjaTrader implementation. No NinjaTrader code is included.

## Research Contract

- account: Tradeify Select 50K evaluation;
- objective: `$3000` net profit with `$2000` EOD trailing drawdown and `40%` consistency;
- execution limit used for sizing: at most `20 MNQ`, matching funded day-one size rather than the looser `40 MNQ` evaluation limit;
- frequency: at most one completed trade per session;
- base costs: Tradeify `$1.82` MNQ round trip plus `2` total slippage ticks per contract;
- stress costs: Tradeify `$1.82` MNQ round trip plus `6` total slippage ticks per contract;
- ambiguous target/stop bar: stop first;
- all positions flattened by `15:45 America/New_York`;
- final holdout is not used by the selection ranking.

## Data And Split

- source rows: `67300`;
- dates: `2024-07-15` through `2026-07-02`;
- unique dates: `507`;
- training: `2024-07-15` through `2025-07-08` (`253` dates);
- validation: `2025-07-09` through `2026-01-05` (`127` dates);
- untouched final holdout: `2026-01-06` through `2026-07-02` (`127` dates).

## Fresh Families

The pass tests opening-drive pullbacks, prior-session liquidity sweeps, gap-fade acceptance, and VWAP trend pullbacks. These are separate from the frozen legacy MNQ bot rules.

Generated signal sets: `960`.
Evaluated strategy/exit rows: `15312`.

| Family | Trades | /Wk | Dev Net | Dev PF | Dev DD | Holdout Net | Holdout PF | Holdout DD | Exit | Eligible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `tradeify_gap_fade_acceptance` | 114 | 1.11297071 | 1599.02 | 1.96535861 | -319.74 | -120.5 | 0.85450374 | -473.84 | `25/40` | yes |
| `tradeify_open_drive_pullback` | 113 | 1.10320781 | 2672.16 | 1.71699267 | -414.1 | 246.68 | 1.18615673 | -662.56 | `80/40` | yes |
| `tradeify_prior_day_sweep_reversal` | 113 | 1.10320781 | 1471.58 | 1.58563356 | -531.02 | -90.24 | 0.92817574 | -496.66 | `50/30` | yes |
| `tradeify_vwap_trend_pullback` | 278 | 2.71408647 | 2081.6 | 1.26626417 | -1028.9 | -794.06 | 0.82041018 | -1228.94 | `40/60` | no |

## Frozen Selection

Frozen rule: `tradeify_gap_fade_acceptance:gap20:or15:rev20:delta0:cl0.65:end1130` with `25/40` target/stop points.

The ranking used training and validation only. Holdout metrics below are the first-read result for the selected row.

| Period | Trades | Net 1 MNQ | PF | Win | DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Training | 65 | 1116.7 | 1.89889721 | 76.9% | -319.74 |
| Validation | 24 | 482.32 | 2.16474282 | 79.2% | -284.1 |
| Final holdout | 25 | -120.5 | 0.85450374 | 60.0% | -473.84 |
| Full sample | 114 | 1478.52 | 1.59507365 | 73.7% | -473.84 |

Average hold: `8.28947368` minutes; median hold: `6` minutes.

## Tradeify Sizing

Sizing is restricted to the funded day-one maximum and rejects a nominal stop above `$450`, a nominal target above `$1100`, full-sample DD below `-$1500`, or stress Monte Carlo eval-fail rate above `20%`.

| MNQ | Stop | Target | Net | DD | Hist Pass | Hist Fail | Median Days | MC Pass | MC Fail | Funded Lock | Risk |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | -82.82 | 47.18 | 1478.52 | -473.84 | 0.0% | 0.0% | 0 | 0.0% | 0.0% | 0.0% | reject |
| 2 | -165.64 | 94.36 | 2957.04 | -947.68 | 0.0% | 0.0% | 0 | 0.0% | 0.0% | 0.0% | reject |
| 3 | -248.46 | 141.54 | 4435.56 | -1421.52 | 0.0% | 0.0% | 0 | 0.0% | 0.1% | 0.0% | reject |
| 4 | -331.28 | 188.72 | 5914.08 | -1895.36 | 0.0% | 0.0% | 0 | 0.4% | 1.9% | 4.3% | reject |
| 5 | -414.1 | 235.9 | 7392.6 | -2369.2 | 0.0% | 10.7% | 0 | 2.2% | 5.3% | 24.3% | reject |
| 6 | -496.92 | 283.08 | 8871.12 | -2843.04 | 5.9% | 19.1% | 78 | 9.0% | 11.4% | 41.2% | reject |
| 7 | -579.74 | 330.26 | 10349.64 | -3316.88 | 23.7% | 27.0% | 78 | 14.7% | 16.5% | 52.7% | reject |
| 8 | -662.56 | 377.44 | 11828.16 | -3790.72 | 34.5% | 32.1% | 69 | 21.7% | 24.1% | 58.0% | reject |
| 9 | -745.38 | 424.62 | 13306.68 | -4264.56 | 42.6% | 31.6% | 66.5 | 28.3% | 26.5% | 63.7% | reject |
| 10 | -828.2 | 471.8 | 14785.2 | -4738.4 | 52.7% | 30.4% | 60 | 36.4% | 33.2% | 64.5% | reject |
| 11 | -911.02 | 518.98 | 16263.72 | -5212.24 | 57.4% | 29.4% | 51 | 42.5% | 33.4% | 64.5% | reject |
| 12 | -993.84 | 566.16 | 17742.24 | -5686.08 | 59.8% | 29.0% | 51 | 40.8% | 46.0% | 68.2% | reject |
| 13 | -1076.66 | 613.34 | 19220.76 | -6159.92 | 59.4% | 35.3% | 42 | 46.7% | 45.2% | 62.3% | reject |
| 14 | -1159.48 | 660.52 | 20699.28 | -6633.76 | 59.4% | 35.3% | 42 | 48.8% | 43.8% | 63.3% | reject |
| 15 | -1242.3 | 707.7 | 22177.8 | -7107.6 | 60.0% | 34.7% | 38 | 49.7% | 43.4% | 65.9% | reject |
| 16 | -1325.12 | 754.88 | 23656.32 | -7581.44 | 61.9% | 32.7% | 30 | 52.6% | 42.5% | 65.9% | reject |
| 17 | -1407.94 | 802.06 | 25134.84 | -8055.28 | 61.5% | 36.9% | 30 | 54.2% | 44.2% | 65.5% | reject |
| 18 | -1490.76 | 849.24 | 26613.36 | -8529.12 | 61.5% | 36.9% | 30 | 53.6% | 44.8% | 65.5% | reject |
| 19 | -1573.58 | 896.42 | 28091.88 | -9002.96 | 61.5% | 36.9% | 30 | 54.3% | 44.4% | 65.5% | reject |
| 20 | -1656.4 | 943.6 | 29570.4 | -9476.8 | 62.5% | 35.9% | 28 | 54.4% | 44.6% | 66.5% | reject |

## Stress Decision

No quantity passed the account-risk sizing screen. The strategy is rejected.
