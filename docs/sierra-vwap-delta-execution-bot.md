# Sierra VWAP Delta Execution Bot

`AxonTradeVwapDeltaExecutionBot.cpp` is the simulation-only mechanics test for
the current VWAP/delta exhaustion fade candidate.

Manual help needed now: **Yes.** You need to compile the study in Sierra Chart,
load it on a chart, and arm it for simulation testing.

Manual help needed after it is loaded: **Yes for the first mechanics test only.**
After one clean parent order plus attached targets/stop is verified, it can be
left running in Sierra simulation mode.

This build rejects live trade-service routing. Even if the input
`Send Orders To Trade Service` is changed to `Yes`, the study logs a rejection
and does not submit the entry.

## What It Does

- evaluates the same selected VWAP/delta exhaustion fade rule as the live-sim
  study;
- submits Sierra Chart simulation entries only when explicitly armed;
- uses one market parent order;
- attaches two limit targets and one common stop;
- optionally moves the common stop to breakeven after target 1;
- flattens and cancels working orders at the configured session flatten time;
- blocks new entries after the daily loss lock or daily profit lock is reached;
- writes mechanics rows to:

`C:\SierraChart\Data\AxonTrade_VwapDeltaExecutionBot.csv`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_VwapDeltaExecutionBot.csv`

## Risk Defaults

Defaults are deliberately small for mechanics testing:

- chart symbol gate: `MES`
- first leg quantity: `1`
- runner quantity: `1`
- total max position quantity: `2`
- initial stop: `10` points
- first target: `6` points
- runner target: `12` points
- daily loss lock: `$200`
- daily profit lock: `$650`
- move stop to breakeven after target 1: `No`

Sizing reality:

- `1 + 1 MES` with a 10-point full stop is about `-$100` before costs;
- `2 + 2 MES` is about `-$200` before costs;
- `5 + 5 MES` is about `-$500` before costs.

So for your preferred `-$150` to `-$250` daily loss band, do not use `5 + 5`
with the current 10-point stop. Use `1 + 1 MES` for mechanics, or at most
`2 + 2 MES` if you intentionally want the larger test.

## Sync Source Into Sierra

Manual help needed: **No** for this command.

From the repo:

```bash
bash scripts/sync_to_sierra.sh
```

This copies the source to:

`C:\SierraChart\ACS_Source\AxonTradeVwapDeltaExecutionBot.cpp`

## Build In Sierra Chart

Manual help needed: **Yes**.

Use this exact Sierra Chart path:

1. Click `Analysis >> Build Custom Studies DLL`.
2. In `Build Advanced Custom Studies DLL`, click `File >> Select Files`.
3. Select `AxonTradeVwapDeltaExecutionBot.cpp`.
4. Click `Open`.
5. Click `Build >> Remote Build`.
6. Wait for the build output to say the remote build succeeded.
7. If Sierra asks to allow loading DLLs, click `Build >> Allow Load DLLs`.

If the build output says:

`Can't recognize 'cl ...' as an internal or external command`

you clicked the local Visual C++ build path. In the same build window, click
`Build >> Remote Build`.

## Prepare A MES Mechanics Chart

Manual help needed: **Yes**.

Use MES for the mechanics bot. The study default rejects ES symbols because
`Required Symbol Prefix = MES`.

Fast path from your existing ES orderflow chart:

1. Click the ES 3-minute orderflow chart window.
2. Click `Chart >> Duplicate Chart`.
3. Click the duplicated chart window.
4. Click `Chart >> Chart Settings`.
5. In the `Symbol` field, set the current MES contract, for example
   `MESU26-CME` for the September 2026 contract.
6. Confirm the bar period is still `3 Min`.
7. Click `Apply`.
8. Click `OK`.
9. Click `Trade >> Trade Simulation Mode On` and confirm it is checked.
10. Confirm the chart title bar shows `[Sim]`.

If Sierra does not accept the typed symbol:

1. Click `File >> Find Symbol`.
2. Find the CME Micro E-mini S&P 500 futures list.
3. Select the current MES contract.
4. Click `Open Intraday Chart`.
5. Set it to a `3 Min` chart with `Chart >> Chart Settings`.

## Load The Study

Manual help needed: **Yes**.

1. Click the MES 3-minute mechanics chart window.
2. Click `Analysis >> Studies`.
3. Click `Add Custom Study`.
4. Expand or find `AxonTrade VWAP Delta Execution Bot`.
5. Select `AxonTrade VWAP Delta Execution Bot`.
6. Click `Add`.
7. In `Studies to Graph`, select `AxonTrade VWAP Delta Execution Bot`.
8. Click `Settings`.
9. In `Settings and Inputs`, set or confirm:
   - `CSV Log Path = C:\SierraChart\Data\AxonTrade_VwapDeltaExecutionBot.csv`
   - `Trade Mode = execution_sim`
   - `Arm Execution = No`
   - `Send Orders To Trade Service = No`
   - `Require Trade Simulation Mode = Yes`
   - `Confirmation Text = SIM_ONLY`
   - `Required Symbol Prefix = MES`
   - `Log Rejections = No`
   - `Process Full Recalculation = No`
   - `Reset CSV On Full Recalculation = Yes`
   - `Setup Start Time = 09:45:00`
   - `Setup End Time = 15:45:00`
   - `Flatten Time = 16:40:00`
   - `VWAP Extension Points = 2`
   - `Minimum Bar Delta = 10`
   - `Close Location Threshold = 0.5`
   - `Minimum Raw Candidate Spacing Seconds = 900`
   - `Max Raw Candidates Per Day = 20`
   - `Context Lookback Bars = 20`
   - `Maximum Lookback Directional Move Points = -2.5`
   - `Minimum Session Range Points = 30`
   - `Max Risk To Average Bar Range = 1.75`
   - `Initial Stop Points = 10`
   - `First Target Points = 6`
   - `Runner Target Points = 12`
   - `First Leg Quantity = 1`
   - `Runner Quantity = 1`
   - `Max Position Quantity = 2`
   - `Daily Loss Lock USD = 200`
   - `Daily Profit Lock USD = 650`
   - `Move Stop To Break Even After First Target = No`
   - `Break Even Offset Ticks = 0`
10. Click `OK`.
11. Click `OK` again to close Chart Studies.

At this point the study is loaded but not armed. It should not place orders.

## First Mechanics Test

Manual help needed: **Yes**.

1. Confirm `Trade >> Trade Simulation Mode On` is checked.
2. Confirm the chart title bar shows `[Sim]`.
3. Confirm the chart symbol starts with `MES`.
4. Click `Analysis >> Studies`.
5. Select `AxonTrade VWAP Delta Execution Bot`.
6. Click `Settings`.
7. Set `Arm Execution = Yes`.
8. Confirm `Send Orders To Trade Service = No`.
9. Confirm `Confirmation Text = SIM_ONLY`.
10. Click `OK`.
11. Click `OK` again to close Chart Studies.
12. Let live bars or replay bars close through the setup window.
13. When the first entry appears, click `Trade >> Trade Activity Log`.
14. In the Trade Activity Log, check for:
    - one parent market order;
    - one target 1 limit order;
    - one target 2 limit order;
    - one common stop order.
15. After the first submitted order is verified, click `Analysis >> Studies`.
16. Select `AxonTrade VWAP Delta Execution Bot`.
17. Click `Settings`.
18. Set `Arm Execution = No`.
19. Click `OK`.
20. Click `OK` again to close Chart Studies.

If you need to manually stop the mechanics test, use:

`Trade >> Flatten And Cancel`

Then set:

`Analysis >> Studies >> AxonTrade VWAP Delta Execution Bot >> Settings >> Arm Execution = No`

## Optional Breakeven Test

Manual help needed: **Yes**.

Only test this after the basic attached-order mechanics are verified.

1. Click `Analysis >> Studies`.
2. Select `AxonTrade VWAP Delta Execution Bot`.
3. Click `Settings`.
4. Set `Move Stop To Break Even After First Target = Yes`.
5. Set `Break Even Offset Ticks = 0`.
6. Click `OK`.
7. Click `OK` again to close Chart Studies.

This changes execution behavior versus the currently selected research variant,
which used the initial stop.

## Expected Log Rows

- `execution_signal_rejected`: a raw setup was seen but blocked by a rule gate.
- `execution_entry_rejected`: a valid setup was blocked by safety settings.
- `execution_entry_submitted`: a simulation parent order was accepted by Sierra.
- `execution_entry_error`: Sierra rejected the simulated entry request.
- `execution_flatten_submitted`: the study submitted a flatten/cancel action.

The most useful CSV fields for mechanics debugging are:

- `event_type`
- `timestamp`
- `symbol`
- `trade_account`
- `signal_id`
- `direction`
- `quantity`
- `parent_internal_order_id`
- `target1_internal_order_id`
- `target2_internal_order_id`
- `stop_all_internal_order_id`
- `daily_loss_view`
- `daily_profit_view`
- `rejection_reason`
- `notes`

## Hard Limits Of This Test

This is a mechanics test, not proof that live trading is ready.

- It confirms Sierra accepts the parent order and attached orders.
- It confirms the arming gates, symbol gate, sim-mode gate, and CSV logging work.
- It does not replace historical validation.
- It does not need months of forward logs.
- It does not allow live trade-service routing in this build.
