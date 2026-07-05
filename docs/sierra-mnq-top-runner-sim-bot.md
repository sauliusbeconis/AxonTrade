# Sierra MNQ Top Runner Sim Bot

`AxonTrade MNQ Top Runner Sim Bot` is the ACSIL simulation/replay implementation
of the MNQ top-runner lookback-breakout research lead.

Current status: Sierra replay/mechanics validation passed on `2026-07-05`. It
is simulation-only and rejects live trade-service routing.

## Frozen Strategy

- symbol prefix: `MNQ`
- chart: clean `3 Min` MNQ order-flow chart with bid/ask volume available
- setup window: `10:00:00` through `11:00:00`
- weekdays: Monday through Thursday; Friday entries skipped
- entry: `20` bar lookback breakout, `0` point buffer
- direction: long and short continuation
- VWAP rule: long closes at/above session VWAP; short closes at/below session VWAP
- delta rule: long delta `>= 600`, short delta `<= -600`
- close-location rule: directional close-location `>= 0.90`
- position: `2 MNQ` default
- exits: `160` point target, `70` point stop
- pacing: minimum `3600` seconds between submitted signals
- flatten: `15:45:00`

## Study Name

After compiling `AxonTradeVwapDeltaExecutionBot.cpp`, add:

`AxonTrade MNQ Top Runner Sim Bot`

## Replay / Simulation Inputs

| Input | Value |
| --- | --- |
| `CSV Log Path` | `C:\SierraChart\Data\AxonTrade_MnqTopRunnerSimBot.csv` |
| `Arm Execution` | `Yes` only when ready |
| `Send Orders To Trade Service` | `No` |
| `Require Trade Simulation Mode On For Sim` | `Yes` |
| `Confirmation Text` | `MNQ_TOP_RUNNER_SIM` |
| `Required Symbol Prefix` | `MNQ` |
| `Quantity` | `2` |
| `Max Position Quantity` | `2` |
| `Daily Loss Lock USD` | `0`, disabled for research replay |
| `Daily Profit Lock USD` | `0`, disabled for research replay |
| `Setup Start Time` | `10:00:00` |
| `Setup End Time` | `11:00:00` |
| `Flatten Time` | `15:45:00` |
| `Lookback Bars` | `20` |
| `Buffer Points` | `0` |
| `Delta Threshold` | `600` |
| `Directional Close Location Threshold` | `0.9` |
| `Target Points` | `160` |
| `Stop Points` | `70` |
| `Minimum Signal Spacing Seconds` | `3600` |
| `Draw Status Banner` | `Yes` |
| `Accepted Setup Alert Sound` | any enabled Sierra alert number |
| `Draw Trade Markers And Levels` | `Yes` |

Sierra trade simulation mode must be on.

## Variant Inputs

Use the defaults for the high-PF replay first. For the lower-DD validation
variant, change only:

| Input | Value |
| --- | --- |
| `Target Points` | `120` |
| `Stop Points` | `70` |

For the higher-sample variant, change:

| Input | Value |
| --- | --- |
| `Directional Close Location Threshold` | `0.8` |
| `Target Points` | `160` |
| `Stop Points` | `70` |

## Live Routing

Do not use this study for live routing.

- `Send Orders To Trade Service = Yes` is treated as a blocked state.
- The study forces `sc.SendOrdersToTradeService = false`.
- There is no live confirmation text.
- It is not approved for controlled live routing.
- Passing replay/mechanics does not change this; a separate live-capable study
  must be reviewed and built before any live promotion.
- Use `AxonTrade MNQ Top Runner Live Bot` with `MNQ_TOP_RUNNER_LIVE` for the
  separate controlled live-staging path.

## Status Banner

The chart banner is the first safety check.

- `STANDBY - NOT ARMED`: study is loaded but will not submit.
- `BLOCKED - LIVE ROUTING REJECTED`: trade-service routing was requested and is
  blocked.
- `BLOCKED - CONFIRMATION TEXT`: confirmation text is not `MNQ_TOP_RUNNER_SIM`.
- `BLOCKED - SIERRA SIM MODE IS OFF`: Sierra trade simulation mode must be on.
- `BLOCKED - SYMBOL PREFIX`: chart symbol does not start with `MNQ`.
- `WAIT - HISTORICAL DOWNLOAD`: Sierra is still downloading chart data.
- `LOCKED - DAILY RISK`: optional daily lock is active.
- `ARMED - READY`: all replay/sim gates are open.
- `ARMED - MANAGING POSITION/ORDERS`: position or working orders exist.

## Build In Sierra Chart

1. Run `bash scripts/sync_to_sierra.sh`.
2. In Sierra Chart, click `Analysis >> Build Custom Studies DLL`.
3. Select `AxonTradeVwapDeltaExecutionBot.cpp`.
4. Build the DLL.
5. Add `AxonTrade MNQ Top Runner Sim Bot` to a clean MNQ `3 Min` chart.
6. Start with replay/simulation settings above.

## Replay Checklist

1. Confirm chart symbol starts with `MNQ`.
2. Confirm chart data is complete and not downloading.
3. Confirm Sierra `Trade >> Trade Simulation Mode On` is on.
4. Set `Send Orders To Trade Service = No`.
5. Set `Confirmation Text = MNQ_TOP_RUNNER_SIM`.
6. Confirm `Quantity = 2` and `Max Position Quantity = 2`.
7. Confirm no other automated bot is running on the same sim account/instrument.
8. Set `Arm Execution = Yes` only when the status banner shows all gates ready.

## Operating Notes

- Do not arm on broken or gapped chart data.
- Do not arm while Sierra is downloading historical data.
- The CSV log records accepted setups, rejected entries, submitted entries, and
  flatten events.
- The study draws submitted entry, target, stop, and bot fill markers when
  marker drawing is enabled.
