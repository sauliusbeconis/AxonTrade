# Phase Roadmap

## Phase 0: Foundation

- Repository structure.
- Documentation.
- YAML configs.
- Python config and risk skeleton.
- ACSIL indicator-only smoke test.
- Manual Sierra Chart replay verification.

## Phase 1: Offline Research

- Data import and validation.
- Price-only baseline.
- Chronological walk-forward tests.
- Cost and slippage modeling.
- Reproducible reports.

## Phase 2: Simulation And Replay

- Sierra Chart replay studies.
- Signal logging with rejected-signal tracking.
- Forward simulation with no live routing.
- Safety review of risk-governor behavior.

## Phase 3: Supervised Execution Research

Requires explicit future authorization.

- One-click or manually approved simulated entries only if safety gates approve.
- Protective-exit design review.
- Prop-firm rule compliance review.

## Phase 4: Live Automation Review

Requires explicit future authorization and a separate safety case.

Live automation is not part of the current phase.
