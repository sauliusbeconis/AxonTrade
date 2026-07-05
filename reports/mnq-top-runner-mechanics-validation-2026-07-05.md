# MNQ Top-Runner Filtered Mechanics Validation

Status: Sierra DLL build and fresh replay/mechanics validation passed for the
filtered-rule Top Runner implementation.

Date: `2026-07-05`

## Study

- Sierra study: `AxonTrade MNQ Top Runner Sim Bot`
- Confirmation text: `MNQ_TOP_RUNNER_SIM`
- Mode: simulation/replay only
- Live trade-service routing: rejected by design
- Source: `src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`
- Implementation: filtered frozen Top Runner rule from
  `reports/mnq-top-runner-deep-validation.md`

## Validated Candidate

- family: MNQ lookback-breakout continuation runner
- chart: MNQ `3 Min` order-flow chart
- raw setup window: `10:00-12:30`
- final tradable filter window: `10:00-11:00`
- weekdays: Monday through Thursday; Friday skipped
- lookback: `20` bars
- buffer: `0`
- delta threshold: `600`
- raw directional close-location threshold: `0.65`
- final directional close-location threshold: `0.9`
- default sizing: `2 MNQ`
- default target/stop: `160 / 70`
- minimum raw setup spacing: `3600` seconds
- flatten: `15:45`

## Result

Operator confirmed the Sierra DLL was built and a fresh replay/mechanics pass
completed after the filtered-rule ACSIL alignment.

This pass does not approve live routing. It confirms that the replay/simulation
study can be used as the mechanics reference for the separate live-capable
lower-DD staging version.

## Next Gate

Before any Top Runner live approval:

- stage `AxonTrade MNQ Top Runner Live Bot` on a clean MNQ `3 Min` chart
- use confirmation text `MNQ_TOP_RUNNER_LIVE`
- use exact `Allowed Trade Account`
- keep `2 MNQ`, lower-DD `120 / 70`, and `$300` daily loss lock
- verify Sierra simulation mode is off and `Send Orders To Trade Service = Yes`
- run controlled live staging; do not treat this as approved unattended live
  automation yet
