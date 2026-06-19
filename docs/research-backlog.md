# Research Backlog

Every research source should be documented with a link and retrieval date.

## Account And Platform Rules

- Collect official LucidFlex rules and compare them to `config/firms/lucidflex_25k_evaluation.yaml`.
- Collect Sierra Chart ACSIL documentation links.
- Collect Sierra Chart `VolumeAtPriceForBars` references.
- Research prop-firm restrictions around HFT and microscalping.

## Market Research

- Research time-series momentum evidence.
- Research intraday momentum evidence.
- Research order-flow imbalance literature.
- Research realistic futures commissions and slippage.

## Methodology

- Research backtest overfitting.
- Research walk-forward validation practices for intraday time series.
- Research realistic trade-count thresholds for intraday strategy evaluation.

## Bot Pipeline

- Define the first signal log schema.
- Define rejected-signal reason codes.
- Define Sierra Chart export fields for bars and levels.
- Build Python loaders for Sierra-exported CSV files.
- Build the first price-only VWAP/opening-range baseline.
- Add an indicator-only ACSIL signal overlay and CSV logger.

## Reporting

- Define the first price-only baseline report.
- Define rejected-signal logging fields.
- Define parameter experiment logging format.
