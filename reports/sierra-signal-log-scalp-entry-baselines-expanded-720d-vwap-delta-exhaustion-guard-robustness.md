# Scaled Context Guard Robustness

Status: **research lead, not live-ready**

## Source

- Context diagnostics: `reports/sierra-signal-log-scalp-entry-baselines-expanded-720d-vwap-delta-exhaustion-context-diagnostics.csv`

## Window Robustness

| Train | Holdout | Step | Windows | Unguarded Net | Guarded Net | Improvement | Kept Trades | Avg/Trade | Negative Windows | Worst Window |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 5 | 5 | 93 | -228594.5 | -31407 | 197187.5 | 3751 | -8.37296721 | 45 | -18411.5 |
| 40 | 5 | 5 | 89 | -236753 | -80546.5 | 156206.5 | 3712 | -21.69894935 | 44 | -18411.5 |
| 40 | 10 | 10 | 44 | -239588 | -69682.5 | 169905.5 | 3635 | -19.1698762 | 24 | -29364.5 |
| 60 | 10 | 10 | 42 | -194191.5 | -79039.5 | 115152 | 3386 | -23.34303012 | 23 | -29364.5 |
| 80 | 10 | 10 | 40 | -161060.5 | -102871.5 | 58189 | 3362 | -30.59830458 | 21 | -29364.5 |

## Interpretation

The compact guard family improved every tested window shape, but all tested
window shapes remained negative. This is useful failure attribution, not an
implementation candidate.

Selected guard counts are deliberately shown in the CSV rather than promoted to a final Sierra rule. The next step is to pick one fixed guard, rerun it on a fresh later export, and only then consider implementation.
