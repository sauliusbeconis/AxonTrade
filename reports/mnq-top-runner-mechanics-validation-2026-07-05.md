# MNQ Top-Runner Mechanics Validation

Status: Sierra replay/mechanics validation passed.

Date: `2026-07-05`

## Study

- Sierra study: `AxonTrade MNQ Top Runner Sim Bot`
- Confirmation text: `MNQ_TOP_RUNNER_SIM`
- Mode: simulation/replay only
- Live trade-service routing: rejected by design
- Source: `src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`

## Validated Candidate

- family: MNQ lookback-breakout continuation runner
- chart: MNQ `3 Min` order-flow chart
- setup window: `10:00-11:00`
- weekdays: Monday through Thursday; Friday skipped
- lookback: `20` bars
- buffer: `0`
- delta threshold: `600`
- directional close-location threshold: `0.9`
- default sizing: `2 MNQ`
- default target/stop: `160 / 70`
- minimum submitted-signal spacing: `3600` seconds
- flatten: `15:45`

## Result

Operator replay/mechanics validation passed. The study is considered ready for
the next implementation review gate.

This pass does not approve live routing. It confirms that the replay/simulation
study can be used as the mechanics reference for a future live-capable version.

## Next Gate

Before any live-capable build:

- choose the live candidate variant: high-PF `160 / 70`, lower-DD `120 / 70`,
  or higher-sample `cl >= 0.8` with `160 / 70`
- define account-level daily loss/profit locks
- define max quantity and multi-account scaling rules
- build a separate guarded live-capable study rather than enabling routing in
  the sim study
