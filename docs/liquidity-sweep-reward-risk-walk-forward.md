# Liquidity Sweep Reward/Risk Walk-Forward Sweep

This workflow repeats absorption reward/risk filter selection across rolling
chronological windows. It is research-only and does not place, modify, cancel,
or flatten orders.

Manual help needed: **No** after the absorption outcome CSV exists.

## Run

From the repository:

```bash
.venv/bin/python scripts/run_absorption_reward_risk_walk_forward_sweep.py \
  data/processed/AxonTrade_ES_absorption_outcomes.csv \
  reports/liquidity-sweep-absorption-reward-risk-walk-forward-sample.csv \
  --train-date-count 6 \
  --holdout-date-count 1 \
  --minimum-train-trades 1
```

Default tested thresholds:

- `0`
- `0.5`
- `0.75`
- `1`
- `1.25`
- `1.5`
- `2`

Default direction filters:

- `all`
- `long`
- `short`

## Output Format

The output CSV writes only the selected row for each rolling window:

- `sample = train`
- `sample = holdout`

Each holdout row uses the exact filter selected by highest training `net_usd`
in that rolling window.

Key fields:

- `split_id`
- `sample`
- `trade_dates`
- `direction_filter`
- `minimum_reward_risk`
- `evaluated_trades`
- `net_usd`

## Current Sample Result

Input outcomes:

- source: `data/processed/AxonTrade_ES_absorption_outcomes.csv`
- active trade dates: `19`
- evaluated trades before filtering: `30`
- output: `reports/liquidity-sweep-absorption-reward-risk-walk-forward-sample.csv`

Walk-forward setup:

- train dates per window: `6`
- holdout dates per window: `1`
- minimum selected train trades: `1`
- walk-forward windows: `13`

Selected holdout result:

- holdout windows with selected trades: `7`
- selected holdout trades: `10`
- target hits: `4`
- stop/ambiguous losses: `6`
- gross result: `256.25` USD
- net result after default costs: `-28.75` USD

Selected holdout rows:

| Holdout date | Direction | Min reward/risk | Trades | Net USD |
| --- | --- | ---: | ---: | ---: |
| `2026-06-03` | `long` | `0.5` | `0` | `0.00` |
| `2026-06-04` | `all` | `0.5` | `2` | `-444.50` |
| `2026-06-05` | `short` | `0.5` | `0` | `0.00` |
| `2026-06-08` | `short` | `0.5` | `1` | `-203.50` |
| `2026-06-09` | `long` | `0.5` | `1` | `-191.00` |
| `2026-06-10` | `long` | `0.75` | `1` | `296.50` |
| `2026-06-11` | `all` | `2` | `0` | `0.00` |
| `2026-06-12` | `all` | `2` | `1` | `309.00` |
| `2026-06-15` | `all` | `2` | `0` | `0.00` |
| `2026-06-16` | `all` | `2` | `0` | `0.00` |
| `2026-06-17` | `all` | `1.5` | `2` | `124.25` |
| `2026-06-18` | `all` | `1.5` | `2` | `80.50` |
| `2026-06-19` | `all` | `1.5` | `0` | `0.00` |

Interpretation: the reward/risk filter is not validated by walk-forward testing.
The single chronological split was positive, but rolling selection across the
available dates is slightly negative after costs and still has too few trades.

## Interpretation Rules

- Sum only the `holdout` rows to evaluate the walk-forward result.
- A positive aggregate does not validate the rule if most windows have no
  selected trades.
- Zero-trade holdout rows are acceptable, but zero-trade train selections are
  blocked by `--minimum-train-trades`.
- This workflow validates the filter idea, not execution readiness.
