# Price-Only Liquidity Sweep Reversal

This workflow is the first concrete research pass for the liquidity sweep and
absorption reversal setup family.

Manual help is not needed after the Sierra Chart export file exists.

## Thesis

During the mid-day RTH window, an opening-range breakout that sweeps liquidity
but closes back inside the range may be a failed auction. The price-only version
does not claim absorption; it only creates the control sample that future
footprint and volume-at-price filters must beat.

## Current Proxy Rules

- Use only RTH rows.
- Build the opening range from `09:30:00` through `09:59:59`.
- Ignore the open and close; candidates are allowed from `10:30:00` through
  `15:15:00`.
- Require opening-range width of at least `1.0` point.
- Short setup: bar high sweeps at least `1.0` point above opening-range high,
  then closes at least `0.25` point back below opening-range high.
- Long setup: bar low sweeps at least `1.0` point below opening-range low, then
  closes at least `0.25` point back above opening-range low.
- Stop goes beyond the sweep bar extreme plus `0.25` point.
- Target is the opening-range midpoint.
- Reject trades with more than `20.0` points of initial risk.
- Emit only one candidate per symbol/date/side.

The rule profile is
`config/research/price_only_liquidity_sweep_reversal.yaml`.

## Run

From the repository:

```bash
.venv/bin/python scripts/run_price_only_liquidity_sweep.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_BarStudyExport.txt \
  data/processed/AxonTrade_ES_liquidity_sweep_signals.csv \
  data/processed/AxonTrade_ES_liquidity_sweep_outcomes.csv \
  --symbol ESU26-CME \
  --chart-number 1 \
  --session-phase rth
```

Write the Markdown report:

```bash
.venv/bin/python scripts/report_price_only_outcomes.py \
  data/processed/AxonTrade_ES_liquidity_sweep_signals.csv \
  data/processed/AxonTrade_ES_liquidity_sweep_outcomes.csv \
  reports/price-only-liquidity-sweep-sample.md
```

## Current Sample Result

The current June 2026 ES export produced:

- signals: `3030`
- candidates: `11`
- rejected: `3019`
- target hits: `2`
- stop/ambiguous losses: `9`
- net ES result after default costs: `-1057.25` USD

Direction split:

- long: `6` trades, `-1058.50` USD
- short: `5` trades, `1.25` USD

This rejects the price-only proxy as a standalone system. The next research
question is whether footprint/volume-at-price absorption filters remove enough
failed fades to improve this control sample after costs.

## Next Order-Flow Layer

The first absorption layer should require Sierra footprint fields that identify
aggressive participation failing to extend price. Candidate features:

- sweep-side volume spike;
- delta extreme into the sweep;
- close back inside the level despite sweep-side aggression;
- stacked imbalance failure near the sweep extreme;
- low continuation after the sweep bar.

Those features must be tested as an ablation against this price-only proxy.
