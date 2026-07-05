# Sierra MGC Normal BreakEven Bot

`AxonTrade MGC Normal BreakEven Bot` is the ACSIL implementation of the frozen
MGC lookback-breakout normal-profitability lead.

Current status: Sierra replay/mechanics validation and supervised live staging
passed on `2026-07-05`. Controlled `1 MGC` live routing is approved under the
gates below.

## Frozen Strategy

- symbol prefix: `MGC`
- chart: `1 Min` order-flow chart with bid/ask volume available
- setup window: `08:20:00` through `10:30:00`
- weekdays: Monday, Tuesday, Friday
- entry: `10` bar lookback breakout, `0` point buffer
- direction: long and short
- VWAP rule: long closes at/above session VWAP; short closes at/below session VWAP
- close-location rule: directional close-location `>= 0.45`
- delta rule: long delta `>= 0`, short delta `<= 0`, absolute delta `<= 125`
- position: `1 MGC` default
- exits: `25` point target, `15` point stop
- break-even: move stop to entry after `+20` points favorable movement
- pacing: one submitted trade per chart date
- flatten: `16:30:00`

## Study Name

After compiling `AxonTradeVwapDeltaExecutionBot.cpp`, add:

`AxonTrade MGC Normal BreakEven Bot`

## Replay / Simulation Inputs

Use this first.

| Input | Value |
| --- | --- |
| `CSV Log Path` | `C:\SierraChart\Data\AxonTrade_MgcNormalBreakEvenBot.csv` |
| `Arm Execution` | `Yes` only when ready |
| `Send Orders To Trade Service` | `No` |
| `Require Trade Simulation Mode On For Sim` | `Yes` |
| `Confirmation Text` | `MGC_NORMAL_SIM` |
| `Required Symbol Prefix` | `MGC` |
| `Allowed Trade Account` | blank is allowed for sim |
| `Quantity` | `1` |
| `Max Position Quantity` | `1` |
| `Daily Loss Lock USD` | `500` default |
| `Daily Profit Lock USD` | `0` default, disabled |
| `Lookback Bars` | `10` |
| `Buffer Points` | `0` |
| `Delta Threshold` | `0` |
| `Directional Close Location Threshold` | `0.45` |
| `Max Absolute Delta` | `125` |
| `Target Points` | `25` |
| `Stop Points` | `15` |
| `Break Even Trigger Points` | `20` |
| `Break Even Offset Ticks` | `0` |
| `Draw Status Banner` | `Yes` |
| `Accepted Setup Alert Sound` | any enabled Sierra alert number |
| `Draw Trade Markers And Levels` | `Yes` |

Sierra trade simulation mode must be on for this mode.

## Controlled Live Inputs

Use this only for the validated `1 MGC` live setup.

| Input | Value |
| --- | --- |
| `Send Orders To Trade Service` | `Yes` |
| `Require Trade Simulation Mode Off For Live` | `Yes` |
| `Confirmation Text` | `MGC_NORMAL_LIVE` |
| `Allowed Trade Account` | exact selected Sierra Trade Window account |
| `Arm Execution` | `Yes` only after every gate is correct |

Sierra trade simulation mode must be off for live mode.

## Status Banner

The chart banner is the first safety check.

- `STANDBY - NOT ARMED`: study is loaded but will not submit.
- `BLOCKED - CONFIRMATION TEXT`: confirmation text does not match the current
  route mode.
- `BLOCKED - SIERRA SIM MODE IS OFF`: sim/replay mode requires Sierra trade
  simulation mode on.
- `BLOCKED - SIERRA SIM MODE IS ON`: live mode requires Sierra trade simulation
  mode off.
- `BLOCKED - ACCOUNT MISMATCH`: live mode account whitelist does not match the
  selected trade account.
- `WAIT - HISTORICAL DOWNLOAD`: Sierra is still downloading chart data.
- `LOCKED - DAILY RISK`: daily lock is active.
- `ARMED - READY`: all gates are open.
- `ARMED - MANAGING POSITION/ORDERS`: position or working orders exist.

## Build In Sierra Chart

1. Run `bash scripts/sync_to_sierra.sh`.
2. In Sierra Chart, click `Analysis >> Build Custom Studies DLL`.
3. Select `AxonTradeVwapDeltaExecutionBot.cpp`.
4. Build the DLL.
5. Add `AxonTrade MGC Normal BreakEven Bot` to a clean MGC chart.
6. Start with replay/simulation settings above.

## Controlled Live Routing Checklist

Before arming live:

1. Confirm the chart symbol starts with `MGC`.
2. Confirm chart data is not downloading and the chart is not broken/gapped.
3. Confirm Sierra `Trade >> Trade Simulation Mode On` is off.
4. Set `Send Orders To Trade Service = Yes`.
5. Set `Confirmation Text = MGC_NORMAL_LIVE`.
6. Set `Allowed Trade Account` to the exact selected Trade Window account.
7. Confirm `Quantity = 1` and `Max Position Quantity = 1`.
8. Confirm no other automated bot is running on the same account/instrument.
9. Set `Arm Execution = Yes` only when the status banner shows all gates ready.

## Operating Notes

- Do not arm on broken or gapped chart data.
- Do not arm while Sierra is downloading historical data.
- Do not run another automated bot on the same account/instrument at the same
  time.
- The CSV log records accepted setups, rejected entries, submitted entries, and
  flatten events.
- The study draws submitted entry, target, stop, and bot fill markers when
  marker drawing is enabled.
