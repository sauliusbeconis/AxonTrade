# Fresh 480D VWAP Delta Drawdown Control

Status: **next validation candidate, not live-ready**

## Scope

This pass continues from the fresh 480D guard/exit variant research. The export
was produced on `2026-06-30`, but its bars end at `2026-06-29 16:12:00`, so
this is still historical research rather than current-session validation.

Tested entry/guard family:

`vwap_delta_exhaustion_fade_2pt_10d_cl0.5`

Fixed entry-known guard:

`lookback_directional_move_points <= -2.5; session_range_points >= 30; risk_to_average_bar_range <= 1.75`

Generated outputs:

- `reports/sierra-signal-log-scalp-entry-baselines-fresh-480d-vwap-delta-exhaustion-drawdown-control-trade-diagnostics.csv`
- `reports/sierra-signal-log-scalp-entry-baselines-fresh-480d-vwap-delta-exhaustion-drawdown-control-summary.csv`
- `reports/sierra-signal-log-scalp-entry-baselines-fresh-480d-vwap-delta-exhaustion-drawdown-control-walk-forward.csv`
- `reports/sierra-signal-log-scalp-entry-baselines-fresh-480d-vwap-delta-exhaustion-drawdown-control-fixed-health-gates.csv`

## Candidate Rows

| Candidate | Trades | Net USD | Avg/Trade | Profit Factor | Drawdown/Net | Prior Issue |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `6 / 12 / 15 / initial` | `414` | `60277.00` | `145.60` | `1.3807` | `0.1459` | Too few trades |
| `6 / 10 / 12 / initial` | `550` | `55112.50` | `100.20` | `1.2786` | `0.3161` | Drawdown too high |

## Rolling Health Gates

The first pass selected daily/sequence/drawdown health gates on rolling train
windows and applied the selected gate to holdout windows. That optimizer was
not promoted.

For `6 / 12 / 15 / initial`, the gates mostly reduced net and sample size. For
`6 / 10 / 12 / initial`, the gates improved drawdown, but the rolling selection
still reduced the accepted holdout trade count too aggressively.

Best rolling-selection evidence was on `6 / 10 / 12 / initial`:

| Train | Holdout | Step | Base Net | Health Net | Accepted Trades | Drawdown/Net | Negative Window Rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `40` | `5` | `5` | `55016.50` | `52896.00` | `347` | `0.0916` | `0.1667` |
| `40` | `10` | `10` | `55016.50` | `59348.50` | `352` | `0.0816` | `0.1111` |
| `60` | `10` | `10` | `42696.50` | `43816.50` | `303` | `0.1544` | `0.1429` |
| `80` | `10` | `10` | `29232.50` | `30428.50` | `212` | `0.2223` | `0.2000` |

## Fixed Health Gate

The rolling selector repeatedly converged on a simpler fixed health gate:

`daily_loss_limit_usd = 3600; maximum_equity_drawdown_usd = 4000`

Other gates are effectively disabled:

`maximum_daily_losses = 999; maximum_consecutive_losses = 999; consecutive_pause = 0; drawdown_pause = 0`

This is a realized risk control, not an entry signal. It only blocks new trades
after closed accepted trades breach the daily loss or accepted-equity drawdown
threshold.

Fixed full-sample result on `6 / 10 / 12 / initial`:

| Metric | Value |
| --- | ---: |
| Accepted trades | `526` |
| Skipped trades | `24` |
| Net USD | `63080.50` |
| Average/trade | `119.92` |
| Profit factor | `1.3449` |
| Max drawdown USD | `-15172.00` |
| Drawdown/net | `0.2405` |
| Worst day | `2026-03-09`, `-4128.00` |

Fixed-gate robustness:

| Train | Holdout | Step | Base Net | Health Net | Accepted Trades | Avg/Trade | Profit Factor | Drawdown/Net | Negative Window Rate | Worst Window |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `20` | `5` | `5` | `65316.50` | `72464.50` | `439` | `165.07` | `1.5094` | `0.0736` | `0.0455` | `-784.00` |
| `40` | `5` | `5` | `55016.50` | `60736.50` | `368` | `165.04` | `1.5019` | `0.0879` | `0.0556` | `-784.00` |
| `40` | `10` | `10` | `55016.50` | `60736.50` | `368` | `165.04` | `1.5019` | `0.0879` | `0.0000` | `892.00` |
| `60` | `10` | `10` | `42696.50` | `46188.50` | `307` | `150.45` | `1.4465` | `0.1155` | `0.0000` | `892.00` |
| `80` | `10` | `10` | `29232.50` | `32724.50` | `209` | `156.58` | `1.4569` | `0.1631` | `0.0000` | `892.00` |

## Decision

This pass upgrades the `6 / 10 / 12 / initial` row with the fixed
`daily3600_dd4000` health gate into the next validation candidate.

It is not live-ready because the fixed health gate was selected after reviewing
the same historical export. The next required test is a true future export, or
a replay/live-sim sample that starts after `2026-06-30`, with the fixed entry,
guard, exit, and health gate unchanged.
