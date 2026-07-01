# Sierra VWAP Delta MES Eval Live Bot

`AxonTrade MES Eval Live Bot` is the guarded live-capable prop-eval study built
from `AxonTradeVwapDeltaExecutionBot.cpp`.

Manual help needed: **Yes.** This study can route live trade-service orders when
armed and all live gates pass.

## Live Gates

The study will not submit an entry unless all of these are true:

- `Arm Execution = Yes`
- `Send Orders To Trade Service = Yes`
- `Trade >> Trade Simulation Mode On` is **off**
- `Confirmation Text = MES_EVAL_LIVE`
- `Required Symbol Prefix = MES`
- `Allowed Trade Account` exactly matches the selected Sierra trade account
- chart is not downloading historical data
- no existing position or working orders are present
- daily loss/profit and eval trailing drawdown locks are not active

## Eval Defaults

- symbol gate: `MES`
- first leg quantity: `1`
- runner quantity: `1`
- max position quantity: `2`
- initial stop: `12` points
- first target: `7` points
- runner target: `10` points
- daily loss lock: `$240`
- daily profit lock: `$650`
- max eval trailing drawdown: `$1000`
- move stop to breakeven after target 1: `No`

The eval trailing drawdown guard tracks relative P/L from the moment its
baseline is reset. Its floor trails the high-water mark by `$1000` until the
floor reaches the starting baseline, then it stays at that baseline.

## Required Setup

1. Rebuild `AxonTradeVwapDeltaExecutionBot.cpp` in Sierra Chart.
2. Open a clean MES chart for the current contract.
3. Confirm `Trade >> Trade Simulation Mode On` is **not** checked.
4. Click `Analysis >> Studies`.
5. Add `AxonTrade MES Eval Live Bot`.
6. Open its settings and set:
   - `CSV Log Path = C:\SierraChart\Data\AxonTrade_MesEvalLiveBot.csv`
   - `Trade Mode = mes_eval_live`
   - `Arm Execution = No`
   - `Send Orders To Trade Service = No`
   - `Require Trade Simulation Mode Off = Yes`
   - `Confirmation Text = MES_EVAL_LIVE`
   - `Required Symbol Prefix = MES`
   - `Allowed Trade Account = <exact selected prop account>`
   - `Daily Loss Lock USD = 240`
   - `Daily Profit Lock USD = 650`
   - `Max Eval Trailing Drawdown USD = 1000`
   - `First Leg Quantity = 1`
   - `Runner Quantity = 1`
   - `Max Position Quantity = 2`
7. Click `OK`, then `OK` again.
8. Reopen the study settings.
9. Set `Reset Eval Drawdown Tracking = Yes`.
10. Click `OK`, then `OK` again.
11. Reopen the study settings and confirm `Reset Eval Drawdown Tracking` is
    back to `No`.

## Arming

Only after the setup above:

1. Confirm selected chart symbol starts with `MES`.
2. Confirm the selected trade account is the eval account.
3. Confirm there is no position and no working order.
4. Confirm `Trade >> Trade Simulation Mode On` is **off**.
5. Set `Send Orders To Trade Service = Yes`.
6. Set `Arm Execution = Yes`.
7. Click `OK`, then `OK` again.

To stop the bot:

1. Use `Trade >> Flatten And Cancel` if any position or order is active.
2. Set `Arm Execution = No`.
3. Set `Send Orders To Trade Service = No`.
