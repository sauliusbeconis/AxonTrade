# MGC Orderflow Export Quality

Status: usable for offline research.

Source file:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_MGC_OrderflowExport_Expanded.txt`

## Result

The export passes the standard AxonTrade order-flow field check.

- file size: `123 MB`
- data rows: `813388`
- first bar: `2024-03-17 18:00:00`
- last bar: `2026-07-03 12:13:00`
- unique dates: `717`
- calendar span: `839` days
- timestamp parse failures: `0`
- duplicate timestamps: `0`
- zero-volume rows: `0`
- bid/ask volume mismatch rows: `0`
- blank VWAP rows: `0`
- minimum rows per date: `356`
- maximum rows per date: `1380`
- dates with fewer than `100` rows: `0`

Required fields found:

- timestamp from `Date + Time`;
- `Open`, `High`, `Low`, `Last`;
- `VWAP`;
- `Bid Volume`, `Ask Volume`;
- `Ask Volume Bid Volume Difference`.

## Coverage Notes

The export is one-minute Globex-style data. The largest gaps are expected
weekend/holiday session closures, not broken intraday backfill:

- `2024-03-28 16:59` to `2024-03-31 18:00`
- `2025-04-17 16:59` to `2025-04-20 18:00`
- `2026-04-02 16:59` to `2026-04-05 18:00`
- holiday early closes around `2025-07-04`, `2026-06-19`, and Thanksgiving

The final date, `2026-07-03`, is partial because the export ends at `12:13`.
That is expected for an export taken during the active session.

## Instrument Config

MGC was added to `config/instruments/MGC.yaml`.

- tick size: `0.10`
- tick value: `$1.00`
- point value: `$10.00`
- contract unit: `10` troy ounces

Primary source: CME Micro Gold futures contract specs.
