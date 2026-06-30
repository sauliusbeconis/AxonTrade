# Scaled Context Guard Robustness

Status: **research lead, not live-ready**

## Source

- Context diagnostics: `reports/sierra-signal-log-scalp-entry-baselines-continuous-240d-vwap-delta-exhaustion-context-diagnostics.csv`

## Window Robustness

| Train | Holdout | Step | Windows | Unguarded Net | Guarded Net | Improvement | Kept Trades | Avg/Trade | Negative Windows | Worst Window |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 5 | 5 | 25 | 33510.5 | 71390 | 37879.5 | 630 | 113.31746032 | 6 | -6018 |
| 40 | 5 | 5 | 21 | 26979.5 | 56581 | 29601.5 | 517 | 109.4410058 | 6 | -6018 |
| 40 | 10 | 10 | 10 | 18445.5 | 50738 | 32292.5 | 516 | 98.32945736 | 3 | -2835 |
| 60 | 10 | 10 | 8 | 14367 | 40113.5 | 25746.5 | 432 | 92.85532407 | 2 | -2835 |
| 80 | 10 | 10 | 6 | -4889.5 | 13721 | 18610.5 | 322 | 42.61180124 | 2 | -4539.5 |

## Interpretation

The compact guard family improved every tested window shape. The best guarded net was `71390` on `20x5` windows, while the weakest tested shape still stayed positive at `13721`.

Selected guard counts are deliberately shown in the CSV rather than promoted to a final Sierra rule. The next step is to pick one fixed guard, rerun it on a fresh later export, and only then consider implementation.
