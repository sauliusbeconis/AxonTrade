# Sierra Volume-At-Price Logger

This is the exact Sierra Chart workflow for building and running the
indicator-only AxonTrade volume-at-price CSV logger.

Manual help needed: **Yes**. Sierra Chart must compile and run the ACSIL study
from inside its own UI.

## Sync Source Into Sierra

Manual help needed: **No** for this command.

From the repository:

```bash
WINEPREFIX=/home/saulius/WinePrefixes/SierraChart \
  bash scripts/sync_to_sierra.sh
```

This copies:

`src/acsil/AxonTradeVolumeAtPriceLogger.cpp`

to:

`C:\SierraChart\ACS_Source\AxonTradeVolumeAtPriceLogger.cpp`

## Build In Sierra Chart

Manual help needed: **Yes**.

In Sierra Chart:

1. Click `Analysis >> Build Custom Studies DLL`.
2. In `Files to Build`, select `AxonTradeVolumeAtPriceLogger.cpp`.
3. Confirm the build mode is `Release`.
4. Press `Build`.
5. Wait for the build log to end with no compiler errors.
6. Press `Close`.

Expected DLL output:

`C:\SierraChart\Data\AxonTradeVolumeAtPriceLogger_64.dll`

## Add Study To Chart

Manual help needed: **Yes**.

Use the chart that has the ES/MES order-flow bars loaded.

1. Click the ES chart window.
2. Click `Analysis >> Studies`.
3. Press `Add Custom Study`.
4. In the custom study list, find `AxonTrade Volume At Price CSV Logger`.
5. Select it and press `Add`.
6. In the study settings, open the `Settings and Inputs` tab.
7. Set `Output File Path` to:
   `C:\SierraChart\Data\AxonTrade_ES_VolumeAtPriceExport.txt`
8. Set `Session Phase` to:
   `rth`
9. Set `Max Bars To Export (0 = All Loaded Bars)` to:
   `0`
10. Set `Include Header` to:
    `Yes`
11. Set `Log Summary` to:
    `Yes`
12. Leave `Export Now` as:
    `No`
13. Press `OK`.
14. Press `OK` again to close the Chart Studies window.

## Run One Export

Manual help needed: **Yes**.

Use the same ES chart window that produced:

`C:\SierraChart\Data\AxonTrade_ES_OrderflowExport_NY_Large.txt`

The current large-sample signal/outcome research requires the volume-at-price
file to come from that same chart, timezone, replay segment, and contract.

1. Click the ES chart window.
2. Click `Analysis >> Studies`.
3. Select `AxonTrade Volume At Price CSV Logger`.
4. Press `Settings`.
5. Open the `Settings and Inputs` tab.
6. Set `Export Now` to:
   `Yes`
7. Press `Apply`.
8. Confirm `Export Now` resets to:
   `No`
9. Press `OK`.
10. Press `OK` again to close the Chart Studies window.
11. Click `Window >> Message Log`.
12. Confirm there is a line like:
    `AxonTrade VAP export complete: rows=...`

Expected output file:

`C:\SierraChart\Data\AxonTrade_ES_VolumeAtPriceExport.txt`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_VolumeAtPriceExport.txt`

## Verify From Repo

Manual help needed: **No** after Sierra writes the file.

From the repository:

```bash
.venv/bin/python scripts/check_footprint_export.py --fail-on-missing
```

Expected successful output starts with:

```text
status=PASS
manual_sierra_help_needed=no
```

If it fails, copy the exact `status=FAIL` output and the relevant line from
`Window >> Message Log`.

## Validate Against Signal Research

Manual help needed: **No** after Sierra writes the refreshed VAP file.

From the repository:

```bash
.venv/bin/python scripts/run_vap_absorption_diagnostics.py \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  data/processed/AxonTrade_ES_overlay_signal_outcomes_large_sample.csv \
  reports/sierra-signal-log-vap-absorption-diagnostics-large-sample.csv \
  --vap-input /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_VolumeAtPriceExport.txt \
  --symbol ESU26-CME \
  --minimum-zone-volume 0
```

Expected successful output includes `vap_covered_trades=` greater than `0`.
If the command prints `status=FAIL vap_coverage=0`, repeat the export from the
same chart that produced `AxonTrade_ES_OrderflowExport_NY_Large.txt`.
