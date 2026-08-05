# Tradeify 50K NinjaTrader Strategy Direction

Status date: `2026-08-05`

Status: strategy research only. No NinjaTrader code or live-routing approval is
included in this branch.

## Decision

Use `MGC` as the primary instrument and freeze one new research lead:

`AxonTrade Tradeify MGC Select v1`

It combines the frozen MGC breakout entry, a fixed `8 / 15` target/stop, a
transparent logistic quality gate, and account-drawdown sizing capped at
`3 MGC`. It reached the requested high-win/low-DD/high-PF shape and passed the
programmed account gates.

Its status is **provisional**, because an earlier model iteration exposed the
final-period behavior before the cleaned model was frozen. Independent
NinjaTrader Playback/replay evidence is mandatory before implementation
approval.

`AxonTrade Tradeify MGC Core v1`, fixed `1 MGC` with `25 / 15 / BE+20`, remains
the non-rejected safety fallback. Neither candidate is a profit guarantee or
live authorization.

Machine-readable Select v1 snapshot:
[`config/research/tradeify_mgc_select_v1.yaml`](../config/research/tradeify_mgc_select_v1.yaml).

## Why MGC

| Instrument | Local Evidence | Tradeify Fit | Decision |
| --- | --- | --- | --- |
| `MGC` | 813,388 one-minute rows, 717 raw trade-date labels, 593 eligible active dates, 343 sequenced core trades | One contract risks about `$154` at the initial stop after base friction; strongest path stability | Primary |
| `MNQ` | 67,300 three-minute rows, 507 dates; several profitable historical families | Granular sizing, but the Tradeify adaptations failed final path stress | Research backup |
| `MES` | Existing Sierra mechanics are validated | Lower local PF and prior historical-data/provider problems | Do not lead the NinjaTrader pivot |
| `NQ/ES/GC` | No equivalent local order-flow validation for this strategy | One contract is too coarse for a fresh `$2,000` trailing-drawdown account | Excluded at account day zero |

MGC was selected from local evidence, not from a claim that gold is universally
the best automated market. A different instrument needs comparable data and
must beat this candidate under the same gates before replacing it.

## Tradeify Snapshot

The official rule snapshot is stored in
[`config/firms/tradeify_50k_select.yaml`](../config/firms/tradeify_50k_select.yaml).
Recheck the rules immediately before implementation or account use.

- evaluation target: `$3,000`;
- end-of-day trailing maximum drawdown: `$2,000`, enforced in real time;
- firm daily loss limit: none during evaluation;
- consistency: best winning day must be at most `40%` of total profit;
- minimum trading days: `3`;
- evaluation size limit: `4` minis or `40` micros;
- all positions must be flat before `16:45 America/New_York`;
- internal strategy flatten: `16:30 America/New_York`;
- automated strategies are allowed only within Tradeify's ownership and
  activity restrictions.

Sources: [Select evaluation rules](https://help.tradeify.co/en/articles/12853921-select-evaluation-accounts),
[trailing drawdown rules](https://help.tradeify.co/en/articles/10495897-rules-trailing-max-drawdowns),
[trader guidelines](https://help.tradeify.co/en/articles/10468318-guidelines-for-traders),
[permitted trading times](https://help.tradeify.co/en/articles/10495876-rules-permitted-times-to-trade),
and [commission schedule](https://help.tradeify.co/en/articles/10468315-trading-commission-fees).

## Frozen Signal

Data series and clock:

- instrument: front/current `MGC` contract;
- base series: `1 Minute`;
- research/session timezone: `America/New_York`;
- setup window: `08:20:00` through `10:30:00` inclusive;
- eligible weekdays: Monday, Tuesday, Friday;
- maximum one submitted trade per session date.

Long entry, evaluated on a completed one-minute bar:

1. The previous close is at or below the highest high of the preceding `10`
   completed bars.
2. The signal-bar close crosses above that ten-bar high.
3. Signal-bar close is at or above session VWAP.
4. Signal-bar close location is at least `0.45`, where
   `(close - low) / (high - low)` is clamped to `[0, 1]`.
5. Signal-bar bid/ask delta is nonnegative and its absolute value is at most
   `125`.

Short entry is the exact inverse: close crosses below the preceding ten-bar
low, closes at or below VWAP, close location is at most `0.55`, and delta is
nonpositive with absolute value at most `125`.

Submit a market entry only after the completed signal bar. Research charges two
total slippage ticks, so a future implementation must not assume a fill at the
unadjusted signal close.

## Select v1 Quality Gate

The common breakout signal is accepted only when this frozen logistic model
returns probability `>= 0.70`:

`p = sigmoid(intercept + sum(coefficient * (x - mean) / scale))`

Intercept: `0.81363911`.

| Input available at signal close | Coefficient | Mean | Scale |
| --- | ---: | ---: | ---: |
| Long direction (`1` long, `0` short) | `0.05837870` | `0.58988764` | `0.49185385` |
| Monday (`1/0`) | `0.12634850` | `0.33707865` | `0.47271200` |
| Tuesday (`1/0`; Friday is baseline) | `-0.14564598` | `0.33707865` | `0.47271200` |
| Minute of day | `-0.25028284` | `526.91011236` | `18.98588503` |
| Directional close location | `0.30729904` | `0.82950953` | `0.13580856` |
| Absolute signal-bar delta | `0.28633956` | `58.08426966` | `31.17923322` |
| Signal-bar high-low range | `0.66241121` | `1.96797753` | `1.42447994` |
| Direction-aligned signal-bar body | `-0.81888235` | `1.32977528` | `0.89408855` |
| Absolute close-to-VWAP distance | `0.37597185` | `7.72078652` | `7.39858516` |
| Session range through signal bar | `0.33366238` | `8.92696629` | `6.42255093` |
| Direction-aligned five-bar move | `0.17288455` | `2.99775281` | `1.86167603` |
| Direction-aligned five-bar delta | `-0.39413980` | `118.51685393` | `107.09096337` |
| Direction-aligned five-bar VWAP slope | `-0.42505455` | `0.09269663` | `0.13575642` |
| Signal volume / prior-20-bar mean volume | `0.04497441` | `1.69972387` | `1.19482169` |

Direction alignment multiplies by `+1` for long and `-1` for short. The
five-bar move and VWAP slope compare the signal bar with bar `index - 5`; the
five-bar delta sums the signal bar and previous four bars. Prior-20 mean volume
excludes the signal bar. Do not retrain or recalculate these constants during
an evaluation.

## Select v1 Management

- target: `8.0` MGC points;
- initial stop: `15.0` MGC points;
- no break-even move, trailing stop, partial exit, or time-based target change;
- if stop and target are both reachable in the same historical bar, score the
  stop first;
- flatten any open position at `16:30 America/New_York`;
- do not re-enter on the same session date.

Position quantity is account-state dependent:

| Drawdown from current EOD high-water mark | Quantity |
| --- | ---: |
| `>= -$500` | `3 MGC` |
| `< -$500` and `>= -$1,000` | `2 MGC` |
| `< -$1,000` | `1 MGC` |

Use this adaptive policy only during evaluation and before the funded
drawdown floor locks. After the funded lock objective is confirmed at end of
day, revert to fixed `1 MGC`. Increasing post-lock size or projecting payouts
requires independent NinjaTrader evidence and separate portfolio research.

Before every entry, calculate the distance from current equity to the active
Tradeify drawdown floor. Reduce quantity until the complete `15`-point stop,
base friction, and a `$100` reserve fit. Reject the trade if even `1 MGC` does
not fit. Never increase size to recover a drawdown, average down, martingale,
or run a second strategy on the same account/instrument.

## Select v1 Result

The current-cost model uses the published `$2.12` MGC round-trip fee plus two
total slippage ticks. Stress uses six total slippage ticks. Strategy statistics
below use fixed `1 MGC`; account simulations apply the `3 -> 2 -> 1` policy.

| Sample | Trades | Net | PF | Win | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full base | 198 | `$4,787.24` | `1.74` | `76.3%` | `-$542.96` |
| Full six-tick stress | 198 | `$3,995.24` | `1.60` | `75.8%` | `-$574.96` |
| Final-period base | 68 | `$1,709.84` | `1.74` | `77.9%` | `-$542.96` |
| Final-period six-tick stress | 68 | `$1,437.84` | `1.61` | `77.9%` | `-$574.96` |

Frequency is about `1.65` accepted trades per week.

Account-path results for the selected sizing policy:

- development historical 365-day pass: `98.9%`; breach `0.0%`; risk lock
  `0.0%`;
- development 260-session block bootstrap: pass `66.9%`; breach `0.0%`; risk
  lock `4.2%`;
- full historical 365-day pass: `99.4%`; median successful duration `215`
  calendar days;
- final-period block bootstrap: pass `80.5%`; breach `0.0%`; risk lock `8.2%`.
- historical funded `+$2,100` drawdown-lock objective: `100.0%` pass, `0.0%`
  breach/risk lock, median `126` calendar days.

The lack of modeled breaches depends on the risk-reserve lock. A risk lock
preserves the account but can leave the evaluation unable to progress. These
are resampled historical outcomes, not guaranteed future probabilities.

The final-period process is no longer independent because an earlier model
iteration was inspected before duplicate predictors were removed. The cleaned
model passes the numerical gates, but its formal status remains
`PROVISIONAL_GATES_PASS_REQUIRES_INDEPENDENT_REPLAY`.

Full result:
[`reports/tradeify-50k-mgc-high-win-quality-filter.md`](../reports/tradeify-50k-mgc-high-win-quality-filter.md).

## Core v1 Fallback

If Select v1 fails independent parity/replay, retain the simpler frozen MGC
Core rule: fixed `1 MGC`, `25`-point target, `15`-point stop, move to breakeven
after `+20`, one trade per date.

| Sample | Trades | Net | PF | Win | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full base | 343 | `$12,570.84` | `1.71` | `55.1%` | `-$696.08` |
| Full six-tick stress | 343 | `$11,198.84` | `1.61` | `53.1%` | `-$732.08` |

Core historical rolling 365-day evaluations passed `91.9%`, with median
successful duration `236` calendar days. It is non-rejected but does not meet
the requested high-win profile.

Full fallback result:
[`reports/tradeify-50k-mgc-strategy-research.md`](../reports/tradeify-50k-mgc-strategy-research.md).

Both strategies are slow by quick-evaluation standards. Budget for several
months, not several days.

## Rejected Alternatives

- Fresh MNQ opening-drive, prior-session sweep, gap-fade, and VWAP-pullback
  families did not survive the final chronological holdout.
- The Tradeify MNQ VWAP/delta adaptation reached `76.8%` wins and `1.69` PF,
  but its shuffled P95 drawdown was about `-$2,845`; it was rejected.
- Unconditional MGC fixed `2` and `3` contract policies passed faster but had
  excessive bootstrap risk locks.
- Short-target MGC management reached high win rates but could not keep
  development PF at `1.50` without a filter.
- The first `8/15` quality-filter iteration contained duplicate predictors and
  selected an account policy with excessive final risk locks. Its results are
  superseded by the cleaned provisional Select v1 model, not counted as
  independent confirmation.

Research reports:

- [`reports/tradeify-50k-mnq-strategy-research.md`](../reports/tradeify-50k-mnq-strategy-research.md)
- [`reports/tradeify-50k-vwap-delta-adaptation.md`](../reports/tradeify-50k-vwap-delta-adaptation.md)
- [`reports/tradeify-50k-mgc-high-win-management.md`](../reports/tradeify-50k-mgc-high-win-management.md)
- [`reports/tradeify-50k-mgc-high-win-quality-filter.md`](../reports/tradeify-50k-mgc-high-win-quality-filter.md)

## NinjaTrader Contract

Do not build the NinjaTrader strategy until a Windows/NinjaTrader workspace is
available. The implementation must then satisfy all of these gates:

1. Verify that the Tradeify-provided NinjaTrader license exposes Order Flow+.
   NinjaTrader documents the built-in volumetric/order-flow suite as a lifetime
   license feature. If it is unavailable, calculate the same per-bar BidAsk
   delta from stamped ticks in custom code; do not silently substitute UpDown
   Tick delta.
2. Use a one-minute BidAsk volumetric series, or an equivalent one-minute
   series with reproducible per-bar bid/ask delta.
3. Require historical bid/ask-stamped tick data. NinjaTrader documents that
   historical BidAsk cumulative delta requires it.
4. Keep entry logic on completed bars and add an execution series only for fill
   resolution; do not silently change the signal timeframe.
5. Reproduce all `343` Sierra-derived Core outcomes and the frozen Select v1
   set of `198` accepted entries by timestamp before trusting Strategy Analyzer
   totals.
6. Run high-fill-resolution historical tests, then Playback/Market Replay.
   NinjaTrader explicitly warns that Tick Replay is not intended to provide
   live-equivalent Strategy Analyzer backtests.
7. Test disconnection, rejected order, partial fill, duplicate callback,
   restart/recovery, stop modification, session rollover, and forced-flatten
   behavior in simulation.
8. Keep live routing disabled until historical parity, Playback, simulation,
   and controlled staging are each signed off.

NinjaTrader references:
[Order Flow+ entitlement](https://ninjatrader.com/support/helpguides/nt8/order_flow_plus.htm),
[Order Flow Volumetric Bars](https://ninjatrader.com/support/helpGuides/nt8/order_flow_volumetric_bars2.htm),
[AddVolumetric](https://ninjatrader.com/support/helpguides/nt8/addvolumetric.htm),
[Order Flow Cumulative Delta](https://ninjatrader.com/support/helpGuides/nt8/order_flow_cumulative_delta.htm),
[Tick Replay](https://ninjatrader.com/support/helpguides/nt8/tick_replay.htm),
and [Playback](https://ninjatrader.com/support/helpguides/nt8/playback.htm).

## Next Gate

When Windows and NinjaTrader are available:

1. Install NinjaTrader using the Tradeify/Tradovate connection instructions.
2. Verify Order Flow+ entitlement and that the selected data connection
   provides historical bid/ask tick data for MGC.
3. Export or replay a common date range in both Sierra and NinjaTrader.
4. Compare bars, VWAP, bar delta, signal timestamps, and managed exits.
5. Only after parity, create the NinjaScript strategy in simulation-only mode.

Until then, the strategy is frozen. More tuning on the same export is more
likely to fit history than improve future behavior.
