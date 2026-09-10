# Safety Case

AxonTrade is in a mixed phase. Research and execution-mechanics work remain
simulation-safe, and controlled live order routing is approved for a named set
of validated exports. Live capability is a property a specific export earns and
holds under named gates. It is not a property of the repository, and it is not
granted to a strategy by research results alone.

At this snapshot the approved controlled live-routing exports are
`AxonTrade MES Eval Live Bot`, `AxonTrade MNQ Eval Live Bot`,
`AxonTrade MNQ Eval Pass Combined Bot`, and `AxonTrade MGC Normal BreakEven Bot`.

`AxonTrade MNQ Top Runner Live Bot` is a controlled live-staging candidate and
is not approved. `AxonTrade MNQ Top Runner Sim Bot` and
`AxonTrade VWAP Delta Execution Bot` are simulation and replay only; the latter
rejects live trade-service routing outright rather than warning.

## Safety Claims

- Platform-side order functions are allowed only inside the approved execution
  harness, `src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`. No other ACSIL source
  may contain order-routing calls.
- Live routing is per-export and attended. No export is approved for unattended
  automation.
- An export becomes live-capable only after research acceptance gates pass,
  Sierra mechanics validation passes, and controlled live staging is reviewed.
  Each of those is a separate decision.
- Strategy code and research scripts must treat account rules as external
  configuration, not hardcoded assumptions.
- Risk limits during development and live routing must be stricter than the
  relevant prop-firm limits.
- Every strategy must be documented as a hypothesis before it is tested.
- Widening live capability — a new export, a new instrument, or larger size —
  requires an explicit decision recorded in the decision log, not an incremental
  parameter change.

## Prohibited Behavior

- Order-routing calls in any ACSIL source other than the approved execution
  harness.
- Live routing from an export that is not on the approved list above.
- Unattended live automation.
- Hidden live-trading flags, or any path that reaches live routing without the
  arming, symbol, confirmation-text, account, and routing-mode gates.
- Broker credentials or account numbers in the repository.
- Martingale, averaging down, grid recovery, revenge sizing, unlimited scaling,
  HFT behavior, or microscalping behavior.

## Required Controls

Repository-level:

- Static search to ensure ACSIL order-routing calls are isolated to the approved
  execution harness. Enforced by `scripts/check_repo.sh` and run in CI.
- Manual safety review before any execution work.
- Recalculation-safe Sierra Chart drawings and logging.

Research-level:

- Chronological walk-forward testing.
- Untouched holdout periods, kept untouched until the research design is locked.
- Cost and slippage assumptions in every strategy report.
- Executable acceptance gates in `config/research/`, so a passed gate is
  reproducible rather than asserted.

Runtime, before any live-capable export may route an order:

- `Arm Execution = Yes` set deliberately, after the chart, account, confirmation
  text, and routing mode are staged.
- Chart symbol matching the export's required prefix.
- Confirmation text matching the export's expected value.
- `Allowed Trade Account` exactly matching the selected Sierra trade account.
- Routing mode matching the export's declared mode; simulation-only exports
  reject live trade-service routing.
- Daily loss lock, daily profit lock, and eval trailing lock configured.
- Forced flatten time configured.
- No arming while Sierra is downloading historical data.

## Open Verification Items

- Confirm current LucidFlex rules from official account documents.
- Confirm Sierra Chart ACSIL APIs used by the smoke test under the target Wine
  environment.
- Confirm CSV logging behavior during replay and repeated recalculation.
- Keep the approved-export list in this document and in the README Safety Status
  section consistent whenever an export changes status.
