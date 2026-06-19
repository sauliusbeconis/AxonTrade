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

Override the grid with:

```bash
--target-r-multiples 1,1.5,2
--stop-buffers 0,0.25,0.5
--minimum-opening-range-widths 1,5,10
```

## Output Format

The output CSV is aggregate-only: one row per parameter combination.

Key fields:

- `experiment_id`
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

The current ES sample wrote `24` experiment rows.

Best net result in the default grid:

- target R multiple: `1.5`
- stop buffer: `0`
- minimum opening-range width: `1`
- candidate signals: `47`
- target hits: `19`
- losses: `24`
- other exits: `4`
- net ES result after default costs: `-2927.00` USD

Every default-grid combination is negative after costs. This supports keeping
the price-only baseline as a control strategy before adding any order-flow
features.
