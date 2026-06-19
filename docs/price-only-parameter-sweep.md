# Price-Only Parameter Sweep

This workflow tests whether the current price-only baseline is sensitive to
simple stop/target settings. It is research-only and does not place, modify,
cancel, or flatten orders.

Manual help is not needed after the Sierra Chart export file exists.

## Run

From the repository:

```bash
.venv/bin/python scripts/run_price_only_parameter_sweep.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_BarStudyExport.txt \
  reports/price-only-parameter-sweep-sample.csv \
  --symbol ESU26-CME \
  --chart-number 1 \
  --session-phase rth
```

The default grid tests:

- target R multiples: `0.5,1,1.5,2,2.5,3`;
- stop buffers in points: `0,0.25,0.5,1`;
- minimum opening-range width: `1`.
- direction filters: `all,long,short`.

Override the grid with:

```bash
--target-r-multiples 1,1.5,2
--stop-buffers 0,0.25,0.5
--minimum-opening-range-widths 1,5,10
--direction-filters all,long,short
```

## Output Format

The output CSV is aggregate-only: one row per parameter combination.

Key fields:

- `experiment_id`
- `direction_filter`
- `target_r_multiple`
- `stop_buffer_points`
- `minimum_opening_range_width_points`
- `candidate_signals`
- `evaluated_trades`
- `target_hits`
- `losses`
- `other_exits`
- `gross_usd`
- `net_usd`
- `average_net_usd`
- `long_trades`
- `short_trades`

## Current Sample Result

The current ES sample wrote `72` experiment rows.

Best net result for all directions enabled:

- target R multiple: `1.5`
- stop buffer: `0`
- minimum opening-range width: `1`
- candidate signals: `47`
- target hits: `19`
- losses: `24`
- other exits: `4`
- net ES result after default costs: `-2927.00` USD

Best net result across direction filters:

- direction filter: `long`
- target R multiple: `2.5`
- stop buffer: `1`
- evaluated trades: `11`
- target hits: `4`
- losses: `6`
- other exits: `1`
- net ES result after default costs: `1167.75` USD

All positive rows in the current sample are long-only rows. This is a research
lead, not a tradable rule, because it is based on only `11` long candidates in
one export sample.
