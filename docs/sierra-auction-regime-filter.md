# Sierra Auction-Regime Filter

This workflow tests whether logged liquidity-sweep fade candidates fail because
the session is already in a directional auction instead of a balanced
mean-reverting range.

Manual help needed: **No** after the orderflow bar export and quality
diagnostics CSV exist.

## Diagnostics

Command:

```bash
.venv/bin/python scripts/run_signal_auction_regime_diagnostics.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth
```

Entry-known fields:

- session range from RTH open through the entry bar
- entry close position inside the session range
- direction-aware fade edge score
- direction-aware distance from VWAP
- direction-aware distance from session open
- opening-range edge/outside distance

## Filter Sweeps

Train/holdout:

```bash
.venv/bin/python scripts/run_signal_auction_regime_filter_sweep.py \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-sweep-large-sample.csv \
  --train-date-count 8 \
  --minimum-train-trades 4
```

Rolling walk-forward:

```bash
.venv/bin/python scripts/run_signal_auction_regime_filter_walk_forward_sweep.py \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-large-sample.csv \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-train-trades 4
```

Default tested grids:

- direction filters: `all,long,short`
- max original reward/risk: `2,2.5,3.5,999`
- minimum minutes after RTH open: `0,60`
- maximum minutes after RTH open: `120,240,390`
- max session range points: `20,35,50,999`
- max fade edge score: `0.65,0.75,0.85,1`
- max direction-aware VWAP stretch: `3,6,10,20,999`
- max direction-aware open stretch: `3,6,10,20,999`

## Current Large Sierra Signal Sample

Diagnostic separation:

| Field | Winner Median | Loser Median |
| --- | ---: | ---: |
| Session range points | `33.50` | `48.25` |
| Fade edge score | `0.65079365` | `0.80310881` |
| VWAP stretch points | `4.05` | `12.57` |
| Open stretch points | `5.00` | `16.75` |
| Original reward/risk | `1.74` | `4.20` |

Train/holdout selected rule:

- direction filter: `all`
- max original reward/risk: `3.5`
- minutes after RTH open: `0` to `390`
- max session range: `50`
- max fade edge score: `1`
- max VWAP stretch: `10`
- max open stretch: `20`
- train trades: `9`
- train target hits: `7`
- train losses: `2`
- train net: `2018.50` USD
- holdout trades: `2`
- holdout target hits: `0`
- holdout losses: `2`
- holdout net: `-282.00` USD

Rolling walk-forward selected holdout result:

- holdout windows: `6`
- selected holdout trades: `2`
- target hits: `0`
- losses: `2`
- net result after default costs: `-257.00` USD

Interpretation: auction-regime filters are useful as an explanation and
damage-control clue, but not as a validated entry edge. The filter avoided most
later losing holdout candidates by rejecting high-stretch directional sessions,
yet the trades it still accepted were also losers. This supports adding a
future no-trade regime guard, not enabling automation.
