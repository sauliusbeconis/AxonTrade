# Liquidity Sweep Reward/Risk Sweep

This workflow tests whether the absorption strategy improves when trades with
low target distance relative to stop distance are filtered out.

Manual help needed: **No** after the absorption outcome CSV exists.

## Rationale

The 22-date absorption sample was negative after costs. A failure-mode pass
showed that many losing or low-quality trades had small available target
distance compared with stop distance.

This workflow does not change the strategy rule directly. It runs a
chronological train/holdout experiment over predeclared minimum reward/risk
thresholds.

## Run

```bash
.venv/bin/python scripts/run_absorption_reward_risk_sweep.py \
  data/processed/AxonTrade_ES_absorption_outcomes.csv \
  reports/liquidity-sweep-absorption-reward-risk-sweep-sample.csv \
  --train-date-count 12
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

## Current Sample Result

Input outcomes:

- source: `data/processed/AxonTrade_ES_absorption_outcomes.csv`
- active trade dates: `19`
- evaluated trades: `30`

Chronological split:

- train dates: first `12` active trade dates, `2026-05-22` through `2026-06-10`
- holdout dates: last `7` active trade dates, `2026-06-11` through `2026-06-19`
- output: `reports/liquidity-sweep-absorption-reward-risk-sweep-sample.csv`

Train selection:

- selected rule: `direction=all`, `minimum_reward_risk=2`
- train trades after filter: `2`
- train win rate: `100.00%`
- train net: `580.50` USD

Matching holdout row:

- holdout trades after filter: `5`
- target hits: `3`
- stop/ambiguous losses: `2`
- holdout win rate: `60.00%`
- holdout net: `513.75` USD
- average holdout net: `102.75` USD/trade

Interpretation: the reward/risk filter is promising enough to keep testing, but
the selected rule is not validated yet. The holdout sample has only `5` trades,
and the train-selected rule was chosen from a small grid after observing the
first sample.

## Interpretation Rules

- The selected train row is the highest train `net_usd`.
- The matching holdout row is the only row that matters for validation.
- A positive in-sample threshold does not validate the filter.
- Low trade count must be treated as weak evidence.
