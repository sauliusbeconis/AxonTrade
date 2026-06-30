# Decision Log

## 2026-06-16: Initialize Phase-0 Foundation

Decision: start AxonTrade as a research-first, simulation-safe futures trading laboratory.

Context:

- Target instruments are ES/MES and NQ/MNQ.
- Sierra Chart ACSIL is used for platform-side visual/logging studies.
- Python is used for offline research and reporting.
- Live order routing is prohibited in the foundation phase.

Consequences:

- Strategy ideas are documented as hypotheses only.
- Account and instrument rules live in YAML.
- The first ACSIL study is indicator-only.
- Manual Sierra Chart verification remains required.

## 2026-06-29: Keep Delta Impulse Fixed Row Research-Only

Decision: keep collecting the Sierra delta-impulse `5 / 10 / 8 / initial`
variant, but do not promote it to live order routing.

Context:

- The larger 78-trade sample is positive in-sample at `3104` net USD.
- Rolling walk-forward selection is still negative.
- The fixed-row robustness check shows dependence on the last few dates, a
  narrow parameter shelf, holiday/early-close handling, and weak shorts.

Consequences:

- The current Sierra overlay can continue logging candidates.
- Holiday/early-close flags are required before acceptance testing.
- The next validation step is fixed-row holdout/walk-forward reporting, not a
  live execution change.

## 2026-06-29: Reject Delta Impulse Fixed Row After Expanded Export

Decision: reject the Sierra delta-impulse `5 / 10 / 8 / initial` fixed row as
a current strategy candidate.

Context:

- The expanded Sierra export validates `163` overlay candidates across `41`
  trade dates from `2026-03-23` through `2026-06-26`.
- Overlay validation passes exactly: `163` expected, `163` actual, `163`
  matched.
- The fixed row produces `-15716` net USD.
- The full exit sweep has no positive row; the best row is still negative.
- The normalized context walk-forward loses `-4640` on selected holdout trades.
- News exclusion removes one losing trade but leaves the result strongly
  negative.

Consequences:

- Do not keep optimizing this exact fixed row as a live or funded candidate.
- Further Delta Impulse work requires a changed hypothesis, not only exit
  parameter tuning.
- Any new variant must pass fresh overlay validation, cost/slippage checks,
  context diagnostics, and chronological walk-forward validation.

## 2026-06-29: Reject Simple Delta Impulse Fade Inversion

Decision: reject a simple inverted Delta Impulse fade as a current strategy
candidate.

Context:

- The inverted test flips every logged Delta Impulse candidate direction and
  keeps the same entry bar.
- In-sample sweeps produce positive rows, led by an inverted long-only
  `5 / 10 / 15 / initial` row at `4849` net USD.
- Rolling walk-forward remains negative: `100` selected holdout trades for
  `-4512.50` net USD.
- The first holdout window is positive, but the next three selected windows are
  negative.

Update after the continuous-contract 240D export:

- Logged continuation direction stayed deeply negative: `467` selected holdout
  trades for `-58781.50` USD.
- Inverted/fade direction was less bad but still negative: `437` selected
  holdout trades for `-13209` USD.
- The best inverted full-sample sweep row was also negative: long-only
  `5 / 8 / 15 / initial`, `426` trades, `-1482` USD.
- This invalidates the earlier small-sample positive in-sample inversion row as
  insufficient evidence.

Consequences:

- Do not promote simple "take the opposite side" logic.
- The failed continuation signal may contain information, but it needs a
  materially different context filter before it is useful.
- Further Delta Impulse research should focus on auction regime, liquidity
  sweep, or exhaustion context rather than raw direction inversion.

## 2026-06-29: Keep Delta Impulse Context Filtering Active

Decision: keep normalized context filtering for Delta Impulse as an active
research direction, but do not promote the fixed row or the first regime grid.

Context:

- The refreshed expanded-sample context diagnostics still cover `163` fixed-row
  outcomes across `41` trade dates.
- The `20x5` default net selector reduces same-window holdout exposure to `13`
  trades and improves selected net by `5736` USD versus unfiltered holdouts, but
  it remains negative at `-2191` USD.
- The old-style `8x2` non-overlapping selector is the strongest structural
  result: `64` selected holdout trades for `-1198` USD versus `141` unfiltered
  holdout trades for `-12862` USD.
- That improves average holdout result from `-91.22` USD/trade to `-18.72`
  USD/trade while taking `45.4%` of same-window holdout trades.
- The first broad regime grid using session edge, opening-range breakout,
  lookback efficiency, choppiness, and session-volume thresholds makes results
  worse in both `20x5` and `8x2` walk-forward shapes.

Consequences:

- Raw Delta Impulse continuation stays rejected.
- The first regime-threshold grid stays rejected.
- The normalized context filter is not deployable because selected holdouts are
  still negative after costs.
- The next Delta Impulse research step should be a targeted veto or quality
  model for losing selected windows, not another broad parameter grid.

## 2026-06-29: Mark Delta Impulse Selected Veto Research-Only

Decision: keep the second-stage selected context veto as a diagnostic, but
reject it as a standalone strategy candidate.

Context:

- The selected-veto walk-forward starts from the old-style `8x2`
  non-overlapping context selector.
- The first-stage selected holdout baseline is `64` trades for `-1198` USD.
- A train-selected single-feature veto with at least `10` kept train trades
  improves holdout to `53` trades for `3979` USD.
- The veto removes `11` selected holdout trades and improves net by `5177` USD.
- The most selected veto families are opening-range continuation edge minimum,
  signal-delta ratio maximum, and risk-to-average-range maximum.

Consequences:

- Delta Impulse context filtering is useful for loss attribution, but not as an
  executable edge.
- No Sierra-side rule change should be made from this stack.
- Further Delta Impulse work needs a materially different hypothesis, not just
  another threshold layer.

Update after the `2026-06-29` larger export:

- Overlay validation increased only from `163` to `169` matched candidates.
- The selected-veto result held directionally: `60` kept holdout trades for
  `3930` USD versus `72` first-stage selected holdout trades for `-1554` USD.
- This is a useful sanity check, but not a genuine larger-sample validation.

Update after the continuous-contract 240D export:

- Overlay validation passed on `1003` matched candidates across `168` signal
  dates.
- Raw fixed row remained strongly negative: `-72508.50` USD.
- First-stage selected context remained negative: `364` holdout trades for
  `-45648` USD.
- Second-stage selected veto reduced losses but stayed negative: `227` kept
  holdout trades for `-22339` USD.
- The small positive selected-veto result is invalidated as an overfit/thin
  sample result.

## 2026-06-30: Keep VWAP Delta Exhaustion Fade As Research Lead

Decision: keep `vwap_delta_exhaustion_fade_2pt_10d_cl0.5` as the active scalp
research lead, but do not promote it to live automation.

Context:

- The continuous-contract 240D export covers `168` trade dates from
  `2025-11-03` through `2026-06-29`.
- The export lacked a Sierra VWAP column, so the synthetic baseline generator
  now computes a session VWAP fallback from cumulative `HLC Avg * Volume` by
  trade date.
- Default ES costs, one tick per side, rejected all `33` broad synthetic entry
  families.
- Zero-slippage and reduced-slippage sensitivity showed real entry information,
  led by VWAP/delta exhaustion fade.
- Fixed `vwap_delta_exhaustion_fade_2pt_10d_cl0.5` with `5 / 10 / 10 /
  initial` exits survived chronological `20x5` walk-forward at `1.0` tick total
  slippage per contract: `1298` holdout trades, `27101.50` USD net, `20.88`
  USD/trade.

Risks:

- Profit factor is only `1.061`.
- Only `14` of `29` five-day holdout windows are positive.
- Max trade-sequence drawdown is `-23636` USD.
- Worst day is `2026-04-13`, `-12012` USD.

Consequences:

- Stop spending time on raw Delta Impulse continuation as the main lead.
- Focus next on regime filters and daily health gates for VWAP/delta exhaustion
  fade.
- Do not build live Sierra automation until drawdown control survives
  chronological validation and execution can be modeled at or below `1.0` tick
  total slippage per contract.

Update after first risk-control pass:

- Aggregate health gates overfit: best aggregate net was `72131` USD, but the
  non-overlapping `20x5` walk-forward accepted only `18159` USD while skipped
  trades contained `15351.50` USD.
- The same-window ungated baseline for that health-gate walk-forward was
  `33510.50` USD, so the selected gates reduced net.
- Scaled context filters were worse: `218` holdout trades for `2499` USD versus
  `33510.50` USD same-window unfiltered.
- The current broad health/context gates are rejected as Sierra rule changes.
- Next work should isolate the worst days and blocks, then test targeted vetoes
  derived from those failure modes.

Update after the fresh 480D export and drawdown-control pass:

- The fresh export was produced on `2026-06-30`, but its bars ended at
  `2026-06-29 16:12:00`, so it is historical validation rather than a current
  live-session test.
- The `risk_to_average_bar_range <= 2.5` fixed guard failed fresh 480D
  acceptance gates.
- The next validation candidate is
  `vwap_delta_exhaustion_fade_2pt_10d_cl0.5` with
  `lookback_directional_move_points <= -2.5`,
  `session_range_points >= 30`, `risk_to_average_bar_range <= 1.75`,
  `6 / 10 / 12 / initial` exits, and the realized
  `daily_loss_limit_usd = 3600; maximum_equity_drawdown_usd = 4000` health
  gate.
- Build only a Sierra forward-simulation harness for this candidate. Do not add
  broker order routing.
