# Liquidity Sweep VAP Threshold Sweep

This workflow tests whether swept-zone volume-at-price thresholds improve the
absorption setup after the VAP diagnostic metrics have been generated.

Manual help needed: **No** after the VAP diagnostics CSV exists.

## Run

First regenerate diagnostics so `entry_time` is available for chronological
splits:

```bash
.venv/bin/python scripts/run_vap_absorption_diagnostics.py \
  data/processed/AxonTrade_ES_absorption_signals.csv \
  data/processed/AxonTrade_ES_absorption_outcomes.csv \
  reports/liquidity-sweep-vap-absorption-diagnostics-sample.csv \
  --vap-input /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_VolumeAtPriceExport.txt \
  --symbol ESU26-CME \
  --minimum-zone-volume 20
```

Then run the threshold sweep:

```bash
.venv/bin/python scripts/run_vap_absorption_threshold_sweep.py \
  reports/liquidity-sweep-vap-absorption-diagnostics-sample.csv \
  reports/liquidity-sweep-vap-threshold-sweep-sample.csv \
  --train-date-count 12
```

Default tested grids:

- minimum swept-zone aggression ratios: `1,1.25,1.5,2,3`
- minimum swept-zone volumes: `0,5,10,20,50,100,150,200`
- direction filters: `all,long,short`

## Current Sample Result

Chronological split:

- train dates: first `12` active trade dates, `2026-05-22` through `2026-06-10`
- holdout dates: last `7` active trade dates, `2026-06-11` through `2026-06-19`
- output: `reports/liquidity-sweep-vap-threshold-sweep-sample.csv`

Train-selected rule:

- direction filter: `long`
- minimum swept-zone aggression ratio: `1`
- minimum swept-zone volume: `10`
- train trades: `2`
- train net: `93.00` USD

Matching holdout row:

- holdout trades: `5`
- target hits: `1`
- losses: `4`
- holdout net: `-267.50` USD

Interpretation: this does not validate the current VAP threshold idea. The
sample still shows that high swept-zone volume is interesting, especially on
some later short trades, but the chronological train-selected rule did not
survive holdout.

## Interpretation Rules

- The selected train row is the highest train `net_usd` among rows with at
  least one training trade.
- The matching holdout row is the validation row.
- Do not use the best holdout row as evidence; that is in-sample selection on
  the holdout period.
- This remains research-only and does not imply an executable strategy.
