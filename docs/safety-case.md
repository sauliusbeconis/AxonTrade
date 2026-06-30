# Safety Case

AxonTrade is currently in a foundation, simulation-safe research, and simulation
execution-mechanics phase. Live order routing is prohibited.

## Safety Claims

- The repository must not contain live trade-service routing code.
- Platform-side order functions are allowed only inside the approved
  simulation-only execution harness.
- Strategy code and research scripts must treat account rules as external configuration, not hardcoded assumptions.
- Risk limits during development must be stricter than the relevant prop-firm limits.
- Every strategy must be documented as a hypothesis before it is tested.
- Live automation requires a future explicit phase change and safety review.

## Prohibited Behavior

- Live order routing.
- Hidden live-trading flags.
- Broker credentials or account numbers in the repository.
- Martingale, averaging down, grid recovery, revenge sizing, unlimited scaling, HFT behavior, or microscalping behavior.

## Required Controls

- Manual safety review before any execution work.
- Static search to ensure ACSIL order-routing calls are isolated to the approved
  simulation-only execution harness.
- Recalculation-safe Sierra Chart drawings and logging.
- Chronological walk-forward testing.
- Untouched holdout periods.
- Cost and slippage assumptions in every strategy report.
- Sierra Chart simulation mode, explicit arming, symbol-prefix gating, and
  confirmation-text gating before simulation entries are allowed.

## Open Verification Items

- Confirm current LucidFlex rules from official account documents.
- Confirm Sierra Chart ACSIL APIs used by the smoke test under the target Wine environment.
- Confirm CSV logging behavior during replay and repeated recalculation.
