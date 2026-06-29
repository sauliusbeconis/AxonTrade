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
- Add target R-multiple sweep for logged Sierra overlay candidates. Done.
- Add rolling walk-forward validation for logged Sierra overlay target R sweeps. Done.
- Add signal quality diagnostics for logged Sierra overlay outcomes. Done.
- Add dynamic breakeven stop sweeps and walk-forward validation for logged Sierra overlay candidates. Done.
- Add fixed two-contract scaled-scalp exit sweeps and walk-forward validation for logged Sierra overlay candidates. Done.
- Add random/VWAP/impulse synthetic scalp-entry baselines for logged Sierra overlay bars. Done.
- Add order-flow proxy and passive-touch sensitivity baselines for synthetic scalp entries. Done.
- Add passive-touch wait-window sensitivity for synthetic scalp entries. Done.
- Add passive-entry plus market-exit slippage sensitivity for synthetic scalp entries. Done.
- Add walk-forward validation for fast passive synthetic scalp candidates. Done.
- Add perfect-fill and half-tick walk-forward cost threshold checks for synthetic scalp entries. Done.
- Add larger-target/larger-stop walk-forward checks for synthetic scalp entries. Done.
- Add time-based session-structure synthetic entry families. Done.
- Add non-overlapping step control for scaled-scalp walk-forward windows. Done.
- Add trade-level audit for the spaced delta-impulse continuation lead. Done.
- Add exit-stability or fixed-exit validation for the spaced delta-impulse continuation lead. Done.
- Build a dedicated Sierra overlay candidate for fixed-exit spaced delta-impulse continuation. Done.
- Validate the Sierra delta-impulse overlay log against the Python-generated baseline.
- Add fixed-row robustness and holiday/early-close diagnostics for the Sierra delta-impulse overlay. Done.
- Add entry-quality filter sweeps and walk-forward validation for logged Sierra overlay diagnostics. Done.
- Add volatility/activity-normalized sweep features for logged Sierra overlay diagnostics. Done.
- Add trade-level audits for selected auction-regime target/breakeven stacks. Done.
- Add acceptance gates for selected auction-regime stack trade-level audits. Done.
- Add one-command auction-regime target/breakeven stack pipeline. Done.
- Build walk-forward filters over normalized context features after the sample is large enough.
- Add scheduled-news exclusion to Sierra overlay research exports. Done.
- Populate scheduled-news calendar for the current Sierra overlay sample.

## Reporting

- Define the first price-only baseline outcome workflow. Done.
- Define rejected-signal logging fields.
- Define parameter experiment logging format. Done.
- Define daily outcome and drawdown breakdown. Done.
- Build Sierra overlay signal-log validation/report workflow. Done.
- Document Sierra overlay signal-log outcome workflow. Done.
