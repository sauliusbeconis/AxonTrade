# Liquidity Sweep VAP Trap Filter

This workflow tests a stricter swept-level VAP hypothesis after the basic VAP
threshold filter failed.

Manual help needed: **No** after the VAP diagnostics CSV exists.

## Hypothesis

The failed VAP threshold test showed that more sweep-side aggression is not
enough. A more concrete trap should look like absorption concentrated at the
exact swept extreme, without broad heavy volume through the whole swept zone.

Tested entry-known filters:

- minimum swept-zone aggression ratio
- maximum swept-zone bid+ask volume
- maximum swept-zone price levels
- minimum exact-extreme volume share
- direction filter

This remains research-only and does not place, modify, cancel, or flatten
orders.

## Run

Train/holdout:

```bash
.venv/bin/python scripts/run_vap_trap_filter_sweep.py \
  reports/sierra-signal-log-vap-absorption-diagnostics-large-sample.csv \
  reports/sierra-signal-log-vap-trap-filter-sweep-large-sample.csv \
  --train-date-count 8 \
  --minimum-zone-aggression-ratios 1,1.25,1.5,2,3 \
  --maximum-zone-volumes 3,5,10,20,50,100,250 \
  --maximum-zone-levels 1,2,3,5 \
  --minimum-extreme-volume-shares 0,0.25,0.5,0.75,1 \
  --direction-filters all,long,short \
  --minimum-train-trades 4
```

Rolling walk-forward:

```bash
.venv/bin/python scripts/run_vap_trap_filter_walk_forward_sweep.py \
  reports/sierra-signal-log-vap-absorption-diagnostics-large-sample.csv \
  reports/sierra-signal-log-vap-trap-filter-walk-forward-large-sample.csv \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-zone-aggression-ratios 1,1.25,1.5,2,3 \
  --maximum-zone-volumes 3,5,10,20,50,100,250 \
  --maximum-zone-levels 1,2,3,5 \
  --minimum-extreme-volume-shares 0,0.25,0.5,0.75,1 \
  --direction-filters all,long,short \
  --minimum-train-trades 4
```

## Current Large Sierra Signal Sample

Train-selected rule:

- direction filter: `all`
- minimum swept-zone aggression ratio: `1`
- maximum swept-zone volume: `20`
- maximum swept-zone levels: `5`
- minimum exact-extreme volume share: `0.25`
- train trades: `8`
- train target hits: `6`
- train losses: `2`
- train net: `1953.25` USD

Matching holdout row:

- holdout trades: `5`
- target hits: `0`
- losses: `5`
- holdout net: `-1130.00` USD

Rolling walk-forward selected holdout result:

- holdout windows: `6`
- selected holdout trades: `5`
- target hits: `0`
- losses: `5`
- net result after default costs: `-1205.00` USD

Selected holdout rows:

| Window | Holdout Dates | Max Zone Volume | Max Zone Levels | Min Extreme Share | Trades | Net USD |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `1` | `2026-06-04` to `2026-06-08` | `20` | `5` | `0.25` | `3` | `-798.00` |
| `2` | `2026-06-08` to `2026-06-10` | `3` | `2` | `0` | `0` | `0.00` |
| `3` | `2026-06-10` to `2026-06-11` | `10` | `3` | `0.5` | `1` | `-203.50` |
| `4` | `2026-06-11` to `2026-06-12` | `10` | `5` | `0.5` | `1` | `-203.50` |
| `5` | `2026-06-12` to `2026-06-17` | `10` | `5` | `0.5` | `0` | `0.00` |
| `6` | `2026-06-17` to `2026-06-19` | `10` | `5` | `0.5` | `0` | `0.00` |

Interpretation: this stricter trap filter reduced selected holdout exposure
compared with the basic VAP threshold walk-forward (`5` trades instead of `11`),
but every selected holdout trade still lost. Treat this as a rejected edge and a
possible risk-reduction clue, not as a bot entry rule.
