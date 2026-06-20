# Sierra Signal Log Outcomes

This workflow evaluates candidate rows emitted by the Sierra Chart
indicator-only overlay against later exported bars.

Manual help needed: **Yes before running this workflow**, because Sierra Chart
must export fresh bar data from the same chart and timezone as the signal log.

## Inputs

Signal log:

`C:\SierraChart\Data\AxonTrade_SignalLog.csv`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_SignalLog.csv`

Fresh Sierra bar export:

`C:\SierraChart\Data\AxonTrade_ES_OrderflowExport_NY.txt`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY.txt`

## Export Fresh Bars From Sierra

Manual help needed: **Yes**.

Use the same Sierra chart that generated the overlay signal log.

1. Click the ES footprint/execution chart window, currently chart `#2`.
2. Click `Chart >> Chart Settings`.
3. In `Chart Settings`, confirm the symbol is the same contract you replayed.
   The current signal log uses `ESU26-CME`.
4. Click `OK`.
5. Click `Edit >> Export Bar and Study Data to Text File`.
6. In the save dialog, go to Sierra's Data folder:
   `C:\SierraChart\Data`.
7. Save the file as:
   `AxonTrade_ES_OrderflowExport_NY.txt`.
8. If Sierra opens the exported text file after saving, close the text editor.

The export must come after `Global Settings >> Time Zone Settings` is set to
New York and after the replay segment has loaded the bars you want evaluated.

## Run Outcomes

Manual help needed: **No after the fresh export exists**.

From the repository:

```bash
.venv/bin/python scripts/run_signal_log_outcomes.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY.txt \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_SignalLog.csv \
  data/processed/AxonTrade_ES_overlay_signal_outcomes.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth
```

To evaluate the local replay sample instead of the active Sierra log:

```bash
.venv/bin/python scripts/run_signal_log_outcomes.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_replay_sample.csv \
  data/processed/AxonTrade_ES_overlay_signal_outcomes.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth
```

The runner first checks candidate entries against the nearest exported bar. If
it says `Export fresh bars from the same Sierra chart/timezone as the signal
log`, the export is stale, from the wrong chart, or from a different timezone.

## Run Path Diagnostics

Manual help needed: **No after the fresh export and outcome CSV exist**.

```bash
.venv/bin/python scripts/run_trade_path_diagnostics.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY.txt \
  data/processed/AxonTrade_ES_overlay_signal_outcomes.csv \
  reports/sierra-signal-log-path-diagnostics-replay-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth
```

This measures maximum favorable excursion, maximum adverse excursion, first
target touch, and first stop touch from the first bar after entry through the
evaluated exit.

## Run Quality Diagnostics

Manual help needed: **No after the signal log, outcome CSV, and optional path
diagnostics CSV exist**.

```bash
.venv/bin/python scripts/run_signal_quality_diagnostics.py \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  data/processed/AxonTrade_ES_overlay_signal_outcomes_large_sample.csv \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  --path-diagnostics reports/sierra-signal-log-path-diagnostics-large-sample.csv
```

This joins each evaluated outcome back to the candidate signal notes and path
diagnostics. The current fields focus on entry-known quality variables:
minutes after RTH open, original target/risk distance, sweep-to-entry bar gap,
sweep delta, sweep aggression ratio, and confirmation close location. Optional
MFE/MAE fields are included for post-trade diagnosis, not for entry filtering.

## Run Quality Filter Sweep

Manual help needed: **No after the quality diagnostics CSV exists**.

```bash
.venv/bin/python scripts/run_signal_quality_filter_sweep.py \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  reports/sierra-signal-log-quality-filter-sweep-large-sample.csv \
  --max-original-reward-risks 1.5,2,2.5,3,3.5,4,999 \
  --min-minutes-after-rth-open 0,60,90 \
  --max-minutes-after-rth-open 120,150,180,240,390 \
  --max-sweep-abs-deltas 3,5,10,20,999999 \
  --direction-filters all,long,short
```

This tests entry-known filters only: target distance in R, minutes after RTH
open, absolute sweep delta, and direction. It does not change exits.

## Run Quality Filter Walk-Forward

Manual help needed: **No after the quality diagnostics CSV exists**.

```bash
.venv/bin/python scripts/run_signal_quality_filter_walk_forward_sweep.py \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  reports/sierra-signal-log-quality-filter-walk-forward-large-sample.csv \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-train-trades 4 \
  --max-original-reward-risks 1.5,2,2.5,3,3.5,4,999 \
  --min-minutes-after-rth-open 0,60,90 \
  --max-minutes-after-rth-open 120,150,180,240,390 \
  --max-sweep-abs-deltas 3,5,10,20,999999 \
  --direction-filters all,long,short
```

This selects the best quality filter on earlier candidate dates, then evaluates
the same filter on later candidate dates.

## Run Target R Sweep

Manual help needed: **No after the fresh export and signal log exist**.

```bash
.venv/bin/python scripts/run_signal_target_r_sweep.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_replay_sample.csv \
  reports/sierra-signal-log-target-r-sweep-replay-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --target-r-multiples 0.5,1,1.5,2,2.5,3,3.5,4,4.5,5 \
  --direction-filters all,long,short
```

This keeps the logged entry and stop fixed, replaces only the target price with
an R-multiple of the original risk, and re-evaluates conservative outcomes.

## Run Target R Walk-Forward

Manual help needed: **No after the fresh export and signal log exist**.

```bash
.venv/bin/python scripts/run_signal_target_r_walk_forward_sweep.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-target-r-walk-forward-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-train-trades 4 \
  --target-r-multiples 0.5,1,1.5,2,2.5,3,3.5,4,4.5,5 \
  --direction-filters all,long,short
```

This selects the best target R and direction filter on earlier candidate dates,
then evaluates the same selection on later candidate dates.

## Run Breakeven Stop Sweep

Manual help needed: **No after the fresh export and signal log exist**.

```bash
.venv/bin/python scripts/run_signal_breakeven_stop_sweep.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-breakeven-stop-sweep-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --target-r-multiples 1,1.25,1.5,2,2.5,3 \
  --breakeven-trigger-r-multiples 0.5,0.75,1,1.25,1.5 \
  --direction-filters all,long,short
```

This keeps the logged entry and initial stop fixed, replaces the target with a
fixed R multiple, and moves the stop to entry after price reaches the configured
favorable R threshold. If one exported OHLC bar can mean both target and active
stop were hit, the simulator chooses the stop first.

## Run Breakeven Stop Walk-Forward

Manual help needed: **No after the fresh export and signal log exist**.

```bash
.venv/bin/python scripts/run_signal_breakeven_stop_walk_forward_sweep.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-breakeven-stop-walk-forward-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-train-trades 4 \
  --target-r-multiples 1,1.25,1.5,2,2.5,3 \
  --breakeven-trigger-r-multiples 0.5,0.75,1,1.25,1.5 \
  --direction-filters all,long,short
```

This selects the best target R, breakeven trigger R, and direction filter on
earlier candidate dates, then evaluates the same selection on later candidate
dates.

## Output

Outcome rows are written to:

`data/processed/AxonTrade_ES_overlay_signal_outcomes.csv`

The output is a local research artifact and is ignored by Git.

## Current Replay Outcome Sample

Report:

`reports/sierra-signal-log-outcomes-replay-sample.md`

Current result from the matched New York-time export:

- candidate signals: `2`
- evaluated trades: `2`
- target hits: `0`
- stop/ambiguous losses: `1`
- other exits: `1`
- net USD: `-182.00`

Path diagnostics:

`reports/sierra-signal-log-path-diagnostics-replay-sample.csv`

Current diagnostic split:

- `neither_stop_nor_target_reached`: `1`
- `stop_reached_target_not_reached`: `1`

Notable failure mode: the `2026-06-17 10:42:28` long moved `7.5` points
favorable, but the target was `9.25` points away, then price reached the stop.
That makes target placement a concrete next research variable.

Target R sweep:

`reports/sierra-signal-log-target-r-sweep-replay-sample.csv`

Current aggregate result for `direction=all`:

| Target R | Trades | Target Hits | Losses | Other | Net USD |
| ---: | ---: | ---: | ---: | ---: | ---: |
| `0.5` | `2` | `1` | `0` | `1` | `-32` |
| `1` | `2` | `1` | `0` | `1` | `18` |
| `1.5` | `2` | `1` | `0` | `1` | `68` |
| `2` | `2` | `1` | `0` | `1` | `118` |
| `2.5` | `2` | `1` | `0` | `1` | `168` |
| `3` | `2` | `1` | `0` | `1` | `218` |
| `3.5` | `2` | `1` | `0` | `1` | `268` |
| `4` | `2` | `0` | `1` | `1` | `-182` |
| `4.5` | `2` | `0` | `1` | `1` | `-182` |
| `5` | `2` | `0` | `1` | `1` | `-182` |

Interpretation: on this tiny two-candidate replay sample, `3.5R` is the best
tested target because the June 17 trade reached about `3.75R` favorable before
stopping. This is not validation; it is a concrete hypothesis for a larger
replay/export sample.

## Larger Recalculation Sample

Signal report:

`reports/sierra-signal-log-large-sample.md`

Outcome report:

`reports/sierra-signal-log-outcomes-large-sample.md`

Path diagnostics:

`reports/sierra-signal-log-path-diagnostics-large-sample.csv`

Quality diagnostics:

`reports/sierra-signal-log-quality-diagnostics-large-sample.csv`

Quality filter sweep:

`reports/sierra-signal-log-quality-filter-sweep-large-sample.csv`

Quality filter walk-forward:

`reports/sierra-signal-log-quality-filter-walk-forward-large-sample.csv`

Target R sweep:

`reports/sierra-signal-log-target-r-sweep-large-sample.csv`

Target R walk-forward:

`reports/sierra-signal-log-target-r-walk-forward-large-sample.csv`

Breakeven stop sweep:

`reports/sierra-signal-log-breakeven-stop-sweep-large-sample.csv`

Breakeven stop walk-forward:

`reports/sierra-signal-log-breakeven-stop-walk-forward-large-sample.csv`

Sample range:

- first row: `2026-05-21 09:30:00`
- last row: `2026-06-19 12:59:58`
- signal rows: `43048`
- candidate signals: `23`
- long candidates: `12`
- short candidates: `11`

Original opening-range-midpoint target result:

- evaluated trades: `23`
- target hits: `7`
- stop/ambiguous losses: `16`
- other exits: `0`
- win rate: `30.43%`
- net USD: `-880.50`

Path diagnostic split:

- `target_reached_stop_not_reached`: `7`
- `stop_reached_target_not_reached`: `16`

Quality diagnostic observations:

- diagnostic rows: `23`
- original target hits: `7`
- original stops: `16`
- target-hit median original reward/risk: `1.74R`
- stop-hit median original reward/risk: `3.85R`
- `original_reward_risk > 3`: `11` trades, `1` target hit, net `-1432.25`
- `original_reward_risk > 4`: `8` trades, `0` target hits, net `-1478.00`
- `original_reward_risk <= 2.5`: `10` trades, `6` target hits, net `1021.25`
- `sweep_abs_delta >= 5`: `10` trades, `1` target hit, net `-1641.25`

Interpretation: the clearest current failure mode is taking midpoint targets
that are too far from entry relative to stop distance. Simple "bigger sweep is
better" logic is not supported by this sample. This is still in-sample
diagnosis on only `23` candidates, so use it to design the next filter test,
not as production evidence.

External parameter clues, retrieved `2026-06-20`:

- [Returns and Order Flow Imbalances: Intraday Dynamics and Macroeconomic News Effects](https://arxiv.org/html/2508.06788)
  studies S&P 500 E-mini futures at one-second frequency by 15-minute interval.
  Practical clue: time-of-day and news context matter; do not use a single raw
  order-flow threshold across the whole session.
- [Intraday Trading Invariance in the E-mini S&P 500 Futures Market](https://ideas.repec.org/p/cfr/cefirw/w0229.html)
  reports a pronounced intraday diurnal pattern and a relationship between
  return variation per transaction and trade size. Practical clue: raw volume or
  sweep size should eventually be normalized by activity/volatility.
- [Overnight-Intraday Reversal Everywhere](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2730304)
  documents reversal behavior across asset classes and links it to liquidity
  provision. Practical clue: reversal logic is plausible, but should be tested
  by session context instead of assumed from every sweep.
- [CME Group: Reassessing Liquidity, Beyond Order Book Depth](https://www.cmegroup.com/articles/2025/reassessing-liquidity-beyond-order-book-depth.html)
  shows that ES volume and order-book depth can move in opposite directions
  during volatility. Practical clue: a large sweep alone is not enough; combine
  it with contextual filters.

Quality filter aggregate sweep:

| Direction | Max Original RR | Minutes After Open | Max Sweep Abs Delta | Trades | Target Hits | Losses | Net USD |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `all` | `3.5` | `0-120` | `3` | `6` | `5` | `1` | `1691.50` |
| `all` | `3.5` | `0-120` | `999999` | `8` | `6` | `2` | `1628.25` |
| `all` | `3.5` | `0-150` | `999999` | `9` | `6` | `3` | `1387.25` |
| `all` | `3.5` | `0-390` | `3` | `10` | `6` | `4` | `1358.75` |

Rolling quality filter walk-forward validation:

- train date count: `8`
- holdout date count: `2`
- minimum selected train trades: `4`
- holdout windows: `6`
- selected holdout trades: `4`
- selected holdout target hits: `0`
- selected holdout losses: `4`
- selected holdout net USD: `-1064.00`

Interpretation: quality filters reduce trade count and improve several
aggregate rows, but the selected filters still failed chronologically. This is
less bad than the target-only and breakeven-stop walk-forward runs, but it is
still not a validated edge. The next improvement should avoid raw sweep-size
thresholds and add normalized context: current volatility, current traded
volume, and scheduled-news exclusion.

Target R sweep, `direction=all`:

| Target R | Trades | Target Hits | Losses | Other | Win Rate | Net USD |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `0.5` | `23` | `12` | `11` | `0` | `52.17%` | `-1655.5` |
| `1` | `23` | `12` | `11` | `0` | `52.17%` | `-543` |
| `1.5` | `23` | `12` | `11` | `0` | `52.17%` | `569.5` |
| `2` | `23` | `12` | `11` | `0` | `52.17%` | `1682` |
| `2.5` | `23` | `10` | `13` | `0` | `43.48%` | `1394.5` |
| `3` | `23` | `8` | `14` | `1` | `34.78%` | `657` |
| `3.5` | `23` | `7` | `15` | `1` | `30.43%` | `725.75` |
| `4` | `23` | `5` | `17` | `1` | `21.74%` | `219.5` |
| `4.5` | `23` | `5` | `17` | `1` | `21.74%` | `725.75` |
| `5` | `23` | `3` | `18` | `2` | `13.04%` | `-55.5` |

Interpretation: the larger sample does not support the current
opening-range-midpoint target. In the fixed-R sweep, `2R` is the best aggregate
tested target. Direction-specific rows suggest `2.5R` performed best for longs
and `4.5R` performed best for shorts, but those are still small subsamples and
must be tested chronologically before changing the Sierra overlay defaults.

Rolling walk-forward validation:

- train date count: `8`
- holdout date count: `2`
- minimum selected train trades: `4`
- holdout windows: `6`
- selected holdout trades: `13`
- selected holdout net USD: `-2408.00`

| Window | Train Dates | Holdout Dates | Selected Direction | Selected Target R | Train Net USD | Holdout Trades | Holdout Net USD |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: |
| `1` | `2026-05-21` to `2026-06-03` | `2026-06-04` to `2026-06-08` | `all` | `2.5` | `2770.5` | `3` | `-798` |
| `2` | `2026-05-22` to `2026-06-04` | `2026-06-08` to `2026-06-10` | `all` | `2.5` | `2299` | `4` | `-489` |
| `3` | `2026-05-25` to `2026-06-08` | `2026-06-10` to `2026-06-11` | `long` | `2` | `691.5` | `2` | `-332` |
| `4` | `2026-05-26` to `2026-06-10` | `2026-06-11` to `2026-06-12` | `short` | `4.5` | `601.25` | `2` | `-469.5` |
| `5` | `2026-05-27` to `2026-06-11` | `2026-06-12` to `2026-06-17` | `short` | `2` | `32.5` | `1` | `-203.5` |
| `6` | `2026-05-29` to `2026-06-12` | `2026-06-17` to `2026-06-19` | `short` | `2` | `-171` | `1` | `-116` |

Interpretation: target R optimization did not validate chronologically. The
aggregate `2R` result is likely overfit to this sample. Do not change Sierra
overlay target defaults from this result alone. The next research step should
filter or improve candidate quality before another target-optimization pass.

Breakeven stop aggregate sweep:

| Direction | Target R | BE Trigger R | Trades | Target Hits | Losses | BE Exits | Net USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `all` | `2.5` | `1.25` | `23` | `10` | `11` | `2` | `1794.50` |
| `all` | `2.5` | `1.5` | `23` | `10` | `11` | `2` | `1794.50` |
| `all` | `2` | `1.25` | `23` | `12` | `11` | `0` | `1682.00` |
| `long` | `2.5` | `1.25` | `12` | `6` | `5` | `1` | `1358.00` |
| `all` | `1.5` | `1` | `23` | `10` | `11` | `2` | `-161.75` |

Rolling breakeven stop walk-forward validation:

- train date count: `8`
- holdout date count: `2`
- minimum selected train trades: `4`
- holdout windows: `6`
- selected holdout trades: `12`
- selected holdout target hits: `1`
- selected holdout losses: `11`
- selected holdout breakeven exits: `0`
- selected holdout net USD: `-2142.00`

Interpretation: the dynamic breakeven stop improved the best aggregate row from
the fixed target-only sweep, but it still failed chronological validation. The
specific proposed rule `target=1.5R, breakeven_trigger=1R` was negative on the
large sample under conservative OHLC ordering. Candidate quality filters remain
the higher-priority research step.

Implementation note: Sierra exports sub-second bar timestamps, while the signal
log stores whole-second bar times. Outcome preflight therefore validates matching
entries by same-day `bar_index` first, then falls back to nearest timestamp.
