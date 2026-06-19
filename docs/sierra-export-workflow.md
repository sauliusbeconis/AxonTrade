# Sierra Export Workflow

This workflow connects Sierra Chart replay/chart data to the AxonTrade
price-only baseline.

Manual help is required for the Sierra Chart export step because Sierra must
write the chart and study data from inside its own UI.

## Required Chart

Use the ES/MES chart that has:

- the correct futures symbol;
- RTH session settings;
- `Volume Weighted Average Price`;
- enough loaded bars to include `09:30:00` through `09:59:59` for each
  exported RTH date.

The Python baseline does not require footprint, DOM, heatmap, or a Sierra
opening-range study.

## Required Normalized Columns

AxonTrade needs these normalized fields:

- `timestamp`
- `symbol`
- `chart_number`
- `bar_index`
- `open`
- `high`
- `low`
- `close`
- `vwap`
- `opening_range_high`, computed in Python from exported bars
- `opening_range_low`, computed in Python from exported bars
- `session_phase`

Sierra's exported headers may be different. The adapter maps common headers from
`config/research/sierra_bar_export.yaml`.

## Export From Sierra Chart

Manual help is required.

1. In Sierra Chart, click the chart that has VWAP.
2. Click `Analysis >> Studies`.
3. Confirm `Volume Weighted Average Price` is present.
4. An opening-range high/low study is not required for this baseline.
5. Click `OK`.
6. Click `Edit >> Export Bar and Study Data to Text File`.
7. In the save dialog, use this filename:
   `AxonTrade_ES_BarStudyExport.txt`.
8. Save it in Sierra Chart's Data folder:
   `C:\SierraChart\Data`.
9. If Sierra opens the exported text file, close the text editor after confirming
   the file has a header row and bar rows.

On this workstation, the Linux path for that folder is:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data`

## Opening Range Handling

Manual help is not needed for opening-range calculation after the export exists.

AxonTrade computes the opening range from exported bar highs/lows between
`09:30:00` and `09:59:59`. This avoids trusting Sierra study columns that may
write completed historical study values onto earlier bars.

If the script says no bars were found inside the opening range, manual help is
required to re-export the correct chart window:

1. In Sierra Chart, click the ES/MES chart used for export.
2. Click `Chart >> Chart Settings`.
3. In `Chart Settings`, open the `Session Times` page or tab.
4. Confirm the RTH session starts at `09:30:00`.
5. Confirm the chart has bars from `09:30:00` through at least `10:00:00`.
6. Click `OK`.
7. Click `Edit >> Export Bar and Study Data to Text File`.
8. Save again as `C:\SierraChart\Data\AxonTrade_ES_BarStudyExport.txt`.

## Run The Baseline

Manual help is not needed after the export file exists.

From the repo:

```bash
.venv/bin/python scripts/run_price_only_baseline.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_BarStudyExport.txt \
  data/processed/AxonTrade_ES_price_only_signals.csv \
  --symbol ESU26-CME \
  --chart-number 1 \
  --session-phase rth
```

Replace `ESU26-CME` with the exact current symbol shown in your Sierra chart
title if it differs.

The default opening-range window is `09:30:00` through `09:59:59`. To override
it:

```bash
.venv/bin/python scripts/run_price_only_baseline.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_BarStudyExport.txt \
  data/processed/AxonTrade_ES_price_only_signals.csv \
  --symbol ESU26-CME \
  --chart-number 1 \
  --session-phase rth \
  --opening-range-start 09:30:00 \
  --opening-range-end 09:59:59
```

Only use `--use-exported-opening-range` when intentionally testing Sierra study
columns. The normal research path computes opening range in Python.

Expected output:

- a CSV written to `data/processed/AxonTrade_ES_price_only_signals.csv`;
- one row per input bar;
- `candidate_signal` rows when the VWAP/opening-range reclaim setup appears;
- `rejected_signal` rows for no setup, first-bar context, or outside-session
  rows.

## Troubleshooting

If the script says a price or VWAP column is missing:

1. Open the exported file.
2. Check the exact header name Sierra wrote for VWAP.
3. Either rename that header in the exported file, or update
   `config/research/sierra_bar_export.yaml`.

If all rows are rejected as `no_setup`, that is acceptable for a sample. It means
the export path works but no baseline signal occurred in that data window.

If rows are rejected as `insufficient_context`, export more bars or confirm the
opening-range study is producing values.

## Official Sierra Reference

Sierra Chart documents the export path as:

`Edit >> Export Bar and Study Data to Text File`

Reference:

https://www.sierrachart.com/index.php?page=doc/EditMenu.html#ExportBarAndStudyDataToTextFile
