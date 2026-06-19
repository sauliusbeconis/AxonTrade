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
- opening range high/low study or lines that export as study subgraphs;
- enough loaded days for the replay or research sample.

The Python baseline does not require footprint, DOM, or heatmap data.

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
- `opening_range_high`
- `opening_range_low`
- `session_phase`

Sierra's exported headers may be different. The adapter maps common headers from
`config/research/sierra_bar_export.yaml`.

## Export From Sierra Chart

Manual help is required.

1. In Sierra Chart, click the chart that has VWAP and opening-range levels.
2. Click `Analysis >> Studies`.
3. Confirm `Volume Weighted Average Price` is present.
4. Confirm the opening-range high/low study is present.
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

## If Opening Range Is Missing

Manual help is required.

Add an opening-range high/low study before exporting:

1. Click the ES/MES chart.
2. Click `Analysis >> Studies`.
3. In `Studies Available`, select `High/Low for Time Period`.
4. Click `Add >>`.
5. In `Studies to Graph`, select the newly added `High/Low for Time Period`.
6. Click `Settings`.
7. In `Settings and Inputs`, set the start time to `09:30:00`.
8. Set the end time to `09:59:59` for the first 30-minute opening range.
9. Confirm the high and low subgraphs are visible.
10. Click `OK`.
11. Click `OK`.
12. Click `File >> Save`.

Then run the export again with:

`Edit >> Export Bar and Study Data to Text File`

If Sierra exports the opening-range columns under unexpected names, keep the
file and send me the header row. I will update
`config/research/sierra_bar_export.yaml` to match your Sierra output.

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

Expected output:

- a CSV written to `data/processed/AxonTrade_ES_price_only_signals.csv`;
- one row per input bar;
- `candidate_signal` rows when the VWAP/opening-range reclaim setup appears;
- `rejected_signal` rows for no setup, first-bar context, or outside-session
  rows.

## Troubleshooting

If the script says a column is missing:

1. Open the exported file.
2. Check the exact header name Sierra wrote for VWAP or opening-range levels.
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
