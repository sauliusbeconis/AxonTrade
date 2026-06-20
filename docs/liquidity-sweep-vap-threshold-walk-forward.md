# Liquidity Sweep VAP Threshold Walk-Forward Sweep

This workflow repeats swept-level volume-at-price threshold selection across
rolling chronological windows. It is research-only and does not place, modify,
cancel, or flatten orders.

Manual help needed: **No** after the VAP diagnostics CSV exists.

## Run

From the repository:

```bash
.venv/bin/python scripts/run_vap_absorption_threshold_walk_forward_sweep.py \
  reports/liquidity-sweep-vap-absorption-diagnostics-sample.csv \
  reports/liquidity-sweep-vap-threshold-walk-forward-sample.csv \
  --train-date-count 6 \
  --holdout-date-count 1 \
  --minimum-train-trades 1
```

Default tested grids:

- minimum swept-zone aggression ratios: `1,1.25,1.5,2,3`
- minimum swept-zone volumes: `0,5,10,20,50,100,150,200`
- direction filters: `all,long,short`

## Output Format

The output CSV writes only the selected row for each rolling window:

- `sample = train`
- `sample = holdout`

Each holdout row uses the exact threshold rule selected by highest training
`net_usd` in that rolling window. Zero-trade holdout rows are allowed. Zero-trade
train selections are blocked by `--minimum-train-trades`.

Key fields:

- `split_id`
- `sample`
- `trade_dates`
- `direction_filter`
- `minimum_zone_aggression_ratio`
- `minimum_zone_volume`
- `evaluated_trades`
- `net_usd`

## Current Sample Result

Input diagnostics:

- source: `reports/liquidity-sweep-vap-absorption-diagnostics-sample.csv`
- active trade dates: `19`
- evaluated trades before filtering: `30`
- output: `reports/liquidity-sweep-vap-threshold-walk-forward-sample.csv`

Walk-forward setup:

- train dates per window: `6`
- holdout dates per window: `1`
- minimum selected train trades: `1`
- walk-forward windows: `13`

Selected holdout result:

- holdout windows with selected trades: `6`
- selected holdout trades: `6`
- target hits: `3`
- stop/ambiguous losses: `3`
- net result after default costs: `-233.50` USD

Selected holdout rows:

| Holdout date | Direction | Min zone ratio | Min zone volume | Trades | Net USD |
| --- | --- | ---: | ---: | ---: | ---: |
| `2026-06-03` | `long` | `1` | `0` | `1` | `71.50` |
| `2026-06-04` | `long` | `1` | `10` | `0` | `0.00` |
| `2026-06-05` | `long` | `1` | `10` | `1` | `21.50` |
| `2026-06-08` | `long` | `1` | `10` | `0` | `0.00` |
| `2026-06-09` | `long` | `1` | `10` | `0` | `0.00` |
| `2026-06-10` | `long` | `1` | `10` | `0` | `0.00` |
| `2026-06-11` | `all` | `1` | `5` | `1` | `-153.50` |
| `2026-06-12` | `short` | `1` | `5` | `0` | `0.00` |
| `2026-06-15` | `all` | `1` | `5` | `1` | `-141.00` |
| `2026-06-16` | `all` | `2` | `5` | `1` | `-141.00` |
| `2026-06-17` | `all` | `2` | `5` | `0` | `0.00` |
| `2026-06-18` | `all` | `2` | `0` | `0` | `0.00` |
| `2026-06-19` | `short` | `1` | `150` | `1` | `109.00` |

Interpretation: the current VAP threshold filter is not validated by rolling
walk-forward testing. The filter finds some useful holdout trades, but the
selected rolling rule remains negative on the available sample and the trade
count is too small for execution decisions.

## Interpretation Rules

- Sum only the `holdout` rows to evaluate the walk-forward result.
- Do not choose the best holdout row after the fact; that is holdout leakage.
- A few positive holdout dates do not validate the setup if rolling selected
  holdout net remains negative.
- This workflow validates the filter idea, not execution readiness.
