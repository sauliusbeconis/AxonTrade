# Price-Only Outcome Workflow

This workflow evaluates the first price-only baseline after a Sierra Chart export
exists. It is research-only and does not place, modify, cancel, or flatten
orders.

Manual help is not needed for this workflow after Sierra has already exported
the bar/study file.

## Inputs

Required local export:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_BarStudyExport.txt`

The runner:

- normalizes Sierra bars;
- computes the `09:30:00` to `09:59:59` opening range from bar highs/lows;
- generates price-only VWAP/opening-range candidate and rejected signals;
- evaluates each candidate against later same-day bars;
- writes both signal and outcome CSV files under `data/processed`.

## Run

From the repository:

```bash
.venv/bin/python scripts/run_price_only_outcomes.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_BarStudyExport.txt \
  data/processed/AxonTrade_ES_price_only_signals.csv \
  data/processed/AxonTrade_ES_price_only_outcomes.csv \
  --symbol ESU26-CME \
  --chart-number 1 \
  --session-phase rth
```

Replace `ESU26-CME` with the exact current symbol shown in Sierra Chart if it
differs.

## Model Rules

- Entry price is the candidate signal price.
- Only bars after the signal bar are scanned.
- Only bars from the same symbol and same date are scanned.
- A long exits at stop when a later bar's low touches the stop.
- A long exits at target when a later bar's high touches the target.
- A short exits at stop when a later bar's high touches the stop.
- A short exits at target when a later bar's low touches the target.
- If stop and target are both touched in the same later bar, the model records
  `ambiguous_stop_first`.
- If neither stop nor target is touched before the available same-day data ends,
  the model records `end_of_session`.

Cost assumptions come from:

- `config/instruments/ES.yaml`
- `config/research/default_costs.yaml`

Default ES cost model:

- `1` tick slippage per side;
- `1.75` USD commission per side;
- `50.00` USD per point.

Override slippage with:

```bash
--slippage-ticks-per-side 2
```

## Current Sample Result

The June 2026 ES export currently evaluates as:

- signals: `3030`
- candidates: `47`
- rejected: `2983`
- outcome wins: `8`
- outcome losses: `30`
- other exits: `9`
- net ES result after default costs: `-18152.00` USD

This result confirms the current price-only baseline is a control strategy, not
a tradable system.

## Write A Markdown Report

Manual help is not needed.

After the signal and outcome CSVs exist, write the report with:

```bash
.venv/bin/python scripts/report_price_only_outcomes.py \
  data/processed/AxonTrade_ES_price_only_signals.csv \
  data/processed/AxonTrade_ES_price_only_outcomes.csv \
  reports/price-only-outcome-sample.md
```

The report is deterministic from the two CSV inputs.

## Write A Daily Breakdown

Manual help is not needed.

After the outcome CSV exists, write a daily aggregate with:

```bash
.venv/bin/python scripts/summarize_outcomes_by_day.py \
  data/processed/AxonTrade_ES_price_only_outcomes.csv \
  reports/price-only-daily-outcome-sample.csv
```

The daily file includes trades, target hits, losses, other exits, direction
counts, average holding bars, cumulative net, and drawdown by entry date.

Current sample:

- trading dates with candidates: `7`
- worst day: `2026-06-11`, net `-8881.00` USD
- best day: `2026-06-15`, net `2404.00` USD
- final cumulative net: `-18152.00` USD
- max drawdown: `-18876.50` USD
