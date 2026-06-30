# Scaled Context Guard Robustness

Status: **research lead, not live-ready**

## Source

- Context diagnostics: `reports/sierra-signal-log-scalp-entry-baselines-fresh-480d-vwap-delta-exhaustion-context-diagnostics.csv`

## Window Robustness

| Train | Holdout | Step | Windows | Unguarded Net | Guarded Net | Improvement | Kept Trades | Avg/Trade | Negative Windows | Worst Window |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 5 | 5 | 32 | 16793 | 69375 | 52582 | 850 | 81.61764706 | 8 | -7446 |
| 40 | 5 | 5 | 28 | 17919 | 46996 | 29077 | 672 | 69.93452381 | 10 | -6504 |
| 40 | 10 | 10 | 14 | 17919 | 50272 | 32353 | 679 | 74.03829161 | 4 | -7158 |
| 60 | 10 | 10 | 12 | 25522.5 | 44320.5 | 18798 | 631 | 70.2385103 | 4 | -7158 |
| 80 | 10 | 10 | 10 | 25059.5 | 57862 | 32802.5 | 534 | 108.35580524 | 2 | -3495.5 |

## Interpretation

The compact guard family improved every tested window shape. The best guarded net was `69375` on `20x5` windows, while the weakest tested shape still stayed positive at `44320.5`.

Selected guard counts are deliberately shown in the CSV rather than promoted to a final Sierra rule. The next step is to pick one fixed guard, rerun it on a fresh later export, and only then consider implementation.
