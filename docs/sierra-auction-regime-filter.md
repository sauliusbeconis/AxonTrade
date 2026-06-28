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

## Full Stack Pipeline

This command regenerates the auction-regime diagnostics, rolling selected
rules, target-R stack, breakeven stack, trade-level audits, and acceptance
reports from the current large Sierra export.

Manual help needed: **No** after the large Sierra export, signal log, and
quality diagnostics CSV exist.

Audit-grade full run:

```bash
.venv/bin/python scripts/run_signal_auction_regime_stack_pipeline.py
```

Non-overlapping holdout-date only:

```bash
.venv/bin/python scripts/run_signal_auction_regime_stack_pipeline.py \
  --samples holdout1
```

Use `--fail-on-reject` if the command should return a nonzero exit code when
the generated acceptance reports fail. The current checked sample is expected
to fail the acceptance gate.

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

Non-overlapping holdout-date audit:

```bash
.venv/bin/python scripts/run_signal_auction_regime_filter_walk_forward_sweep.py \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-holdout1-large-sample.csv \
  --train-date-count 8 \
  --holdout-date-count 1 \
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

## Guard Report

The filter reports accepted trades only. The guard report replays the selected
rules and shows both accepted and skipped candidate outcomes.

Train/holdout guard:

```bash
.venv/bin/python scripts/run_signal_auction_regime_guard_report.py \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-sweep-large-sample.csv \
  reports/sierra-signal-log-auction-regime-guard-sweep-large-sample.csv
```

Rolling walk-forward guard:

```bash
.venv/bin/python scripts/run_signal_auction_regime_guard_report.py \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-large-sample.csv \
  reports/sierra-signal-log-auction-regime-guard-walk-forward-large-sample.csv
```

Non-overlapping holdout-date guard:

```bash
.venv/bin/python scripts/run_signal_auction_regime_guard_report.py \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-holdout1-large-sample.csv \
  reports/sierra-signal-log-auction-regime-guard-walk-forward-holdout1-large-sample.csv
```

## Auction Guard Plus Health Gate

This report applies the selected auction-regime rule first, then selects a
closed-trade health gate on the auction-eligible training rows. The selected
health gate is applied to auction-eligible holdout rows with state warmed from
the training rows.

Manual help needed: **No** after the auction-regime diagnostics CSV and
selected-rule CSV exist.

Rolling walk-forward stack:

```bash
.venv/bin/python scripts/run_signal_auction_regime_health_gate_report.py \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-large-sample.csv \
  reports/sierra-signal-log-auction-regime-health-gate-walk-forward-large-sample.csv \
  --minimum-train-accepted-trades 4
```

## Auction Guard Plus Target R

This report applies the selected auction-regime rule first, then selects a
replacement target R on the auction-eligible training rows. The selected target
R is applied to auction-eligible holdout rows using the logged entry and stop.

Manual help needed: **No** after the large Sierra export, signal log,
auction-regime diagnostics CSV, and selected-rule CSV exist.

Rolling walk-forward stack:

```bash
.venv/bin/python scripts/run_signal_auction_regime_target_r_report.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-large-sample.csv \
  reports/sierra-signal-log-auction-regime-target-r-walk-forward-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --minimum-train-trades 4 \
  --target-r-multiples 0.5,1,1.5,2,2.5,3,3.5,4,4.5,5 \
  --direction-filters all,long,short
```

Non-overlapping holdout-date target-R stack:

```bash
.venv/bin/python scripts/run_signal_auction_regime_target_r_report.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-holdout1-large-sample.csv \
  reports/sierra-signal-log-auction-regime-target-r-walk-forward-holdout1-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --minimum-train-trades 4 \
  --target-r-multiples 0.5,1,1.5,2,2.5,3,3.5,4,4.5,5 \
  --direction-filters all,long,short
```

## Auction Guard Plus Breakeven Stop

This report applies the selected auction-regime rule first, then selects a
replacement target R plus a stop move to breakeven after a favorable R trigger.
The selected exit pair is applied to auction-eligible holdout rows using the
logged entry and stop.

Manual help needed: **No** after the large Sierra export, signal log,
auction-regime diagnostics CSV, and selected-rule CSV exist.

Rolling walk-forward stack:

```bash
.venv/bin/python scripts/run_signal_auction_regime_breakeven_report.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-large-sample.csv \
  reports/sierra-signal-log-auction-regime-breakeven-walk-forward-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --minimum-train-trades 4 \
  --target-r-multiples 0.5,1,1.25,1.5,2,2.5,3,3.5,4,4.5,5 \
  --breakeven-trigger-r-multiples 0.5,0.75,1,1.25,1.5,2,2.5 \
  --direction-filters all,long,short
```

Non-overlapping holdout-date breakeven stack:

```bash
.venv/bin/python scripts/run_signal_auction_regime_breakeven_report.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-holdout1-large-sample.csv \
  reports/sierra-signal-log-auction-regime-breakeven-walk-forward-holdout1-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --minimum-train-trades 4 \
  --target-r-multiples 0.5,1,1.25,1.5,2,2.5,3,3.5,4,4.5,5 \
  --breakeven-trigger-r-multiples 0.5,0.75,1,1.25,1.5,2,2.5 \
  --direction-filters all,long,short
```

## Trade-Level Audit

This report reconstructs the selected rolling stack one candidate at a time. It
marks rows as `evaluated`, `auction_skipped`, or `exit_direction_skipped`, and
adds duplicate markers when the same signal appears in multiple rolling
holdout windows.

Manual help needed: **No** after the large Sierra export, signal log,
auction-regime diagnostics CSV, and selected-rule CSV exist.

Target-R stack, rolling walk-forward:

```bash
.venv/bin/python scripts/run_signal_auction_regime_trade_audit.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-large-sample.csv \
  reports/sierra-signal-log-auction-regime-target-r-trade-audit-large-sample.csv \
  --stack-type target_r \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --minimum-train-trades 4 \
  --target-r-multiples 0.5,1,1.5,2,2.5,3,3.5,4,4.5,5 \
  --direction-filters all,long,short
```

Target-R stack, non-overlapping holdout-date audit:

```bash
.venv/bin/python scripts/run_signal_auction_regime_trade_audit.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-holdout1-large-sample.csv \
  reports/sierra-signal-log-auction-regime-target-r-trade-audit-holdout1-large-sample.csv \
  --stack-type target_r \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --minimum-train-trades 4 \
  --target-r-multiples 0.5,1,1.5,2,2.5,3,3.5,4,4.5,5 \
  --direction-filters all,long,short
```

Breakeven stack, rolling walk-forward:

```bash
.venv/bin/python scripts/run_signal_auction_regime_trade_audit.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-large-sample.csv \
  reports/sierra-signal-log-auction-regime-breakeven-trade-audit-large-sample.csv \
  --stack-type breakeven \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --minimum-train-trades 4 \
  --target-r-multiples 0.5,1,1.25,1.5,2,2.5,3,3.5,4,4.5,5 \
  --breakeven-trigger-r-multiples 0.5,0.75,1,1.25,1.5,2,2.5 \
  --direction-filters all,long,short
```

Breakeven stack, non-overlapping holdout-date audit:

```bash
.venv/bin/python scripts/run_signal_auction_regime_trade_audit.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-holdout1-large-sample.csv \
  reports/sierra-signal-log-auction-regime-breakeven-trade-audit-holdout1-large-sample.csv \
  --stack-type breakeven \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --minimum-train-trades 4 \
  --target-r-multiples 0.5,1,1.25,1.5,2,2.5,3,3.5,4,4.5,5 \
  --breakeven-trigger-r-multiples 0.5,0.75,1,1.25,1.5,2,2.5 \
  --direction-filters all,long,short
```

## Acceptance Gate

The acceptance gate checks trade-level audit rows against minimum evidence
thresholds before any simulation-only bot phase can treat a stack as eligible.

Manual help needed: **No** after the trade-level audit CSV exists.

Target-R holdout `1` acceptance check:

```bash
.venv/bin/python scripts/check_auction_regime_stack_acceptance.py \
  --audit reports/sierra-signal-log-auction-regime-target-r-trade-audit-holdout1-large-sample.csv \
  --report reports/sierra-signal-log-auction-regime-target-r-acceptance-holdout1-large-sample.md
```

Breakeven holdout `1` acceptance check:

```bash
.venv/bin/python scripts/check_auction_regime_stack_acceptance.py \
  --audit reports/sierra-signal-log-auction-regime-breakeven-trade-audit-holdout1-large-sample.csv \
  --report reports/sierra-signal-log-auction-regime-breakeven-acceptance-holdout1-large-sample.md
```

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

Guard accepted/skipped holdout result:

| Split | Accepted Trades | Accepted Net USD | Skipped Trades | Skipped Net USD |
| --- | ---: | ---: | ---: | ---: |
| Train/holdout | `2` | `-282.00` | `9` | `-1881.50` |
| Rolling walk-forward | `2` | `-257.00` | `17` | `-3634.50` |
| Rolling walk-forward, holdout `1` | `1` | `-128.50` | `10` | `-2035.00` |

Auction guard plus health-gate rolling holdout result:

| Accepted Trades | Health-Skipped Trades | Auction-Skipped Trades | Accepted Net USD | Health-Skipped Net USD | Auction-Skipped Net USD |
| ---: | ---: | ---: | ---: | ---: | ---: |
| `2` | `0` | `17` | `-257.00` | `0.00` | `-3634.50` |

Auction guard plus target-R rolling holdout result:

| Split | Evaluated Trades | Target Hits | Losses | Selected Target R Values | Accepted Net USD | Auction-Skipped Trades | Auction-Skipped Net USD |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Rolling walk-forward | `2` | `2` | `0` | `2R`, `2.5R` | `393.00` | `17` | `-3634.50` |
| Rolling walk-forward, holdout `1` | `1` | `1` | `0` | `2.5R` | `221.50` | `10` | `-2035.00` |

Auction guard plus breakeven-stop rolling holdout result:

| Split | Evaluated Trades | Target Hits | Losses | Breakeven Exits | Selected Target R Values | Selected Breakeven Trigger Values | Accepted Net USD | Auction-Skipped Trades | Auction-Skipped Net USD |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| Rolling walk-forward | `2` | `2` | `0` | `0` | `2R`, `2.5R` | `1.25R` | `393.00` | `17` | `-3634.50` |
| Rolling walk-forward, holdout `1` | `1` | `1` | `0` | `0` | `2.5R` | `1.25R` | `221.50` | `10` | `-2035.00` |

Trade-level audit result:

| Stack | Holdout Evaluated Rows | Unique Evaluated Holdout Signals | Duplicate Evaluated Rows | Evaluated Net USD |
| --- | ---: | ---: | ---: | ---: |
| Target-R rolling walk-forward | `2` | `1` | `1` | `393.00` |
| Target-R holdout `1` | `1` | `1` | `0` | `221.50` |
| Breakeven rolling walk-forward | `2` | `1` | `1` | `393.00` |
| Breakeven holdout `1` | `1` | `1` | `0` | `221.50` |

Acceptance gate result:

| Stack | Audit | Status | Unique Signals | Trade Dates | Duplicate Evaluated Rows | Unique Net USD | Largest Signal Share |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Target-R | Rolling walk-forward | `FAIL` | `1 / 30` | `1 / 15` | `2 / 0` | `171.50` | `100.00% / 25.00%` |
| Target-R | Holdout `1` | `FAIL` | `1 / 30` | `1 / 15` | `0 / 0` | `221.50` | `100.00% / 25.00%` |
| Breakeven | Rolling walk-forward | `FAIL` | `1 / 30` | `1 / 15` | `2 / 0` | `171.50` | `100.00% / 25.00%` |
| Breakeven | Holdout `1` | `FAIL` | `1 / 30` | `1 / 15` | `0 / 0` | `221.50` | `100.00% / 25.00%` |

Interpretation: auction-regime filters are useful as an explanation and
damage-control clue, but not as a validated entry edge. The filter avoided most
later losing holdout candidates by rejecting high-stretch directional sessions,
yet the trades it still accepted were also losers. The stacked health gate did
not improve the current holdout result because the auction guard left at most
one eligible trade in the losing holdout windows; a closed-trade health gate
cannot skip the first loss of a new day. The target-R stack is the first
positive holdout result after the auction guard, because the surviving June 17
long reached `3.75R` favorable before stopping while the original target was
`4.625R`. Adding a breakeven stop after a favorable R trigger did not improve
the current held-out net beyond target-R alone; the held-out accepted trades
hit target and recorded `0` breakeven exits. The non-overlapping holdout-date
audit reduces the positive result to one unique holdout trade for `+221.50`,
signal `liquidity_sweep_absorption_reversal_ESU26-CME_32971` on `2026-06-17`.
The overlapping audit counts that same signal twice with two selected exits
(`2R` and `2.5R`). Treat the target-R/breakeven stack as an exit hypothesis to
test on a larger export, not as automation approval. The executable acceptance
gate rejects both stacks on the current sample.
