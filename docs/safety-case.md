# Safety Case

**AxonTrade executes autonomously and unattended.** Approved exports place live
orders on their own. No human approves individual trades, and no human monitors
a session while it runs. Arming an export is a deliberate pre-session action; it
grants an autonomous session, it does not put a person in the loop during one.

Capital at risk is a prop-firm evaluation account — LucidFlex 25k, profiled in
`config/firms/lucidflex_25k_evaluation.yaml` — not a personal live brokerage
account. The firm permits automated strategies. Maximum loss is bounded by that
account's own limits rather than by anyone noticing a problem in time.

**The interlocks are the safety mechanism.** There are seven independent layers
rather than one check precisely because nothing is watching. Each layer must hold
on its own, because a failure that gets past one will not be caught by an
operator — there is no operator. That is the whole design premise of this
document, and every control below follows from it.

Live capability remains a property a specific export earns and holds under named
gates. It is not a property of the repository, and research results alone do not
grant it.

## Operating State

At this snapshot the approved live-routing exports are
`AxonTrade MES Eval Live Bot`, `AxonTrade MNQ Eval Live Bot`,
`AxonTrade MNQ Eval Pass Combined Bot`, and `AxonTrade MGC Normal BreakEven Bot`.

`AxonTrade MNQ Top Runner Live Bot` is a controlled live-staging candidate and is
not approved for routing. `AxonTrade MNQ Top Runner Sim Bot` and
`AxonTrade VWAP Delta Execution Bot` are simulation and replay only; the latter
rejects live trade-service routing outright rather than warning.

## Safety Claims

- Platform-side order functions are allowed only inside the approved execution
  harness, `src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`. No other ACSIL source
  may contain order-routing calls.
- Every gate is enforced in code, not by procedure. A control that depends on a
  person being present is not a control here.
- Every live-capable export carries self-enforcing capital limits — daily loss
  lock, daily profit lock, eval trailing lock, position caps, and a forced
  flatten time. These are what stop an unattended session, so they must be
  configured before an export may route.
- An export becomes live-capable only after research acceptance gates pass,
  Sierra mechanics validation passes, and controlled live staging is reviewed.
  Each of those is a separate decision.
- Strategy code and research scripts must treat account rules as external
  configuration, not hardcoded assumptions.
- Risk limits must be stricter than the prop-firm limits they map to.
- Every strategy must be documented as a hypothesis before it is tested.
- Widening live capability — a new export, a new instrument, or larger size —
  requires an explicit decision recorded in the decision log, not an incremental
  parameter change.

## Prohibited Behavior

- Order-routing calls in any ACSIL source other than the approved execution
  harness.
- Live routing from an export that is not on the approved list above.
- Routing on a personal live brokerage account. Approved routing targets the
  prop-firm evaluation account.
- Arming an export whose loss lock, profit lock, trailing lock, or flatten time
  is unset. An unattended session with no capital stop has no safety mechanism.
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

Runtime — the seven layers, all of which must hold without human intervention:

1. **Source.** Order-routing calls exist only in the approved execution harness.
2. **Instrument.** The chart symbol must match the export's required prefix
   (`MES`, `MNQ`, `MGC`) or the export refuses to arm.
3. **Intent.** The export's confirmation text must match its expected value.
4. **Account.** `Allowed Trade Account` must exactly equal the selected Sierra
   trade account.
5. **Routing mode.** The routing mode must match the export's declared mode;
   simulation-only exports reject live trade-service routing.
6. **Capital.** Daily loss lock, daily profit lock, eval trailing lock,
   per-export position caps, one-trade-per-day limits where declared, and a
   forced flatten time. These terminate an unattended session on their own.
7. **State.** The export will not arm while Sierra is downloading historical
   data.

Layers 1 through 5 and layer 7 are pre-conditions checked at arming. Layer 6
operates throughout the session and is the only thing that stops a running
strategy.

## Open Verification Items

- `config/firms/lucidflex_25k_evaluation.yaml` still declares
  `simulation_only: true` and `live_automated_entries_enabled: false`, and is
  annotated as a Phase-0 research configuration. Those flags describe the earlier
  research stage, not current operation. Reconcile them with the live state.
- Confirm current LucidFlex rules from official account documents. The profile
  records `source_status: official_sources_reviewed_recheck_before_live` against
  sources retrieved on 2026-06-29.
- Confirm Sierra Chart ACSIL APIs used by the smoke test under the target Wine
  environment.
- Confirm CSV logging behavior during replay and repeated recalculation.
- Keep the approved-export list in this document and in the README Safety Status
  section consistent whenever an export changes status.
