# Sierra Liquidity Sweep Signal Overlay

`AxonTradeLiquiditySweepSignalOverlay.cpp` is an indicator-only ACSIL study that
draws candidate liquidity-sweep absorption reversals and writes rows to
`config/research/signal_log_schema.yaml`.

Manual help needed: **Yes, to compile and load the Sierra Chart study.**
Manual help needed after it is loaded: **No**, unless Sierra Chart reports a
build error or the chart has missing bid/ask volume data.

The study does not place, modify, cancel, flatten, or route orders.

## What It Logs

Default output file:

`C:\SierraChart\Data\AxonTrade_SignalLog.csv`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_SignalLog.csv`

Rows use the AxonTrade signal-log fields:

- `candidate_signal` when the sweep, absorption, reversal, stop, and target
  checks pass.
- `rejected_signal` when the bar is outside the setup, lacks context, has no
  setup, lacks absorption, duplicates an existing same-side daily signal, or
  violates risk limits.

## Rule Defaults

The defaults mirror `config/research/liquidity_sweep_absorption_reversal.yaml`:

- opening range: `09:30:00` through `09:59:59`
- setup window: `10:30:00` through `15:15:00`
- minimum opening-range width: `1.0` point
- minimum sweep distance: `1.0` point
- maximum reversal window: `5` bars
- close back inside: `0.25` point
- stop buffer: `0.25` point
- maximum risk: `20.0` points
- minimum aggression ratio: `1.25`
- short confirmation close location: `0.45` or lower
- long confirmation close location: `0.55` or higher
- one signal per side per day: `Yes`

## Sync Source Into Sierra

Manual help needed: **No** for this command.

From the repository:

```bash
bash scripts/sync_to_sierra.sh
```

This copies the source to:

`C:\SierraChart\ACS_Source\AxonTradeLiquiditySweepSignalOverlay.cpp`

## Build In Sierra Chart

Manual help needed: **Yes**.

Use the exact Sierra Chart path:

1. Click `Analysis >> Build Custom Studies DLL`.
2. In `Build Advanced Custom Studies DLL`, click `File >> Select Files`.
3. Select `AxonTradeLiquiditySweepSignalOverlay.cpp`.
4. Click `Open`.
5. Click `Build >> Remote Build`.
6. Wait for the build output to say the remote build succeeded.
7. If Sierra asks to allow loading DLLs, click `Build >> Allow Load DLLs`.

If the build output says:

`Can't recognize 'cl ...' as an internal or external command`

you used the local Visual C++ path. In the same build window, click
`Build >> Remote Build`.

## Load On The Execution Chart

Manual help needed: **Yes**.

Use the ES footprint/execution chart, not the TPO context chart.

1. Click the ES footprint/execution chart window.
2. Click `Analysis >> Studies`.
3. Click `Add Custom Study`.
4. Expand `AxonTrade Liquidity Sweep Signal Overlay`.
5. Select `AxonTrade Liquidity Sweep Signal Overlay`.
6. Click `Add`.
7. In `Studies to Graph`, select `AxonTrade Liquidity Sweep Signal Overlay`.
8. Click `Settings`.
9. In `Settings and Inputs`, confirm:
   - `CSV Log Path = C:\SierraChart\Data\AxonTrade_SignalLog.csv`
   - `Trade Mode = replay` for replay, or `sim` for simulation
   - `Log Rejections = Yes`
   - `Process Full Recalculation = No`
   - `One Signal Per Side Per Day = Yes`
   - `Opening Range Start Time = 09:30:00`
   - `Opening Range End Time = 09:59:59`
   - `Setup Start Time = 10:30:00`
   - `Setup End Time = 15:15:00`
   - `Minimum Aggression Ratio = 1.25`
10. Click `OK`.
11. Click `OK` again to close Chart Studies.

Expected chart result:

- long candidates draw a blue up arrow, label, stop segment, and target segment;
- short candidates draw a red down arrow, label, stop segment, and target
  segment;
- candidate and rejection rows append to the CSV log.

## Replay Use

Manual help needed: **No** after the study is built and loaded.

1. Click `Trade >> Trade Simulation Mode On` and confirm it is checked.
2. Click `Chart >> Replay Chart`.
3. Start replay after the opening range is complete, or replay through the
   opening range from `09:30:00`.
4. Let bars close during the setup window.
5. Check the log at:
   `C:\SierraChart\Data\AxonTrade_SignalLog.csv`

If you want to backfill all loaded historical bars:

1. Click `Analysis >> Studies`.
2. Select `AxonTrade Liquidity Sweep Signal Overlay`.
3. Click `Settings`.
4. Set `Process Full Recalculation = Yes`.
5. Click `OK`.
6. Click `Chart >> Recalculate`.
7. After the backfill, set `Process Full Recalculation = No`.

Leaving `Process Full Recalculation = Yes` can write many rejection rows during
recalculations.
