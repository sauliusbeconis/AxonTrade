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
- Add first chronological train/holdout parameter check. Done.
- Add first rolling walk-forward parameter check. Done.

## Bot Pipeline

- Define the first signal log schema. Done.
- Define rejected-signal reason codes.
- Define Sierra Chart export fields for bars and levels. Done.
- Build Python loaders for Sierra-exported CSV files. Done.
- Build the first price-only VWAP/opening-range baseline. Done.
- Build the first price-only liquidity sweep reversal baseline. Done.
- Define Sierra bid/ask volume export fields for absorption research. Done.
- Build first bid/ask-volume absorption filter for liquidity sweep reversals. Done.
- Add chronological reward/risk filter experiment for absorption outcomes. Done.
- Add rolling reward/risk walk-forward experiment for absorption outcomes. Done.
- Add Sierra footprint/volume-at-price export fields for level-specific absorption research. Done.
- Build indicator-only Sierra volume-at-price CSV logger. Done.
- Build first level-specific absorption evaluator from volume-at-price exports. Done.
- Run parameter sweeps over level-specific absorption thresholds. Done.
- Run rolling walk-forward sweeps over level-specific absorption thresholds. Done.
- Build the first conservative stop/target outcome evaluator. Done.
- Add an indicator-only ACSIL signal overlay and CSV logger. Done.
- Add Sierra overlay signal-log outcome workflow with stale-export preflight. Done.
- Add MFE/MAE path diagnostics for evaluated Sierra overlay outcomes. Done.

## Reporting

- Define the first price-only baseline outcome workflow. Done.
- Define rejected-signal logging fields.
- Define parameter experiment logging format. Done.
- Define daily outcome and drawdown breakdown. Done.
- Build Sierra overlay signal-log validation/report workflow. Done.
- Document Sierra overlay signal-log outcome workflow. Done.
