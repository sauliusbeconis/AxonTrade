# Sierra Signal Log Outcomes

This workflow evaluates candidate rows emitted by the Sierra Chart
indicator-only overlay against later exported bars.

Manual help needed: **Yes before running this workflow**, because Sierra Chart
must export fresh bar data from the same chart and timezone as the signal log.

## Inputs

Signal log:

`C:\SierraChart\Data\AxonTrade_SignalLog.csv`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_SignalLog.csv`

Fresh Sierra bar export:

`C:\SierraChart\Data\AxonTrade_ES_OrderflowExport_NY.txt`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY.txt`

## Export Fresh Bars From Sierra

Manual help needed: **Yes**.

Use the same Sierra chart that generated the overlay signal log.

1. Click the ES footprint/execution chart window, currently chart `#2`.
2. Click `Chart >> Chart Settings`.
3. In `Chart Settings`, confirm the symbol is the same contract you replayed.
   The current signal log uses `ESU26-CME`.
4. Click `OK`.
5. Click `Edit >> Export Bar and Study Data to Text File`.
6. In the save dialog, go to Sierra's Data folder:
   `C:\SierraChart\Data`.
7. Save the file as:
   `AxonTrade_ES_OrderflowExport_NY.txt`.
8. If Sierra opens the exported text file after saving, close the text editor.

The export must come after `Global Settings >> Time Zone Settings` is set to
New York and after the replay segment has loaded the bars you want evaluated.

## Run Outcomes

Manual help needed: **No after the fresh export exists**.

From the repository:

```bash
.venv/bin/python scripts/run_signal_log_outcomes.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY.txt \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_SignalLog.csv \
  data/processed/AxonTrade_ES_overlay_signal_outcomes.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth
```

To evaluate the local replay sample instead of the active Sierra log:

```bash
.venv/bin/python scripts/run_signal_log_outcomes.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_replay_sample.csv \
  data/processed/AxonTrade_ES_overlay_signal_outcomes.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth
```

The runner first checks candidate entries against the nearest exported bar. If
it says `Export fresh bars from the same Sierra chart/timezone as the signal
log`, the export is stale, from the wrong chart, or from a different timezone.

## Output

Outcome rows are written to:

`data/processed/AxonTrade_ES_overlay_signal_outcomes.csv`

The output is a local research artifact and is ignored by Git.

## Current Replay Outcome Sample

Report:

`reports/sierra-signal-log-outcomes-replay-sample.md`

Current result from the matched New York-time export:

- candidate signals: `2`
- evaluated trades: `2`
- target hits: `0`
- stop/ambiguous losses: `1`
- other exits: `1`
- net USD: `-182.00`
