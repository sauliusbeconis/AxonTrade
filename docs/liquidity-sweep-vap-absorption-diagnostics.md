# Liquidity Sweep VAP Absorption Diagnostics

This workflow joins existing absorption outcomes to the Sierra
volume-at-price export and measures swept-zone bid/ask volume.

Manual help needed: **No** after
`C:\SierraChart\Data\AxonTrade_ES_VolumeAtPriceExport.txt` exists.

## Run

```bash
.venv/bin/python scripts/run_vap_absorption_diagnostics.py \
  data/processed/AxonTrade_ES_absorption_signals.csv \
  data/processed/AxonTrade_ES_absorption_outcomes.csv \
  reports/liquidity-sweep-vap-absorption-diagnostics-sample.csv \
  --vap-input /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_VolumeAtPriceExport.txt \
  --symbol ESU26-CME \
  --minimum-zone-volume 20
```

## Rule Measured

For each evaluated absorption outcome:

- parse `sweep_bar_index` from the candidate signal notes;
- recover the swept extreme from stop price and stop buffer;
- inspect the `1.0` point zone nearest the swept extreme;
- calculate swept-zone bid volume, ask volume, delta, and aggressor ratio;
- mark `level_absorption_pass=true` when the zone has sweep-side delta,
  aggression ratio at least `1.25`, and total zone volume at least `20`.

## Current Sample Result

Input files:

- signals: `data/processed/AxonTrade_ES_absorption_signals.csv`
- outcomes: `data/processed/AxonTrade_ES_absorption_outcomes.csv`
- VAP export:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_VolumeAtPriceExport.txt`

VAP export check:

- rows: `115219`
- dates: `2026-05-21` through `2026-06-19`
- symbol: `ESU26-CME`
- chart number: `2`

Diagnostic result:

| Bucket | Trades | Target hits | Losses | Net USD |
| --- | ---: | ---: | ---: | ---: |
| `level_absorption_pass=true` | `12` | `6` | `6` | `64.25` |
| `level_absorption_pass=false` | `18` | `9` | `9` | `-1088.00` |

Interpretation: swept-zone volume is a better hypothesis than raw VAP aggression
ratio alone, but this is not validated. The `20` volume threshold was selected
after inspecting this sample, so the next step is a chronological sweep over VAP
thresholds.

Follow-up: the chronological threshold sweep is documented in
`docs/liquidity-sweep-vap-threshold-sweep.md`. The train-selected VAP threshold
did not survive holdout.
