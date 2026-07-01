# NQ/MNQ Research Plan

Status date: 2026-07-01.

## Scope

NQ/MNQ research is separate from ES/MES. ES thresholds, exits, and risk locks
must not be copied directly.

The practical path is:

1. research NQ first for cleaner point-value signal math;
2. translate to MNQ for sizing and prop-eval risk;
3. only consider NQ live sizing after MNQ behavior and drawdown are understood.

## Current Local Data

Local Sierra SCID files found:

| File | First Tick | Last Tick | Records |
| --- | --- | --- | ---: |
| `NQM26-CME.scid` | `2025-12-15 12:44:37` | `2026-06-18 13:29:55` | `34,295,042` |
| `MNQM26-CME.scid` | `2025-12-15 09:53:09` | `2026-06-18 13:29:59` | `123,393,887` |

This is useful for tooling and first-pass reconnaissance, but it is not enough
for a production conclusion:

- it is only the June 2026 contract;
- the current September contract files were not present locally;
- chart/session timezone must be confirmed against Sierra before trusting RTH
  window results;
- no manual NQ/MNQ orderflow export was available yet.

## Tooling Added

`scripts/export_sierra_scid_bars.py` streams a Sierra `.scid` file into
Sierra-export-compatible OHLCV bars with bid/ask volume and delta fields.

Example:

```bash
.venv/bin/python scripts/export_sierra_scid_bars.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/NQM26-CME.scid \
  data/processed/AxonTrade_NQ_scid_3min_rth_20251215_20260618.csv \
  --symbol NQM26-CME \
  --chart-number 1 \
  --date-from 2025-12-15 \
  --date-to 2026-06-18
```

The exporter handles Sierra files where per-record `Open` is `0` by using the
first record close as the bar open.

## Initial Recon Result

Initial NQ sweep source:

`data/processed/AxonTrade_NQ_scid_3min_rth_20251215_20260618.csv`

The first full-sample sweep was intentionally broad and produced suspiciously
strong results, including a positive random baseline. That means this pass is a
data/tooling diagnostic, not a candidate.

Focused walk-forward, one tick total slippage per contract:

| Strategy | Windows | Trades | Net | Avg/Trade | Negative Windows | Worst Window |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `impulse_continue_3bar_1.5pt` | 22 | 2193 | `135789` | `61.92` | 10 | `-9300` |
| `impulse_continue_5bar_2pt` | 22 | 2184 | `106857` | `48.93` | 8 | `-16000` |
| `vwap_extension_fade_3pt` | 22 | 2195 | `86175` | `39.26` | 8 | `-17700` |
| `impulse_fade_5bar_2pt` | 22 | 2184 | `81842` | `37.47` | 5 | `-17100` |
| `random_25_per_day` | 22 | 2750 | `21040` | `7.65` | 10 | `-16125` |

Focused walk-forward, four ticks total slippage per contract:

| Strategy | Windows | Trades | Net | Avg/Trade | Negative Windows | Worst Window |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `impulse_continue_3bar_1.5pt` | 22 | 2193 | `69999` | `31.92` | 10 | `-12300` |
| `impulse_continue_5bar_2pt` | 22 | 2184 | `41337` | `18.93` | 10 | `-19000` |
| `vwap_extension_fade_3pt` | 22 | 2195 | `20325` | `9.26` | 8 | `-20700` |
| `impulse_fade_5bar_2pt` | 22 | 2184 | `16322` | `7.47` | 10 | `-20100` |
| `random_25_per_day` | 22 | 2750 | `-61460` | `-22.35` | 14 | `-19875` |

## Decision

No NQ/MNQ candidate is accepted yet.

`impulse_continue_3bar_1.5pt` is the first research lead because it survived
the four-tick slippage stress while random turned negative. It still has too
many negative windows and the source data/session assumptions are unresolved.

## Next Steps

1. Confirm Sierra chart timezone/session alignment for SCID timestamps.
2. Export or download current NQU/MNQU data before treating the sample as
   representative.
3. Run a smaller NQ-specific parameter grid around the impulse-continuation
   lead.
4. Add health gates based on maximum trade-sequence drawdown and worst
   5-trading-day window.
5. Translate only surviving NQ rules to MNQ sizing.
