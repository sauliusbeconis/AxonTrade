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

## Run Auction-Regime Stack Pipeline

Manual help needed: **No after the large Sierra export, signal log, and quality
diagnostics CSV exist**.

```bash
.venv/bin/python scripts/run_signal_auction_regime_stack_pipeline.py
```

For non-overlapping holdout-date outputs only:

```bash
.venv/bin/python scripts/run_signal_auction_regime_stack_pipeline.py \
  --samples holdout1
```

For a faster target-R-only holdout-date check:

```bash
.venv/bin/python scripts/run_signal_auction_regime_stack_pipeline.py \
  --samples holdout1 \
  --stacks target_r
```

This regenerates auction-regime diagnostics, selected rolling rules, target-R
and breakeven stack reports, trade-level audits, and acceptance reports. The
current checked sample is expected to finish with acceptance status `FAIL`.

## Run Context Diagnostics

Manual help needed: **No after the orderflow export and quality diagnostics CSV
exist**.

```bash
.venv/bin/python scripts/run_signal_context_diagnostics.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  reports/sierra-signal-log-context-diagnostics-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --lookback-bars 50
```

This adds rolling pre-entry context from the orderflow bar export: average bar
range, average volume, average trade count, average absolute delta, entry-bar
volume/trades/delta, and normalized ratios such as
`sweep_abs_delta_to_average_abs_delta`.

## Run Context Filter Sweep

Manual help needed: **No after the context diagnostics CSV exists**.

```bash
.venv/bin/python scripts/run_signal_context_filter_sweep.py \
  reports/sierra-signal-log-context-diagnostics-large-sample.csv \
  reports/sierra-signal-log-context-filter-sweep-large-sample.csv
```

This tests entry-known context thresholds on top of the quality diagnostic
fields: original reward/risk, RTH time window, raw sweep delta, risk/target
distance normalized by recent bar range, sweep delta normalized by recent
absolute delta, and entry activity normalized by recent volume/trade count.

## Run Context Filter Walk-Forward

Manual help needed: **No after the context diagnostics CSV exists**.

```bash
.venv/bin/python scripts/run_signal_context_filter_walk_forward_sweep.py \
  reports/sierra-signal-log-context-diagnostics-large-sample.csv \
  reports/sierra-signal-log-context-filter-walk-forward-large-sample.csv \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-train-trades 4
```

This chronologically selects the best context filter on each training window,
then applies that exact filter to the next holdout dates.

## Run Structure Filter Sweep

Manual help needed: **No after the quality diagnostics CSV exists**.

```bash
.venv/bin/python scripts/run_signal_structure_filter_sweep.py \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  reports/sierra-signal-log-structure-filter-sweep-large-sample.csv
```

This tests stricter entry-known setup-structure filters: maximum bars from
sweep to confirmation, minimum sweep-side aggression ratio, and direction-aware
confirmation close location, on top of reward/risk, time, and sweep-size
filters.

## Run Structure Filter Walk-Forward

Manual help needed: **No after the quality diagnostics CSV exists**.

```bash
.venv/bin/python scripts/run_signal_structure_filter_walk_forward_sweep.py \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  reports/sierra-signal-log-structure-filter-walk-forward-large-sample.csv \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-train-trades 4
```

This chronologically selects the best structure filter on each training window,
then applies that exact filter to the next holdout dates.

## Run Health Gate Sweep

Manual help needed: **No after the quality diagnostics CSV exists**.

```bash
.venv/bin/python scripts/run_signal_health_gate_sweep.py \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  reports/sierra-signal-log-health-gate-sweep-large-sample.csv
```

This replays candidate outcomes chronologically and tests bot-control gates
based only on closed accepted trades: maximum daily losses, daily realized loss
limit, consecutive-loss pauses, and accepted-equity drawdown pauses. Skipped
trades do not update health state, matching what a live bot would know.

## Run Health Gate Walk-Forward

Manual help needed: **No after the quality diagnostics CSV exists**.

```bash
.venv/bin/python scripts/run_signal_health_gate_walk_forward_sweep.py \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  reports/sierra-signal-log-health-gate-walk-forward-large-sample.csv \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-train-accepted-trades 4
```

This selects health-gate parameters on each training window, then applies the
selected gate to the next holdout dates with health state warmed by the
training window.

## Run Auction-Regime Plus Health Gate Report

Manual help needed: **No after the auction-regime diagnostics CSV and
selected-rule CSV exist**.

```bash
.venv/bin/python scripts/run_signal_auction_regime_health_gate_report.py \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-large-sample.csv \
  reports/sierra-signal-log-auction-regime-health-gate-walk-forward-large-sample.csv \
  --minimum-train-accepted-trades 4
```

This applies the selected auction-regime guard first, then selects a
closed-trade health gate on the auction-eligible training rows and evaluates the
same health gate on auction-eligible holdout rows.

## Run Auction-Regime Plus Target R Report

Manual help needed: **No after the large Sierra export, signal log,
auction-regime diagnostics CSV, and selected-rule CSV exist**.

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

This applies the selected auction-regime guard first, then selects a
replacement target R on the auction-eligible training rows and evaluates the
same target policy on auction-eligible holdout rows.

To avoid overlapping holdout-date double counting, rerun the auction-regime
selection with one holdout date:

```bash
.venv/bin/python scripts/run_signal_auction_regime_filter_walk_forward_sweep.py \
  reports/sierra-signal-log-auction-regime-diagnostics-large-sample.csv \
  reports/sierra-signal-log-auction-regime-filter-walk-forward-holdout1-large-sample.csv \
  --train-date-count 8 \
  --holdout-date-count 1 \
  --minimum-train-trades 4
```

Then run the target-R stack against that selection:

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

Current non-overlapping result: `1` evaluated holdout trade, `1` target hit,
`0` losses, `+221.50` net USD, with `10` auction-skipped holdout candidates for
`-2035.00` net USD.

## Run Auction-Regime Plus Breakeven Stop Report

Manual help needed: **No after the large Sierra export, signal log,
auction-regime diagnostics CSV, and selected-rule CSV exist**.

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

This applies the selected auction-regime guard first, then selects a
replacement target R plus a breakeven-stop trigger on the auction-eligible
training rows. The selected exit pair is evaluated on auction-eligible holdout
rows.

For the non-overlapping holdout-date audit, run the same report against the
holdout `1` selected-rule file:

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

Current result: the overlapping walk-forward has `2` evaluated holdout trades,
`2` target hits, `0` losses, `0` breakeven exits, and `+393.00` net USD. The
non-overlapping audit has `1` evaluated holdout trade, `1` target hit, `0`
losses, `0` breakeven exits, and `+221.50` net USD. This matches the target-R
stack on the held-out rows, so the breakeven stop is not yet proven to add
out-of-sample value.

## Run Auction-Regime Trade-Level Audit

Manual help needed: **No after the large Sierra export, signal log,
auction-regime diagnostics CSV, and selected-rule CSV exist**.

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

For the non-overlapping audit, change the selected-rule and output paths:

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

Use `--stack-type breakeven` plus the breakeven grid to audit the breakeven
stack:

```bash
  --target-r-multiples 0.5,1,1.25,1.5,2,2.5,3,3.5,4,4.5,5 \
  --breakeven-trigger-r-multiples 0.5,0.75,1,1.25,1.5,2,2.5
```

Current trade-level result: the overlapping target-R and breakeven audits each
show `2` evaluated holdout rows but only `1` unique evaluated holdout signal.
That duplicate signal is
`liquidity_sweep_absorption_reversal_ESU26-CME_32971` on `2026-06-17`. The
non-overlapping holdout-1 audit keeps it once at `2.5R` for `+221.50`.

## Run Auction-Regime Stack Acceptance Gate

Manual help needed: **No after the trade-level audit CSV exists**.

```bash
.venv/bin/python scripts/check_auction_regime_stack_acceptance.py \
  --audit reports/sierra-signal-log-auction-regime-target-r-trade-audit-holdout1-large-sample.csv \
  --report reports/sierra-signal-log-auction-regime-target-r-acceptance-holdout1-large-sample.md
```

For the breakeven stack:

```bash
.venv/bin/python scripts/check_auction_regime_stack_acceptance.py \
  --audit reports/sierra-signal-log-auction-regime-breakeven-trade-audit-holdout1-large-sample.csv \
  --report reports/sierra-signal-log-auction-regime-breakeven-acceptance-holdout1-large-sample.md
```

Current result: `FAIL`. The holdout-1 target-R and breakeven audits each have
`1` unique evaluated holdout signal across `1` trade date, below the configured
minimums of `30` unique signals and `15` trade dates. The single winning signal
also contributes `100.00%` of positive unique holdout net, above the configured
maximum of `25.00%`.

## Run Quality Plus Health Gate Walk-Forward

Manual help needed: **No after the quality diagnostics CSV exists**.

```bash
.venv/bin/python scripts/run_signal_quality_health_gate_walk_forward_sweep.py \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  reports/sierra-signal-log-quality-health-gate-walk-forward-large-sample.csv \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-train-accepted-trades 4
```

This jointly selects an entry-quality filter and a closed-trade health gate on
each training window, then applies the selected pair to the next holdout dates.

## Run News Exclusion Annotation

Manual help needed: **Yes before running this workflow**, because the scheduled
news event CSV must be populated from an official economic calendar. Use New
York local time, matching the Sierra signal log and exports.

Template:

`config/research/news_events.template.csv`

Working event calendar path:

`data/processed/AxonTrade_US_news_events.csv`

Required CSV header:

```text
schema_version,event_id,event_time,event_name,currency,impact,blackout_before_minutes,blackout_after_minutes,source,notes
```

Example event row format:

```text
1,us-cpi-2026-06,2026-06-10 08:30:00,CPI,USD,high,15,30,official calendar,New York time
```

Keep each event on one physical CSV line. Wrapped URLs or notes create malformed
rows and the annotation script will reject them before parsing timestamps.

After the event calendar exists, annotate diagnostics with:

```bash
.venv/bin/python scripts/run_signal_news_exclusion.py \
  reports/sierra-signal-log-quality-diagnostics-large-sample.csv \
  data/processed/AxonTrade_US_news_events.csv \
  reports/sierra-signal-log-quality-diagnostics-news-annotated-large-sample.csv \
  --timestamp-field entry_time \
  --default-blackout-before-minutes 10 \
  --default-blackout-after-minutes 15
```

Then run quality filters with news-blackout rows excluded:

```bash
.venv/bin/python scripts/run_signal_quality_filter_walk_forward_sweep.py \
  reports/sierra-signal-log-quality-diagnostics-news-annotated-large-sample.csv \
  reports/sierra-signal-log-quality-filter-news-excluded-walk-forward-large-sample.csv \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-train-trades 4 \
  --max-original-reward-risks 1.5,2,2.5,3,3.5,4,999 \
  --min-minutes-after-rth-open 0,60,90 \
  --max-minutes-after-rth-open 120,150,180,240,390 \
  --max-sweep-abs-deltas 3,5,10,20,999999 \
  --direction-filters all,long,short \
  --exclude-news-blackout
```

The `--exclude-news-blackout` flag intentionally fails unless the input rows
already include `in_news_blackout`, which prevents accidental unannotated tests
from being treated as news-filtered.

Large-sample event calendar check:

- Input events: BLS Employment Situation `2026-06-05 08:30`, BLS CPI
  `2026-06-10 08:30`, BLS PPI `2026-06-11 08:30`, Census Retail Sales
  `2026-06-17 08:30`, FOMC statement `2026-06-17 14:00`, all New York time.
- Annotation output:
  `reports/sierra-signal-log-quality-diagnostics-news-annotated-large-sample.csv`
- Result: `23` signal rows annotated, `0` rows inside the configured news
  blackout windows.
- News-excluded walk-forward output:
  `reports/sierra-signal-log-quality-filter-news-excluded-walk-forward-large-sample.csv`
- Result: unchanged from the unfiltered quality-filter walk-forward run:
  `6` holdout windows, `4` holdout trades, `-1064.00` net USD.

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

## Run Scaled Scalp Sweep

Manual help needed: **No after the fresh export and signal log exist**.

```bash
.venv/bin/python scripts/run_signal_scaled_scalp_sweep.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-scaled-scalp-sweep-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --first-target-points 0.75,1,1.25,1.5 \
  --stop-points 1.5,2,2.5,3 \
  --runner-target-points 1.5,2,2.5,3,4,5 \
  --runner-stop-modes breakeven,initial \
  --direction-filters all,long,short
```

This keeps the logged entries but replaces the original target/stop pair with
a two-contract scalp: one contract exits at a fixed point target, and the
second contract uses a fixed runner target with either the original fixed stop
or a breakeven stop after the first target is touched. Same-bar ambiguity is
handled conservatively by choosing the stop first.

## Run Scaled Scalp Walk-Forward

Manual help needed: **No after the fresh export and signal log exist**.

```bash
.venv/bin/python scripts/run_signal_scaled_scalp_walk_forward_sweep.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  data/processed/AxonTrade_ES_overlay_signal_log_large_sample.csv \
  reports/sierra-signal-log-scaled-scalp-walk-forward-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --train-date-count 8 \
  --holdout-date-count 2 \
  --minimum-train-trades 4 \
  --first-target-points 0.75,1,1.25,1.5 \
  --stop-points 1.5,2,2.5,3 \
  --runner-target-points 1.5,2,2.5,3,4,5 \
  --runner-stop-modes breakeven,initial \
  --direction-filters all,long,short
```

For a non-overlapping holdout-date read, use `--holdout-date-count 1` and
write to:

`reports/sierra-signal-log-scaled-scalp-walk-forward-holdout1-large-sample.csv`

## Run Synthetic Scalp Entry Baselines

Manual help needed: **No after the fresh export exists**.

```bash
.venv/bin/python scripts/run_signal_scalp_entry_baselines.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  reports/sierra-signal-log-scalp-entry-baselines-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth
```

This generates random, VWAP-extension fade, short impulse fade, and short
impulse continuation entries from the exported Sierra bars, then tests the
same two-contract scaled scalp exit grid. It is a baseline for whether the
logged setup is better or worse than simple synthetic entries.

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

News-annotated diagnostics, once a news calendar exists:

`reports/sierra-signal-log-quality-diagnostics-news-annotated-large-sample.csv`

Context diagnostics:

`reports/sierra-signal-log-context-diagnostics-large-sample.csv`

Context filter sweep:

`reports/sierra-signal-log-context-filter-sweep-large-sample.csv`

Context filter walk-forward:

`reports/sierra-signal-log-context-filter-walk-forward-large-sample.csv`

Health gate sweep:

`reports/sierra-signal-log-health-gate-sweep-large-sample.csv`

Health gate walk-forward:

`reports/sierra-signal-log-health-gate-walk-forward-large-sample.csv`

Quality plus health gate walk-forward:

`reports/sierra-signal-log-quality-health-gate-walk-forward-large-sample.csv`

Quality filter sweep:

`reports/sierra-signal-log-quality-filter-sweep-large-sample.csv`

Quality filter walk-forward:

`reports/sierra-signal-log-quality-filter-walk-forward-large-sample.csv`

Structure filter sweep:

`reports/sierra-signal-log-structure-filter-sweep-large-sample.csv`

Structure filter walk-forward:

`reports/sierra-signal-log-structure-filter-walk-forward-large-sample.csv`

Target R sweep:

`reports/sierra-signal-log-target-r-sweep-large-sample.csv`

Target R walk-forward:

`reports/sierra-signal-log-target-r-walk-forward-large-sample.csv`

Breakeven stop sweep:

`reports/sierra-signal-log-breakeven-stop-sweep-large-sample.csv`

Breakeven stop walk-forward:

`reports/sierra-signal-log-breakeven-stop-walk-forward-large-sample.csv`

Scaled scalp sweep:

`reports/sierra-signal-log-scaled-scalp-sweep-large-sample.csv`

Scaled scalp walk-forward:

`reports/sierra-signal-log-scaled-scalp-walk-forward-large-sample.csv`

Scaled scalp non-overlapping holdout-1 walk-forward:

`reports/sierra-signal-log-scaled-scalp-walk-forward-holdout1-large-sample.csv`

Synthetic scalp entry baselines:

`reports/sierra-signal-log-scalp-entry-baselines-large-sample.csv`

Synthetic scalp entry baseline report:

`reports/sierra-signal-log-scalp-entry-baselines-large-sample.md`

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

Structure filter aggregate sweep:

| Direction | Max Original RR | Minutes After Open | Max Sweep Abs Delta | Max Bars After Sweep | Min Sweep Aggression Ratio | Min Confirmation Edge Close | Trades | Target Hits | Losses | Net USD |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `all` | `3.5` | `0-120` | `3` | `5` | `1` | `0.55` | `6` | `5` | `1` | `1691.50` |

Rolling structure filter walk-forward validation:

- train date count: `8`
- holdout date count: `2`
- minimum selected train trades: `4`
- holdout windows: `6`
- selected holdout trades: `3`
- selected holdout target hits: `0`
- selected holdout losses: `3`
- selected holdout net USD: `-1010.50`

Interpretation: the structure filters did not solve the problem. The best
aggregate row is still the same early-sample pocket as the basic quality
filter, and the walk-forward selector often kept `max_bars_after_sweep=5` and
`min_confirmation_edge_close=0.55`, meaning stricter sweep timing and close
location did not consistently win. The setup likely needs level-specific
absorption evidence, not more bar-level proxy thresholds.

Scaled two-contract scalp result:

- grid: first target `0.75,1,1.25,1.5` points; stop `1.5,2,2.5,3` points;
  runner target `1.5,2,2.5,3,4,5` points; runner stop modes
  `breakeven,initial`
- best aggregate row: `long`, first target `1.5`, stop `2.5`, runner target
  `5`, runner stop `initial`, `12` trades, `+166.00` net USD
- best aggregate all-direction row: first target `1.5`, stop `1.5`, runner
  target `5`, runner stop `initial`, `23` trades, `-336.00` net USD
- rolling walk-forward: `6` holdout windows, `8` holdout trades, `8` full
  stops before the first target, `0` positive trades, `-2056.00` net USD
- non-overlapping holdout-1 walk-forward: `7` holdout windows, `5` holdout
  trades, `5` full stops before the first target, `0` positive trades,
  `-1235.00` net USD

Interpretation: the fixed two-contract scalp is not validated on the current
sample. The only positive result is a small long-only aggregate pocket, and the
chronological holdouts show that selected trades mostly failed before even
reaching the first scale-out. This points back to entry filtering or better
level-specific absorption evidence, not more aggressive stop/target tuning.

Synthetic scalp entry baseline result:

- generated entries: `4869` across random, VWAP-extension fade, impulse fade,
  and impulse continuation families
- entry window: `09:45` to `15:45` New York time
- best synthetic family: `impulse_continue_3bar_1.5pt`, `433` trades,
  `-9881.00` net USD, `-22.82` average net per trade
- random baseline: `550` trades, `-25500.00` net USD, `-46.36` average net per
  trade

Interpretation: random entries were not better after current ES two-contract
cost assumptions. The least bad simple baseline was short-term impulse
continuation, but it was still negative.

Context diagnostic observations:

- context rows: `23`
- lookback bars per row: `50`
- `sweep_abs_delta_to_average_abs_delta <= 1`: `15` trades, `6` target hits,
  net `478.75`
- `target_distance_to_average_bar_range <= 20`: `11` trades, `5` target hits,
  net `399.00`
- `risk_to_average_bar_range <= 8`: `18` trades, `4` target hits, net
  `-1638.00`
- `entry_volume_to_average_volume >= 1`: `10` trades, `3` target hits, net
  `-135.00`

Interpretation: normalized context is now available, but the first scan still
does not show a standalone filter strong enough to promote into another
walk-forward optimizer. The positive rows are mostly the same lower target/R
and earlier-session subset already seen in quality diagnostics.

Context filter aggregate sweep:

| Direction | Max Original RR | Minutes After Open | Max Sweep Abs Delta | Max Sweep/Avg Abs Delta | Min Volume/Avg Volume | Min Trades/Avg Trades | Trades | Target Hits | Losses | Net USD |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `all` | `3.5` | `0-120` | `3` | `1` | `0` | `0` | `6` | `5` | `1` | `1691.50` |

Rolling context filter walk-forward validation:

- train date count: `8`
- holdout date count: `2`
- minimum selected train trades: `4`
- holdout windows: `6`
- selected holdout trades: `4`
- selected holdout target hits: `0`
- selected holdout losses: `4`
- selected holdout net USD: `-1064.00`

Interpretation: the context optimizer found the same chronological failure as
the quality-filter optimizer. The selected train filters usually kept
`min_entry_volume_to_average_volume=0` and
`min_entry_trades_to_average_trades=0`, so this sample does not support a
simple "only trade above-average activity" rule. Static context filters are not
enough; the next bot-control candidate is a strategy health/disable gate that
stops trading after the setup family enters a losing regime.

Health gate aggregate sweep:

| Max Daily Losses | Daily Stop USD | Max Consecutive Losses | Consecutive Pause Dates | Max Drawdown USD | Drawdown Pause Dates | Accepted | Skipped | Target Hits | Losses | Net USD | Skipped Net USD |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `1` | `150` | `2` | `2` | `500` | `3` | `12` | `11` | `6` | `6` | `833.00` | `-1713.50` |

Rolling health gate walk-forward validation:

- train date count: `8`
- holdout date count: `2`
- minimum selected train accepted trades: `4`
- holdout windows: `6`
- selected holdout accepted trades: `7`
- selected holdout skipped trades: `12`
- selected holdout target hits: `0`
- selected holdout losses: `7`
- selected holdout net USD: `-1237.00`
- skipped holdout net USD: `-2654.50`

Interpretation: health gates are useful damage controls, not a validated edge.
They skipped only losing holdout candidates in this sample, which is promising
for risk containment, but the trades still accepted in holdout were all losers.
Do not enable live automation from this result. The next research question is
whether the health gate should be combined with the quality/context filters, or
whether the setup family needs a stricter entry definition before any bot
execution work.

Quality plus health gate walk-forward validation:

- train date count: `8`
- holdout date count: `2`
- minimum selected train accepted trades: `4`
- holdout windows: `6`
- selected holdout accepted trades: `3`
- selected holdout skipped trades: `1`
- selected holdout target hits: `0`
- selected holdout losses: `3`
- selected holdout net USD: `-935.50`
- skipped holdout net USD: `-128.50`

Interpretation: combining the entry-quality filter with health gates reduces
exposure more than either layer alone, but the selected holdout trades are still
all losers. This is not a validation. The current setup definition likely needs
stricter market-structure or level-specific absorption criteria before any
execution-bot work.

Scheduled-news exclusion status:

- implementation exists
- template CSV exists
- local official-event sample exists at
  `data/processed/AxonTrade_US_news_events.csv`
- annotated output:
  `reports/sierra-signal-log-quality-diagnostics-news-annotated-large-sample.csv`
- configured events removed `0` of `23` candidate rows from this sample
- news-excluded quality-filter walk-forward remained unchanged: `4` selected
  holdout trades, `0` target hits, `4` losses, `-1064.00` net USD
- manual help needed: **No for the current checked sample**; **Yes for future
  samples** if the date range includes new official event rows not yet in the
  local event CSV

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

Volume-at-price absorption diagnostics:

- VAP export:
  `C:\SierraChart\Data\AxonTrade_ES_VolumeAtPriceExport.txt`
- diagnostics output:
  `reports/sierra-signal-log-vap-absorption-diagnostics-large-sample.csv`
- evaluated trades: `23`
- VAP covered trades: `23`
- default level-absorption passes: `23`
- target hits: `7`
- losses: `16`
- net USD: `-880.50`
- swept-zone volume min/median/max: `1` / `6` / `205`

Interpretation: the refreshed VAP export is aligned with the NY large-sample
signal log. However, the default swept-zone aggression rule accepts every
evaluated candidate, because the setup definition already requires sweep-side
aggression. Level-specific VAP confirms that the sweep happened; it does not
separate winning traps from losing continuation attempts.

VAP threshold train/holdout validation:

| Sample | Direction | Min Zone Ratio | Min Zone Volume | Trades | Target Hits | Losses | Net USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `train` | `all` | `1` | `0` | `12` | `7` | `5` | `1283.00` |
| `holdout` | `all` | `1` | `0` | `11` | `0` | `11` | `-2163.50` |

VAP threshold rolling walk-forward validation:

- train date count: `8`
- holdout date count: `2`
- minimum selected train trades: `4`
- holdout windows: `6`
- selected holdout trades: `11`
- selected holdout target hits: `0`
- selected holdout losses: `11`
- selected holdout net USD: `-2501.00`

Interpretation: swept-zone VAP thresholds do not validate on the current large
sample. Tightening ratio or volume either preserves the losing holdout trades or
selects no trades. Do not promote VAP aggression/volume thresholds to Sierra
overlay defaults from this result.

VAP trap filter validation:

This tests a stricter interpretation of absorption: enough sweep-side
aggression, limited total swept-zone volume, limited number of swept-zone price
levels, and enough volume concentrated at the exact swept extreme.

Train/holdout selected rule:

| Sample | Direction | Min Ratio | Max Zone Volume | Max Zone Levels | Min Extreme Share | Trades | Target Hits | Losses | Net USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `train` | `all` | `1` | `20` | `5` | `0.25` | `8` | `6` | `2` | `1953.25` |
| `holdout` | `all` | `1` | `20` | `5` | `0.25` | `5` | `0` | `5` | `-1130.00` |

VAP trap filter rolling walk-forward validation:

- train date count: `8`
- holdout date count: `2`
- minimum selected train trades: `4`
- holdout windows: `6`
- selected holdout trades: `5`
- selected holdout target hits: `0`
- selected holdout losses: `5`
- selected holdout net USD: `-1205.00`

Interpretation: the trap filter is directionally better as damage reduction
than the broad VAP threshold filter, but it is still not an edge. It selected
fewer holdout trades and every selected holdout trade lost. Do not automate from
this result.

Auction-regime filter validation:

This tests whether failed fades are associated with directional session stretch:
wider session range, entry deeper at the fade edge, larger distance from VWAP,
and larger distance from the session open.

Diagnostic separation:

| Field | Winner Median | Loser Median |
| --- | ---: | ---: |
| Session range points | `33.50` | `48.25` |
| Fade edge score | `0.65079365` | `0.80310881` |
| VWAP stretch points | `4.05` | `12.57` |
| Open stretch points | `5.00` | `16.75` |
| Original reward/risk | `1.74` | `4.20` |

Train/holdout selected rule:

| Sample | Direction | Max RR | Max Session Range | Max Fade Edge | Max VWAP Stretch | Max Open Stretch | Trades | Target Hits | Losses | Net USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `train` | `all` | `3.5` | `50` | `1` | `10` | `20` | `9` | `7` | `2` | `2018.50` |
| `holdout` | `all` | `3.5` | `50` | `1` | `10` | `20` | `2` | `0` | `2` | `-282.00` |

Auction-regime rolling walk-forward validation:

- train date count: `8`
- holdout date count: `2`
- minimum selected train trades: `4`
- holdout windows: `6`
- selected holdout trades: `2`
- selected holdout target hits: `0`
- selected holdout losses: `2`
- selected holdout net USD: `-257.00`

Auction-regime guard accepted/skipped holdout result:

| Split | Accepted Trades | Accepted Net USD | Skipped Trades | Skipped Net USD |
| --- | ---: | ---: | ---: | ---: |
| Train/holdout | `2` | `-282.00` | `9` | `-1881.50` |
| Rolling walk-forward | `2` | `-257.00` | `17` | `-3634.50` |

Interpretation: auction-regime filters explain much of the later failure mode
and avoided most losing holdout candidates, but they still did not produce a
validated entry edge. Treat this as a future no-trade regime guard candidate,
not as permission to automate entries.

Implementation note: Sierra exports sub-second bar timestamps, while the signal
log stores whole-second bar times. Outcome preflight therefore validates matching
entries by same-day `bar_index` first, then falls back to nearest timestamp.
