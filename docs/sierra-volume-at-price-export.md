# Sierra Volume-At-Price Export Contract

This contract defines the footprint export needed for level-specific liquidity
sweep absorption research.

Manual help needed: **Yes, later, to produce the export from Sierra Chart.**
Manual help is **not** needed to run the repo-side checker after the file exists.

## Why This Exists

The current absorption layer only sees total bid and ask volume for each bar.
That is too coarse for a trap/fade setup because the important question is
whether aggressive volume was absorbed at the swept price levels.

Sierra Chart's normal `Edit >> Export Bar and Study Data to Text File` workflow
exports one row per loaded chart bar. It is useful for bar and study values, but
it is not enough for full footprint price-level data. Sierra's ACSIL
documentation says Volume at Price data is available through
`sc.VolumeAtPriceForBars`, and `sc.MaintainVolumeAtPriceData` must be enabled in
the study defaults block.

## Expected File

Windows path:

`C:\SierraChart\Data\AxonTrade_ES_VolumeAtPriceExport.txt`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_VolumeAtPriceExport.txt`

One CSV or tab-delimited row must represent one price level inside one chart
bar.

Required normalized fields:

- `timestamp`
- `symbol`
- `chart_number`
- `bar_index`
- `open`
- `high`
- `low`
- `close`
- `price`
- `bid_volume`
- `ask_volume`
- `session_phase`

Optional normalized fields:

- `level_volume`
- `delta`
- `number_of_trades`

Header aliases are configured in:

`config/research/sierra_volume_at_price_export.yaml`

## Check The Export

Manual help needed: **No after the export file exists**.

From the repository:

```bash
.venv/bin/python scripts/check_footprint_export.py
```

To check another file:

```bash
.venv/bin/python scripts/check_footprint_export.py \
  /path/to/AxonTrade_ES_VolumeAtPriceExport.txt \
  --fail-on-missing
```

Expected successful output starts with:

```text
status=PASS
manual_sierra_help_needed=no
```

## Sierra Manual Status

Manual help needed: **Not now**.

The repo can validate the file format. The Sierra-side producer is the
indicator-only ACSIL study documented in
`docs/sierra-volume-at-price-logger.md`. It:

1. sets `sc.MaintainVolumeAtPriceData = 1` in `sc.SetDefaults`;
2. reads each bar's `sc.VolumeAtPriceForBars` entries;
3. writes one row per bar/price level to
   `C:\SierraChart\Data\AxonTrade_ES_VolumeAtPriceExport.txt`;
4. does not place, modify, cancel, or flatten orders.

## Official Sierra References

- `Edit >> Export Bar and Study Data to Text File`:
  https://www.sierrachart.com/index.php?page=doc/EditMenu.html#ExportBarAndStudyDataToTextFile
- Accessing Volume at Price Data Per Bar:
  https://www.sierrachart.com/index.php?page=doc/ACSILProgrammingConcepts.html#AccessingVolumeAtPriceDataPerBar
- `sc.MaintainVolumeAtPriceData` / `sc.VolumeAtPriceForBars`:
  https://www.sierrachart.com/index.php?page=doc/ACSIL_Members_Variables_And_Arrays.html#scVolumeAtPriceForBars
