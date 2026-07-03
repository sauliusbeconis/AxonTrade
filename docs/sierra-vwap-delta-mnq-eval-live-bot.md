# Sierra VWAP Delta MNQ Eval Live Bot

`AxonTrade MNQ Eval Live Bot` is the guarded live-capable prop-eval study built
from `AxonTradeVwapDeltaExecutionBot.cpp`.

Manual help needed: **Yes.** This study can route live trade-service orders when
armed and all live gates pass.

## Live Gates

The study will not submit an entry unless all of these are true:

- `Arm Execution = Yes`
- `Send Orders To Trade Service = Yes`
- `Trade >> Trade Simulation Mode On` is **off**
- `Confirmation Text = MNQ_EVAL_LIVE`
- `Required Symbol Prefix = MNQ`
- `Allowed Trade Account` exactly matches the selected Sierra trade account
- chart is not downloading historical data
- no existing position or working orders are present
- daily loss/profit and eval trailing drawdown locks are not active

Expected ready banner:

`AXON MNQ LIVE: ARMED - READY FOR LIVE ORDERS`

## Research Defaults

- symbol gate: `MNQ`
- strategy: `80pt_400d_cl0.4`, no Fridays, no `11:00` or `15:00` exchange-time entries
- first leg quantity: `1`
- runner quantity: `1`
- max position quantity: `2`
- initial stop: `140` points
- first target: `25` points
- runner target: `40` points
- daily loss lock: `$650`
- daily profit lock: `$650`
- max eval trailing drawdown: `$1000`
- move stop to breakeven after target 1: `No`

## Required Setup

1. Rebuild `AxonTradeVwapDeltaExecutionBot.cpp` in Sierra Chart.
2. Open a clean MNQ chart for the current contract.
3. Confirm `Trade >> Trade Simulation Mode On` is **not** checked.
4. Add `AxonTrade MNQ Eval Live Bot`.
5. Set:
   - `Confirmation Text = MNQ_EVAL_LIVE`
   - `Allowed Trade Account = <exact selected prop account>`
   - `Send Orders To Trade Service = No`
   - `Arm Execution = No`
   - `Draw Status Banner = Yes`
6. Reset eval drawdown tracking once after loading the study.
7. Before arming, confirm the banner shows every gate as passing except arm/route.

## Arming

Only after setup and replay/mechanics verification:

1. Confirm selected chart symbol starts with `MNQ`.
2. Confirm selected trade account is the eval account.
3. Confirm no position and no working order exists.
4. Confirm Sierra trade simulation mode is **off**.
5. Set `Send Orders To Trade Service = Yes`.
6. Set `Arm Execution = Yes`.

To stop the bot, flatten/cancel if needed, then set `Arm Execution = No` and
`Send Orders To Trade Service = No`.
