# Sierra Delta Impulse Overlay Validation

Status: **PASS**

## Sources

- Bars export: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Large.txt`
- Signal log: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`

## Rule

- strategy ID: `delta_impulse_continue_10bar_2.5pt_50d`
- setup window: `09:45:00` through `15:45:00`
- lookback bars: `10`
- minimum price move: `2.5` points
- minimum delta sum: `50`
- minimum spacing: `900` seconds
- max signals per day: `6`
- fixed exits: `5 / 10 / 8 / initial`

## Summary

- expected candidates from bars: `163`
- Sierra candidate log rows: `163`
- matched rows: `163`
- missing rows: `0`
- unexpected rows: `0`
- field mismatches: `0`
- trade dates: `41`
- date range: `2026-03-23` through `2026-06-26`

## Interpretation

The Python baseline reproduces every Sierra candidate row for the exported bars. This validates the overlay entry rule, spacing filter, daily cap, and fixed stop/target fields for this sample.

## Differences

### Missing

None.

### Unexpected

None.

### Field Mismatches

None.
