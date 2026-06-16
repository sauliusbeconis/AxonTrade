# Research Methodology

Every AxonTrade strategy begins as a written hypothesis. The repository must not present a strategy as profitable until research evidence supports that claim.

## Required Strategy Definition

Each hypothesis must document:

- thesis;
- exact entry rules;
- exact exit rules;
- invalidation rules;
- risk rules;
- excluded market conditions;
- cost assumptions;
- slippage assumptions;
- data requirements;
- known failure modes.

## Baseline First

A price-only baseline must be tested before adding order-flow features. The baseline should use only price, time, and predeclared reference levels.

## Ablation Testing

Order-flow features must be added one layer at a time:

- baseline only;
- baseline plus volume-profile context;
- baseline plus stacked imbalance features;
- baseline plus absorption proxy;
- full model;
- simpler variants that remove each feature group.

## Time-Series Discipline

Use chronological walk-forward testing. Do not randomly shuffle trading data.

Reserve untouched holdout periods and keep them untouched until the research design is locked.

## Reporting Rules

Reports must include rejected signals, accepted signals, parameter experiments, costs, slippage, instrument-specific results, drawdown, holding time, and failure modes.

ES/MES and NQ/MNQ must be evaluated separately.
