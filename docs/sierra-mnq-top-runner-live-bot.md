# Sierra MNQ Top Runner Live Bot

`AxonTrade MNQ Top Runner Live Bot` is the guarded live-capable implementation
of the MNQ top-runner lookback-breakout family.

Current status: live-capable build exists and is aligned to the filtered frozen
research rule. Fresh replay/mechanics passed on the aligned build. It is not
approved for unattended live use until controlled live staging passes.

## Frozen Strategy

- symbol prefix: `MNQ`
- chart: clean `3 Min` MNQ order-flow chart with bid/ask volume available
- raw setup window: `10:00:00` through `12:30:00`
- final tradable filter window: `10:00:00` through `11:00:00`
- weekdays: Monday through Thursday; Friday entries skipped
- entry: `20` bar lookback breakout, `0` point buffer
- direction: long and short continuation
- VWAP rule: long closes at/above session VWAP; short closes at/below session VWAP
- delta rule: long delta `>= 600`, short delta `<= -600`
- raw close-location rule: directional close-location `>= 0.65`
- final close-location rule: directional close-location `>= 0.90`
- position: `2 MNQ` default
- exits: `120` point target, `70` point stop
- pacing: minimum `3600` seconds between raw setups, even when a raw setup is
  later rejected by the final filter
- flatten: `15:45:00`

This uses the lower-DD validated variant by default. The higher-PF `160 / 70`
variant remains available in the sim/replay bot, but is not the first live
staging default.

## Study Name

After compiling `AxonTradeVwapDeltaExecutionBot.cpp`, add:

`AxonTrade MNQ Top Runner Live Bot`

## Controlled Live Inputs

| Input | Value |
| --- | --- |
| `CSV Log Path` | `C:\SierraChart\Data\AxonTrade_MnqTopRunnerLiveBot.csv` |
| `Arm Execution` | `Yes` only when ready |
| `Send Orders To Trade Service` | `Yes` |
| `Require Trade Simulation Mode Off For Live` | `Yes` |
| `Confirmation Text` | `MNQ_TOP_RUNNER_LIVE` |
| `Required Symbol Prefix` | `MNQ` |
| `Allowed Trade Account` | exact selected Sierra Trade Window account |
| `Quantity` | `2` |
| `Max Position Quantity` | `2` |
| `Daily Loss Lock USD` | `300` |
| `Daily Profit Lock USD` | `0`, disabled |
| `Setup Start Time` | `10:00:00`, final filter start and raw setup start |
| `Setup End Time` | `11:00:00`, final filter end |
| `Flatten Time` | `15:45:00` |
| `Lookback Bars` | `20` |
| `Buffer Points` | `0` |
| `Delta Threshold` | `600` |
| `Directional Close Location Threshold` | `0.9`, final filter threshold |
| `Target Points` | `120` |
| `Stop Points` | `70` |
| `Minimum Signal Spacing Seconds` | `3600`, raw setup spacing |
| `Draw Status Banner` | `Yes` |
| `Accepted Setup Alert Sound` | any enabled Sierra alert number |
| `Draw Trade Markers And Levels` | `Yes` |

Sierra trade simulation mode must be off for this study to submit.

The broader raw setup filter is fixed in code at `10:00-12:30` with raw
directional close-location `0.65`; the exposed `Setup End Time` and
`Directional Close Location Threshold` are the final tradable filter.

## Risk Notes

- `2 MNQ` with a `70` point stop is about `$280` gross risk before commissions
  and slippage.
- The default `$300` daily loss lock is intended to stop trading after roughly
  one full stop.
- Daily profit lock is disabled because this is normal-profitability staging,
  not eval consistency-rule optimization.
- Do not run this on the same account/instrument as another MNQ bot.

## Status Banner

The chart banner is the first safety check.

- `STANDBY - NOT ARMED`: study is loaded but will not submit.
- `BLOCKED - ROUTING OFF`: `Send Orders To Trade Service` is not enabled.
- `BLOCKED - CONFIRMATION TEXT`: confirmation text is not `MNQ_TOP_RUNNER_LIVE`.
- `BLOCKED - SIERRA SIM MODE IS ON`: Sierra trade simulation mode must be off.
- `BLOCKED - ALLOWED ACCOUNT BLANK`: account whitelist is empty.
- `BLOCKED - ACCOUNT MISMATCH`: selected trade account does not match whitelist.
- `BLOCKED - SYMBOL PREFIX`: chart symbol does not start with `MNQ`.
- `WAIT - HISTORICAL DOWNLOAD`: Sierra is still downloading chart data.
- `LOCKED - DAILY RISK`: daily lock is active.
- `ARMED - READY`: all live gates are open.
- `ARMED - MANAGING POSITION/ORDERS`: position or working orders exist.

## Build In Sierra Chart

1. Run `bash scripts/sync_to_sierra.sh`.
2. In Sierra Chart, click `Analysis >> Build Custom Studies DLL`.
3. Select `AxonTradeVwapDeltaExecutionBot.cpp`.
4. Build the DLL.
5. Add `AxonTrade MNQ Top Runner Live Bot` to a clean MNQ `3 Min` chart.
6. Keep `Arm Execution = No` until the live checklist is complete.

## Controlled Live Checklist

Before arming:

1. Confirm chart symbol starts with `MNQ`.
2. Confirm chart data is complete and not downloading.
3. Confirm Sierra `Trade >> Trade Simulation Mode On` is off.
4. Confirm no position and no working orders exist.
5. Set `Send Orders To Trade Service = Yes`.
6. Set `Confirmation Text = MNQ_TOP_RUNNER_LIVE`.
7. Set `Allowed Trade Account` to the exact selected Trade Window account.
8. Confirm `Quantity = 2`, `Max Position Quantity = 2`, and `Daily Loss Lock USD = 300`.
9. Confirm `Setup End Time = 11:00:00`, `Directional Close Location Threshold = 0.9`,
   and `Minimum Signal Spacing Seconds = 3600`.
10. Confirm no other automated MNQ bot is running on the same account.
11. Set `Arm Execution = Yes` only when the status banner shows all gates ready.

To stop the bot, flatten/cancel if needed, then set `Arm Execution = No`.

## Operating Notes

- Do not arm on broken or gapped chart data.
- Do not arm while Sierra is downloading historical data.
- The CSV log records accepted setups, rejected entries, submitted entries, and
  flatten events.
- The study draws submitted entry, target, stop, and bot fill markers when
  marker drawing is enabled.
