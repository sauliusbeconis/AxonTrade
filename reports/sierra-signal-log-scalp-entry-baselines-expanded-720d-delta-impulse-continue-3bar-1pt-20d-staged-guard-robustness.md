# Scaled Context Guard Robustness

Status: **research lead, not live-ready**

## Source

- Context diagnostics: `reports/sierra-signal-log-scalp-entry-baselines-expanded-720d-delta-impulse-continue-3bar-1pt-20d-staged-context-diagnostics.csv`

## Window Robustness

| Train | Holdout | Step | Windows | Unguarded Net | Guarded Net | Improvement | Kept Trades | Avg/Trade | Negative Windows | Worst Window |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 5 | 5 | 93 | 38118.5 | 47382.5 | 9264 | 3690 | 12.84078591 | 45 | -18617.5 |
| 40 | 5 | 5 | 89 | 35451 | 35451 | 0 | 3557 | 9.96654484 | 43 | -18617.5 |
| 40 | 10 | 10 | 44 | 33031 | 33031 | 0 | 3517 | 9.3918112 | 24 | -20560 |
| 60 | 10 | 10 | 42 | 10538.5 | 10538.5 | 0 | 3357 | 3.13926125 | 24 | -20560 |
| 80 | 10 | 10 | 40 | -18973.5 | -18973.5 | 0 | 3198 | -5.93292683 | 24 | -20560 |

## Interpretation

The compact guard family improved the shorter window shapes, but the widest
tested shape still failed at `-18973.5`.

Selected guard counts are deliberately shown in the CSV rather than promoted to a final Sierra rule. The next step is to pick one fixed guard, rerun it on a fresh later export, and only then consider implementation.
