# Sierra Delta Impulse 3-Min Large Sample Outcomes

This report evaluates the larger Sierra Chart export from
`ESU26-CME[M] 3 Min #2`.

## Sources

- Signal log:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`
- Bar export:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Large.txt`
- Overlay validation:
  `reports/sierra-delta-impulse-overlay-validation.md`
- Live signal report:
  `reports/sierra-delta-impulse-signal-log-live.md`
- Exit sweep:
  `reports/sierra-delta-impulse-3min-large-scaled-exit-sweep.csv`
- Fixed-row robustness:
  `reports/sierra-delta-impulse-3min-large-robustness.md`
- Fixed-row acceptance:
  `reports/sierra-delta-impulse-3min-fixed-row-acceptance.md`
- Context filter walk-forward:
  `reports/sierra-delta-impulse-fixed-row-context-filter-walk-forward.csv`
- One-command pipeline:
  `scripts/run_delta_impulse_fixed_row_pipeline.py`

## Candidate Log

- dates: `2026-03-23` through `2026-06-26`
- RTH dates with candidates: `41`
- candidates: `163`
- rejected rows: `0`
- directions: `95` long, `68` short
- overlay validation: `PASS`, `163` expected, `163` actual, `163` matched
- logged overlay variant: `5 / 10 / 8 / initial`

The logged variant means:

- first target: `5` points
- stop: `10` points
- runner target: `8` points
- runner stop: initial stop

## Current Logged Variant Result

| Metric | Value |
| --- | ---: |
| Trades | 163 |
| First-target hits | 102 |
| Runner targets | 87 |
| Full stops | 57 |
| Runner initial-stop exits | 15 |
| End/no-following exits | 3 |
| Net USD | -15716 |

Direction split:

| Direction | Trades | Net USD |
| --- | ---: | ---: |
| Long | 95 | -7690 |
| Short | 68 | -8026 |

The larger export rejects the fixed `5 / 10 / 8 / initial` row. The sample is
now large enough for the minimum trade-count and date-count gates, and the full
sample is materially negative.

## Exit Sweep

The fixed-row pipeline generated `924` scaled-exit sweep rows.

Best rows by net USD are still negative:

| Direction | First Target | Stop | Runner Target | Runner Stop | Trades | Net USD |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| long | 4 | 8 | 8 | initial | 95 | -2090 |
| long | 4 | 2 | 8 | initial | 95 | -2815 |
| long | 4 | 2 | 10 | initial | 95 | -2815 |
| long | 5 | 2 | 8 | initial | 95 | -2965 |
| long | 5 | 2 | 10 | initial | 95 | -2965 |

Exit tuning alone does not rescue this entry family.

## Context Filter

The normalized context walk-forward was rerun on `163` diagnostics using:

- train window: `20` trade dates
- holdout window: `5` trade dates
- minimum train trades: `20`
- window step: `5` trade dates

Result:

- holdout windows: `4`
- selected holdout trades: `20`
- selected holdout net USD: `-4640`
- unfiltered same-window holdout trades: `111`
- unfiltered same-window holdout net USD: `-7927`

The selector reduced exposure and lost less than the unfiltered same-window
sample, but it still lost money. It is diagnostic only, not validation.

## Acceptance

Acceptance status: **FAIL**.

Failed gates:

- positive holiday-adjusted net;
- positive holiday-adjusted fixed rolling holdout net;
- maximum drawdown-to-net ratio;
- minimum positive nearby parameter rows;
- nonnegative holiday-adjusted short net;
- maximum nonholiday terminal exits.

## Decision

Do not keep optimizing this exact fixed row as a candidate for live or funded
execution. Treat the current result as a rejection of the fixed Delta Impulse
entry/exit family unless a new hypothesis changes the entry condition, context
filter, or execution model and then passes fresh walk-forward validation.
