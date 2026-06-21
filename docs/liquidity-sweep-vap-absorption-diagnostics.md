# Liquidity Sweep VAP Absorption Diagnostics

This workflow joins existing absorption outcomes to the Sierra
volume-at-price export and measures swept-zone bid/ask volume.

Manual help needed: **No** after a fresh
`C:\SierraChart\Data\AxonTrade_ES_VolumeAtPriceExport.txt` exists from the
same Sierra chart, timezone, replay segment, and contract as the signal log.

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

For the current large Sierra signal sample:

```bash
.venv/bin/python scripts/run_vap_absorption_diagnostics.py \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  data/processed/AxonTrade_ES_overlay_signal_outcomes_large_sample.csv \
  reports/sierra-signal-log-vap-absorption-diagnostics-large-sample.csv \
  --vap-input /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_VolumeAtPriceExport.txt \
  --symbol ESU26-CME \
  --minimum-zone-volume 0
```

The command fails with `status=FAIL vap_coverage=0` when the VAP file is stale
or came from a different chart. In that case manual help is needed: refresh the
VAP export using `Analysis >> Studies >> AxonTrade Volume At Price CSV Logger >>
Settings >> Settings and Inputs >> Export Now = Yes` on the same ES chart that
produced `C:\SierraChart\Data\AxonTrade_ES_OrderflowExport_NY_Large.txt`.

## Rule Measured

For each evaluated absorption outcome:

- parse `sweep_bar_index` from the candidate signal notes;
- join VAP levels by sweep bar index, then by the sweep bar timestamp if the
  bar indexes drift after a chart reload;
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

## Current Large Sierra Signal Sample

Input files:

- signals: `data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv`
- outcomes:
  `data/processed/AxonTrade_ES_overlay_signal_outcomes_large_sample.csv`
- VAP export:
  `C:\SierraChart\Data\AxonTrade_ES_VolumeAtPriceExport.txt`
- output:
  `reports/sierra-signal-log-vap-absorption-diagnostics-large-sample.csv`

Command:

```bash
.venv/bin/python scripts/run_vap_absorption_diagnostics.py \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  data/processed/AxonTrade_ES_overlay_signal_outcomes_large_sample.csv \
  reports/sierra-signal-log-vap-absorption-diagnostics-large-sample.csv \
  --vap-input /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_VolumeAtPriceExport.txt \
  --symbol ESU26-CME \
  --sweep-zone-points 1.0 \
  --stop-buffer-points 0.25 \
  --minimum-zone-aggression-ratio 1.25 \
  --minimum-zone-volume 0
```

Result:

- evaluated trades: `23`
- VAP covered trades: `23`
- default level-absorption passes: `23`
- target hits: `7`
- losses: `16`
- net USD: `-880.50`
- swept-zone volume min/median/max: `1` / `6` / `205`
- swept-zone aggression ratio min/median/max: `1.25641026` / `3.5` / `inf`

Interpretation: the refreshed VAP export is aligned and usable, but the default
swept-zone aggression rule does not discriminate. Every evaluated candidate
passes, so the next useful test is threshold validation, not another default
diagnostic run.
