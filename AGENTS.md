# AGENTS.md

## Project Identity

AxonTrade is a professional-grade futures trading research and execution laboratory.

It is not a get-rich-quick bot, signal seller, black-box system, martingale engine, grid bot, or high-frequency scalper.

The initial focus is intraday ES/MES and NQ/MNQ research using Sierra Chart ACSIL for platform-side logic and Python for offline research.

## Prime Directive

Research first. Safety second. Execution third. Live automation last.

No strategy may trade live until it has passed documented research, simulation, replay, forward-test, and safety-review gates.

## Current Phase

The current phase is foundation and simulation-safe research tooling.

Live order routing is prohibited in this phase.

## Hard Safety Rules

Do not add live order-routing code unless a future task explicitly authorizes a live-trading phase.

Do not call:

- `sc.BuyEntry`
- `sc.SellEntry`
- `sc.BuyOrder`
- `sc.SellOrder`
- `sc.BuyExit`
- `sc.SellExit`
- `sc.FlattenAndCancelAllOrders`

Do not submit, modify, cancel, flatten, or route orders.

Do not add hidden live-trading flags.

Do not store broker credentials, Rithmic credentials, API keys, account numbers, passwords, or personal secrets.

Do not implement martingale logic, averaging down, grid recovery, revenge sizing, unlimited scaling, HFT logic, or microscalping logic.

Protective exits always have priority over any holding-time preference.

## Research Rules

Every strategy begins as a hypothesis.

Every strategy must have:

- a written thesis;
- exact entry rules;
- exact exit rules;
- invalidation rules;
- risk rules;
- excluded market conditions;
- cost assumptions;
- slippage assumptions;
- data requirements;
- known failure modes.

A price-only baseline must be tested before adding order-flow features.

Order-flow features must be evaluated through ablation tests.

ES/MES and NQ/MNQ must be evaluated separately.

Use chronological walk-forward testing. Do not randomly shuffle time-series trading data.

Reserve untouched holdout periods.

Track all rejected signals, not only accepted signals.

Log all parameter experiments. Do not report only the best result.

Prefer robust parameter ranges over one perfect optimized setting.

## Strategy Families Under Research

Initial strategy families:

1. Contextual momentum reclaim / pullback.
2. Failed auction / absorption proxy reversal.
3. Price-only baseline.
4. Order-flow feature ablation.

No strategy is assumed profitable.

## Engineering Rules

Use C++ ACSIL for Sierra Chart studies.

Use Python for offline research, reporting, configuration validation, and analytics.

Separate:

- feature extraction;
- signal detection;
- visualization;
- logging;
- risk controls;
- execution;
- research reporting.

Keep prop-firm rules in YAML configuration files.

Keep instrument settings in YAML configuration files.

Do not hardcode account rules into strategy logic.

Write clear documentation for Sierra Chart-specific ACSIL API usage.

Avoid duplicate drawings and duplicate log rows during Sierra Chart recalculation.

All scripts must fail safely with clear error messages.

## Prop-Firm Profile

The initial target account profile is LucidFlex 25K evaluation.

The project must respect:

- max loss limit;
- consistency rules;
- position limits;
- mandatory flatten time;
- HFT restrictions;
- microscalping restrictions.

Internal project limits should be stricter than firm limits during development.

## Definition Of Done

A task is not done unless:

1. files are created or changed intentionally;
2. assumptions are documented;
3. manual verification steps are written where needed;
4. tests or checks are added where practical;
5. no live-trading code is introduced accidentally;
6. the next safe task is clearly identified.
