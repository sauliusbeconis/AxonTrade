# Phase Roadmap

## Phase 0: Foundation

- Repository structure.
- Documentation.
- YAML configs.
- Python config and risk skeleton.
- ACSIL indicator-only smoke test.
- Manual Sierra Chart replay verification.
- Minimal Sierra Chart bot harness: correct futures symbol, simulation mode,
  VWAP/levels, and repeatable chartbook. Heatmap is optional.

## Phase 1: Offline Research

- Data contract for bars, levels, candidate signals, rejected signals, and replay
  events.
- Data import and validation.
- Price-only baseline.
- Chronological walk-forward tests.
- Cost and slippage modeling.
- Reproducible reports.

## Phase 2: Simulation And Replay

- Sierra Chart replay studies.
- Indicator-only signal overlay.
- Signal logging with rejected-signal tracking.
- Forward simulation with no live routing.
- Safety review of risk-governor behavior.

## Phase 3: Supervised Execution Research

- One-click or manually approved simulated entries only if safety gates approve.
- Protective-exit design review.
- Prop-firm rule compliance review.
- Controlled MES evaluation deployment with explicit account whitelist,
  confirmation text, daily loss/profit locks, and trailing drawdown lock.

## Phase 4: Live Automation Review

Requires a separate safety case before expanding beyond the current MES eval
study.

Live automation is limited to the explicitly gated `AxonTrade MES Eval Live Bot`.
