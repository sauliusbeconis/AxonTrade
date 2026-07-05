# Sierra MNQ Eval-Pass Combined Bot

Current status: Sierra live test/mechanics passed on `2026-07-05`. Controlled
live routing is approved for the validated MNQ A+B eval-pass setup under the
gates below.

`AxonTrade MNQ Eval Pass Combined Bot` is the live-capable ACSIL implementation
of the combined MNQ eval-pass A+B research candidate.

## Status

- source: `src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`
- Sierra export: `scsf_AxonTradeMnqEvalPassCombinedBot`
- chart study name: `AxonTrade MNQ Eval Pass Combined Bot`
- current state: built in source, syntax checked, Sierra live test/mechanics
  passed
- live approval: **approved for controlled live routing**

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

## Controlled Live Routing Checklist

1. Source has already been synced by the repo script. If needed, sync again:

```bash
export WINEPREFIX="/home/saulius/WinePrefixes/SierraChart"
bash scripts/sync_to_sierra.sh
```

2. In Sierra Chart, compile `AxonTradeVwapDeltaExecutionBot.cpp` after any
   source update.
3. Add `AxonTrade MNQ Eval Pass Combined Bot` to a clean MNQ chart.
4. Confirm selected chart symbol starts with `MNQ`.
5. Confirm Sierra trade simulation mode is off.
6. Set `Send Orders To Trade Service = Yes`.
7. Set `Confirmation Text = MNQ_EVAL_PASS_AB_LIVE`.
8. Set `Allowed Trade Account` to the exact selected Trade Window account.
9. Confirm `A Plus Quantity = 12`, `B Fast Quantity = 4`, and
   `Max Position Quantity = 12`.
10. Confirm no other automated bot is running on the same account/instrument.
11. Set `Arm Execution = Yes` only when the status banner shows all gates ready.
