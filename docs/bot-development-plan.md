# Bot Development Plan

AxonTrade is a bot project, but not a live-order-routing project in the current
phase. The near-term goal is to build a research and simulation pipeline that can
produce, log, replay, and evaluate signals before any execution work is allowed.

## Current Bot Definition

In the current phase, "bot" means:

- deterministic signal rules;
- reproducible data inputs;
- candidate signal logging;
- rejected signal logging;
- chart overlays for review;
- replay and simulation validation;
- offline reports with costs and slippage.

It does not mean:

- live order routing;
- broker integration;
- hidden automated entries;
- martingale, grid, averaging-down, or revenge logic;
- optimization without holdout validation.

## Sierra Chart Role

The Sierra Chart workspace is only the harness. It is not the product.

Minimum required Sierra setup for bot development:

- correct ES/MES futures symbol;
- simulation mode visible;
- one clean chart with VWAP and key levels;
- one execution/replay chart where AxonTrade can draw signal markers;
- CSV logging path available;
- chartbook saved and repeatable.

Optional Sierra setup:

- TPO context;
- footprint / Numbers Bars;
- DOM;
- liquidity heatmap.

Those optional views are useful for review and diagnostics, but they must not
block building the signal engine and logger.

## Development Sequence

### 1. Data Contract

Define the CSV schemas that Sierra Chart and AxonTrade will exchange:

- bar data;
- calculated levels;
- candidate signals;
- rejected signals;
- replay verification events;
- simulated trade outcomes.

### 2. Price-Only Baseline

Build the first baseline without footprint or heatmap dependencies.

Initial inputs:

- instrument config;
- session template;
- VWAP;
- opening range;
- overnight high and low;
- prior day high and low;
- prior VAH, VAL, and POC when available.

Initial output:

- no-trade / candidate-signal decisions;
- rejection reasons;
- expected stop/reference level;
- expected target/reference level;
- research-only confidence fields.

### 3. Sierra Signal Overlay And Logger

Extend ACSIL with indicator-only behavior:

- draw candidate signal markers;
- draw invalidation/reference levels;
- write deterministic CSV rows;
- avoid duplicate rows on recalculation;
- never submit, modify, cancel, flatten, or route orders.

### 4. Offline Evaluator

Build Python tools to:

- load logged signal CSV files;
- join signal rows to bar data;
- apply cost and slippage assumptions;
- produce reports;
- compare accepted and rejected signals;
- preserve chronological walk-forward evaluation.

### 5. Replay Verification

Use Sierra Chart replay to confirm:

- signal markers appear at the expected bars;
- rejected signals are logged;
- duplicate rows are not created;
- reports match the replay output.

### 6. Simulation-Only Execution Research

Only after baseline reports and safety checks are stable, consider a separate
simulation-only assistant phase. This still does not authorize live automation.

## Completed Foundation

- `config/research/signal_log_schema.yaml` defines the first signal log contract.
- Python validation checks schema consistency and signal/rejection rows.
- `OrderFlowSignalSmokeTest.cpp` writes schema-compatible CSV rows and draws
  indicator-only signal references.
- `config/research/price_only_vwap_reclaim.yaml` and the price-only baseline
  module emit first-pass candidate/rejected signal rows from bar and level data.

## Next Concrete Task

Connect Sierra-exported bar/level data to the baseline:

- document the exact Sierra Chart export columns;
- create a sample fixture from replay data;
- run the baseline over the exported fixture;
- compare generated candidate/rejected rows to the chart overlay output.
