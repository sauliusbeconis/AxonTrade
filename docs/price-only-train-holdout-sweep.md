# Price-Only Train/Holdout Sweep

This workflow checks parameter-selection risk by splitting one Sierra Chart
export chronologically by trade date. It is research-only and does not place,
modify, cancel, or flatten orders.

Manual help is not needed after the Sierra Chart export file exists.

## Run

From the repository:

```bash
.venv/bin/python scripts/run_price_only_train_holdout_sweep.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_BarStudyExport.txt \
  reports/price-only-train-holdout-sweep-sample.csv \
  --symbol ESU26-CME \
  --chart-number 1 \
  --session-phase rth \
  --train-date-count 5
```

The default grid matches the parameter sweep:

- target R multiples: `0.5,1,1.5,2,2.5,3`;
- stop buffers in points: `0,0.25,0.5,1`;
- minimum opening-range width: `1`;
- direction filters: `all,long,short`.

## Output Format

The output CSV contains two rows per parameter combination:

- `sample = train`
- `sample = holdout`

The row selected by highest training `net_usd` is marked with:

`selected_on_train = true`

Key fields:

- `split_id`
- `sample`
- `selected_on_train`
- `trade_dates`
- `direction_filter`
- `target_r_multiple`
- `stop_buffer_points`
- `evaluated_trades`
- `net_usd`

## Current Sample Result

The current ES sample uses:

- training dates: `2026-06-10` through `2026-06-16`
- holdout dates: `2026-06-17` through `2026-06-19`
- split rows: `144`

Best training row:

- direction filter: `long`
- target R multiple: `2.5`
- stop buffer: `1`
- training trades: `11`
- training net: `1167.75` USD

Same selected row on holdout:

- holdout trades: `0`
- holdout net: `0.00` USD

This means the positive long-only result is not yet confirmed out of sample.
The holdout period produced no long candidates for that selected rule, so more
exported dates are required before treating the long-only observation as
evidence.
