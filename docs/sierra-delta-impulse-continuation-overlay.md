# Sierra Delta Impulse Continuation Overlay

`AxonTradeDeltaImpulseContinuationOverlay.cpp` is an indicator-only ACSIL study
for the current fixed-exit lead:

`delta_impulse_continue_10bar_2.5pt_50d` with fixed `5 / 5 / 15 / breakeven`.

Manual help needed: **Yes, to compile and load the Sierra Chart study.**
Manual help needed after it is loaded: **No**, unless Sierra Chart reports a
build error or the chart is missing bid/ask volume data.

The study does not place, modify, cancel, flatten, or route orders.

## What It Logs

Default output file:

`C:\SierraChart\Data\AxonTrade_DeltaImpulseSignalLog.csv`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`

Rows use the AxonTrade signal-log fields:

- `candidate_signal` when the fixed delta impulse continuation rule passes.
- `rejected_signal` when the bar is outside the setup window, lacks lookback
  context, fails thresholds, violates spacing, or exceeds the daily signal cap.

## Rule Defaults

These defaults match the fixed-exit research lead:

- strategy ID: `delta_impulse_continue_10bar_2.5pt_50d`
- setup window: `09:45:00` through `15:45:00`
- lookback bars: `10` eligible setup-window bars
- minimum price move: `2.5` points over the lookback
- minimum delta sum: `50`
- minimum spacing: `900` seconds
- max signals per day: `6`
- initial stop: `5` points
- first target: `5` points
- runner target: `15` points
- runner stop mode: breakeven after first target, recorded in `notes`

The CSV `target_price` field stores the runner target. The first target and
runner stop mode are recorded in the `notes` field and drawn on the chart.

## Sync Source Into Sierra

Manual help needed: **No** for this command.

From the repository:

```bash
bash scripts/sync_to_sierra.sh
```

This copies the source to:

`C:\SierraChart\ACS_Source\AxonTradeDeltaImpulseContinuationOverlay.cpp`

## Build In Sierra Chart

Manual help needed: **Yes**.

Use the exact Sierra Chart path:

1. Click `Analysis >> Build Custom Studies DLL`.
2. In `Build Advanced Custom Studies DLL`, click `File >> Select Files`.
3. Select `AxonTradeDeltaImpulseContinuationOverlay.cpp`.
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
4. Expand `AxonTrade Delta Impulse Continuation Overlay`.
5. Select `AxonTrade Delta Impulse Continuation Overlay`.
6. Click `Add`.
7. In `Studies to Graph`, select `AxonTrade Delta Impulse Continuation Overlay`.
8. Click `Settings`.
9. In `Settings and Inputs`, confirm:
   - `CSV Log Path = C:\SierraChart\Data\AxonTrade_DeltaImpulseSignalLog.csv`
   - `Trade Mode = replay` for replay, or `sim` for simulation
   - `Log Rejections = Yes`
   - `Process Full Recalculation = No`
   - `Setup Start Time = 09:45:00`
   - `Setup End Time = 15:45:00`
   - `Lookback Bars = 10`
   - `Minimum Price Move Points = 2.5`
   - `Minimum Delta Sum = 50`
   - `Minimum Signal Spacing Seconds = 900`
   - `Max Signals Per Day = 6`
   - `Initial Stop Points = 5`
   - `First Target Points = 5`
   - `Runner Target Points = 15`
10. Click `OK`.
11. Click `OK` again to close Chart Studies.

Expected chart result:

- long candidates draw a blue up arrow, label, stop segment, first target
  segment, and runner target segment;
- short candidates draw a red down arrow, label, stop segment, first target
  segment, and runner target segment;
- candidate and rejection rows append to the CSV log.

## Replay Use

Manual help needed: **No** after the study is built and loaded.

1. Click `Trade >> Trade Simulation Mode On` and confirm it is checked.
2. Click `Chart >> Replay Chart`.
3. Start replay before `09:45:00` New York time if you want the in-study spacing
   and daily cap to match research behavior from the start of the setup window.
4. Let bars close during the setup window.
5. Check the log at:
   `C:\SierraChart\Data\AxonTrade_DeltaImpulseSignalLog.csv`

If you want to backfill all loaded historical bars:

1. Click `Analysis >> Studies`.
2. Select `AxonTrade Delta Impulse Continuation Overlay`.
3. Click `Settings`.
4. Set `Process Full Recalculation = Yes`.
5. Click `OK`.
6. Click `Chart >> Recalculate`.
7. After the backfill, set `Process Full Recalculation = No`.

Leaving `Process Full Recalculation = Yes` can write many rejection rows during
recalculations.

## Report The Log

Manual help needed: **No** after the CSV exists.

From the repository:

```bash
.venv/bin/python scripts/report_signal_log.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv \
  reports/sierra-delta-impulse-signal-log-live.md
```

The reporting workflow is documented in
[sierra-signal-log-report.md](sierra-signal-log-report.md).
