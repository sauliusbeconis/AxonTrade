# Price-Only Walk-Forward Sweep

This workflow repeats parameter selection across rolling chronological windows.
It is research-only and does not place, modify, cancel, or flatten orders.

Manual help is not needed after the Sierra Chart export file exists.

## Run

From the repository:

```bash
.venv/bin/python scripts/run_price_only_walk_forward_sweep.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_BarStudyExport.txt \
  reports/price-only-walk-forward-sweep-sample.csv \
  --symbol ESU26-CME \
  --chart-number 1 \
  --session-phase rth \
  --train-date-count 3 \
  --holdout-date-count 1
```

The default grid matches the parameter sweep:

- target R multiples: `0.5,1,1.5,2,2.5,3`;
- stop buffers in points: `0,0.25,0.5,1`;
- minimum opening-range width: `1`;
- direction filters: `all,long,short`.

## Output Format

The output CSV writes only the selected row for each rolling window:

- `sample = train`
- `sample = holdout`

Each holdout row uses the exact parameter combination selected by highest
training `net_usd` in that window.

Key fields:

- `split_id`
- `sample`
- `trade_dates`
- `direction_filter`
- `target_r_multiple`
- `stop_buffer_points`
- `evaluated_trades`
- `net_usd`

## Current Sample Result

The current ES sample uses `3` train dates and `1` holdout date per rolling
window.

Current result:

- walk-forward windows: `5`
- selected holdout trades: `10`
- selected holdout net: `-847.50` USD

Selected holdout rows:

| Holdout date | Direction | Target R | Stop buffer | Trades | Net USD |
| --- | --- | ---: | ---: | ---: | ---: |
| `2026-06-15` | `long` | `0.5` | `0` | `6` | `529.00` |
| `2026-06-16` | `long` | `3` | `1` | `4` | `-1376.50` |
| `2026-06-17` | `long` | `2.5` | `1` | `0` | `0.00` |
| `2026-06-18` | `long` | `2.5` | `1` | `0` | `0.00` |
| `2026-06-19` | `short` | `1.5` | `0.5` | `0` | `0.00` |

This does not validate the baseline. The selected walk-forward holdout sample
is negative and has too few trades to support a strategy claim.
