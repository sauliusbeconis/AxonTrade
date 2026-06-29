# Sierra Delta Impulse Continuation Overlay

`AxonTradeDeltaImpulseContinuationOverlay.cpp` is an indicator-only ACSIL study
for the current 3-minute delta impulse continuation candidate:

`delta_impulse_continue_10bar_2.5pt_50d` with fixed `5 / 10 / 8 / initial`.

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
  Rejection logging is disabled by default because it creates one row for almost
  every closed bar.

## Rule Defaults

These defaults match the current 3-minute replay candidate:

- strategy ID: `delta_impulse_continue_10bar_2.5pt_50d`
- setup window: `09:45:00` through `15:45:00`
- lookback bars: `10` eligible setup-window bars
- minimum price move: `2.5` points over the lookback
- minimum delta sum: `50`
- minimum spacing: `900` seconds
- max signals per day: `6`
- initial stop: `10` points
- first target: `5` points
- runner target: `8` points
- runner stop mode: `initial`, recorded in `notes`

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
   - `Log Rejections = No`
   - `Process Full Recalculation = No`
   - `Reset CSV On Full Recalculation = Yes`
   - `Setup Start Time = 09:45:00`
   - `Setup End Time = 15:45:00`
   - `Lookback Bars = 10`
   - `Minimum Price Move Points = 2.5`
   - `Minimum Delta Sum = 50`
   - `Minimum Signal Spacing Seconds = 900`
   - `Max Signals Per Day = 6`
   - `Initial Stop Points = 10`
   - `First Target Points = 5`
   - `Runner Target Points = 8`
   - `Runner Stop Mode = initial`
10. Click `OK`.
11. Click `OK` again to close Chart Studies.

Expected chart result:

- long candidates draw a blue up arrow, label, stop segment, first target
  segment, and runner target segment;
- short candidates draw a red down arrow, label, stop segment, first target
  segment, and runner target segment;
- candidate rows append to the CSV log. Rejection rows append only when
  `Log Rejections = Yes`.

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
4. Confirm `Log Rejections = No`.
5. Confirm `Reset CSV On Full Recalculation = Yes`.
6. Set `Process Full Recalculation = Yes`.
7. Click `OK`.
8. Click `Chart >> Recalculate`.
9. After the backfill, click `Analysis >> Studies`.
10. Select `AxonTrade Delta Impulse Continuation Overlay`.
11. Click `Settings`.
12. Set `Process Full Recalculation = No`.
13. Click `OK`.

Leaving `Process Full Recalculation = Yes` can repeat backfills during
recalculations. Turning `Log Rejections = Yes` during a full backfill can write
tens of thousands of diagnostic rows and is only useful for short debugging
runs.

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

## Validate The Overlay Log

Manual help needed: **No** after the matching bar export and signal log exist.

Run this before trusting a new Sierra replay export. It reproduces the overlay
candidate rule from exported 3-minute OHLC plus bid/ask volume and compares the
result to `AxonTrade_DeltaImpulseSignalLog.csv`.

```bash
.venv/bin/python scripts/check_delta_impulse_overlay_validation.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Large.txt \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv \
  --fail-on-mismatch
```

Expected current result:

`overlay_validation=PASS; expected=163; actual=163; matched=163`

The report is written to:

`reports/sierra-delta-impulse-overlay-validation.md`

## Evaluate Scaled Outcomes

Manual help needed: **No** after the matching bar export exists.

For the current fixed row, use the one-command pipeline. It regenerates:

- `reports/sierra-delta-impulse-signal-log-live.md`
- `data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv`
- `reports/sierra-delta-impulse-3min-large-scaled-exit-sweep.csv`
- `reports/sierra-delta-impulse-3min-large-robustness.md`
- `reports/sierra-delta-impulse-3min-fixed-row-acceptance.md`

```bash
.venv/bin/python scripts/run_delta_impulse_fixed_row_pipeline.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Large.txt \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv
```

The current expanded sample is expected to print:

`validated 163 entries; outcomes=163 net_usd=-15716.00; sweep_rows=924; acceptance=FAIL`

That is a research rejection, not a script error.

## Annotate News Blackouts

Manual help needed: **No** for the current June 2026 replay sample.

The tracked June 2026 calendar is:

`config/research/us_scheduled_news_events_2026_06.csv`

Annotate the current fixed-row outcomes with:

```bash
.venv/bin/python scripts/run_signal_news_exclusion.py \
  data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv \
  config/research/us_scheduled_news_events_2026_06.csv \
  reports/sierra-delta-impulse-fixed-row-news-annotated-outcomes.csv \
  --timestamp-field entry_time \
  --default-blackout-before-minutes 10 \
  --default-blackout-after-minutes 15
```

Current result: `163` rows annotated, `1` row inside a blackout window. The
diagnostic summary is:

`reports/sierra-delta-impulse-fixed-row-news-exclusion.md`

## Run Scaled Context Filters

Manual help needed: **No** after the matching bar export, fixed-row outcomes,
and signal log exist.

Generate pre-entry normalized context diagnostics:

```bash
.venv/bin/python scripts/run_scaled_outcome_context_diagnostics.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Large.txt \
  data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv \
  reports/sierra-delta-impulse-fixed-row-context-diagnostics.csv \
  --lookback-bars 20
```

Run the rolling context-filter walk-forward:

```bash
.venv/bin/python scripts/run_scaled_context_filter_walk_forward_sweep.py \
  reports/sierra-delta-impulse-fixed-row-context-diagnostics.csv \
  reports/sierra-delta-impulse-fixed-row-context-filter-walk-forward.csv \
  --train-date-count 20 \
  --holdout-date-count 5 \
  --minimum-train-trades 20 \
  --window-step-date-count 5
```

Current result: `4` holdout windows, `20` selected holdout trades, `-4640` net
USD. The unfiltered rows across the same holdout windows were `-7927` net USD.
The selector reduced exposure and lost less, but it is still a losing
diagnostic, not a validation improvement.

Summary:

`reports/sierra-delta-impulse-fixed-row-context-filter.md`

## Run Direction Variant Diagnostics

Manual help needed: **No** after the matching bar export and signal log exist.

This compares the logged continuation direction with a simple inverted fade
variant. It is a diagnostic only.

```bash
.venv/bin/python scripts/run_delta_impulse_direction_variant_diagnostics.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Large.txt \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv
```

Current result:

- logged-direction walk-forward: `72` selected holdout trades, `-11254` net USD
- inverted-direction walk-forward: `100` selected holdout trades, `-4512.5` net USD

The inverted/fade direction has positive in-sample rows but still fails
walk-forward. Summary:

`reports/sierra-delta-impulse-direction-variant-diagnostics.md`

Use this to evaluate the original `5 / 5 / 15 / breakeven` exit when the CSV
came from the same Sierra chart that produced the export:

```bash
.venv/bin/python scripts/run_signal_log_scaled_scalp_outcomes.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min.txt \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv \
  data/processed/AxonTrade_ES_delta_impulse_3min_scaled_outcomes.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --first-target-points 5 \
  --stop-points 5 \
  --runner-target-points 15 \
  --runner-stop-mode breakeven \
  --entry-match-mode auto
```

For the expanded 3-minute replay sample, this is the rejected fixed variant
currently documented by the overlay and pipeline:

```bash
.venv/bin/python scripts/run_signal_log_scaled_scalp_outcomes.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min.txt \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv \
  data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --first-target-points 5 \
  --stop-points 10 \
  --runner-target-points 8 \
  --runner-stop-mode initial \
  --entry-match-mode auto
```

The one-command pipeline above should normally be preferred because it also
updates the robustness and acceptance reports. Do not promote this variant
without a changed hypothesis and fresh walk-forward validation.

To reproduce that rejected fixed variant in Sierra:

Manual help needed: **Yes**.

1. Click the footprint chart `ESU26-CME[M] 3 Min #2`.
2. Click `Analysis >> Studies`.
3. Select `AxonTrade Delta Impulse Continuation Overlay`.
4. Click `Settings`.
5. Set:
   - `Initial Stop Points = 10`
   - `First Target Points = 5`
   - `Runner Target Points = 8`
   - `Runner Stop Mode = initial`
6. Click `OK`.
7. Click `OK`.
8. Click `File >> Save`.
