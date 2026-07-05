# Sierra MNQ Eval-Pass Combined Bot

Manual help needed: **Yes.** Sierra Chart must compile and load the updated
ACSIL study before replay/mechanics testing.

`AxonTrade MNQ Eval Pass Combined Bot` is the live-capable ACSIL implementation
of the combined MNQ eval-pass A+B research candidate.

## Status

- source: `src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`
- Sierra export: `scsf_AxonTradeMnqEvalPassCombinedBot`
- chart study name: `AxonTrade MNQ Eval Pass Combined Bot`
- current state: built in source, syntax checked, pending Sierra compile and
  replay/mechanics validation
- live approval: **not approved yet**

## Strategy

The bot implements `ab_earliest_one_per_day_fast` from
`reports/mnq-eval-pass-combined-ab.md`:

- exactly one submitted trade per chart date;
- earliest valid A+ or B signal wins;
- exact same-bar ties choose B because it uses lower size and lower planned
  stop risk.

A+ module:

- lookback breakout continuation;
- 40-bar same-date lookback;
- 2.5-point breakout buffer;
- delta threshold `600`;
- close location `>= 0.50` for longs or `<= 0.50` for shorts;
- absolute signal-bar delta cap `1000`;
- default quantity `12 MNQ`;
- target offset `31.0` points;
- stop offset `30.5` points.

B module:

- Tuesday/Wednesday short-only continuation;
- 10-bar same-date lookback;
- no breakout buffer;
- delta threshold `300`;
- close location `<= 0.45`;
- default quantity `4 MNQ`;
- target offset `82.0` points;
- stop offset `55.5` points.

## Required Settings

Use this only on a clean MNQ chart with good historical and live data.

- `Arm Execution = Yes` only after the chart/settings are intentionally staged
- `Send Orders To Trade Service = Yes` is required for order submission
- `Require Trade Simulation Mode Off = Yes` for final live eval routing
- `Confirmation Text = MNQ_EVAL_PASS_AB_LIVE`
- `Required Symbol Prefix = MNQ`
- `Allowed Trade Account =` exact Sierra Trade Window account text
- `Enable A Plus Module = Yes`
- `Enable B Fast Module = Yes`
- `A Plus Quantity = 12`
- `B Fast Quantity = 4`
- `Max Position Quantity = 12`
- `Daily Loss Lock USD = 900`
- `Daily Profit Lock USD = 650`
- `Max Eval Trailing Drawdown USD = 1000`
- `Draw Status Banner = Yes`
- `Draw Trade Markers And Levels = Yes`

## Safety Gates

The bot blocks new entries unless all live gates pass:

- armed;
- CSV path present;
- trade-service routing enabled;
- Sierra trade simulation mode off;
- confirmation text exact;
- allowed account exact;
- symbol prefix exact;
- no historical download in progress;
- no existing position or working orders;
- daily loss/profit and eval trailing drawdown locks clear;
- one-trade-per-day gate unused.

It also does not submit orders during full recalculation.

## Next Validation

1. Source has already been synced by the repo script. If needed, sync again:

```bash
export WINEPREFIX="/home/saulius/WinePrefixes/SierraChart"
bash scripts/sync_to_sierra.sh
```

2. In Sierra Chart, compile `AxonTradeVwapDeltaExecutionBot.cpp`.
3. Add `AxonTrade MNQ Eval Pass Combined Bot` to an MNQ replay chart.
4. First run with `Send Orders To Trade Service = No` and confirm the status
   banner blocks routing.
5. For replay/mechanics order submission, use Sierra simulation mode, set
   `Require Trade Simulation Mode Off = No`, set
   `Send Orders To Trade Service = Yes`, set the confirmation text, and arm only
   on the replay chart.
6. Replay/mechanics test accepted signals, attached target/stop placement, chart
   markers, fills, CSV rows, one-trade-per-day behavior, and lock behavior.
7. For final live eval routing, set `Require Trade Simulation Mode Off = Yes`,
   turn Sierra trade simulation mode off, confirm the exact account, and recheck
   the green status banner before arming.
