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

Update after mapping to LucidFlex 25K:

- The research-size `1 ES + 1 ES` profile is too close to the LucidFlex 25K
  `$1,000` max loss limit because a full stop is about `-$1,000` before costs.
- Keep the signal, stop, and target rules fixed, and scale exposure with MES
  quantities for prop-account fitting.
- Add explicit first-leg and runner quantities plus a paper daily profit lock
  to the Sierra live-sim study.
- Suggested forward-sim profile for LucidFlex 25K funded start is ES signal
  chart with `5 MES + 5 MES` modeled by `First Leg Quantity = 5`,
  `Runner Quantity = 5`, `Point Value USD = 5`, and `Tick Value USD = 1.25`.

Update after switching from forward-log collection to mechanics testing:

- Months of live forward logs are not required for the next step. The immediate
  task is a real-time Sierra mechanics test: confirm order submission, attached
  targets, attached stop, flatten behavior, arming gates, and logging.
- Add a separate simulation-only execution harness instead of converting the
  live-sim logger into an order router.
- Keep live trade-service routing disabled. The execution harness rejects
  `Send Orders To Trade Service = Yes` in this build.
- Use MES-sized defaults for mechanics: `First Leg Quantity = 1`,
  `Runner Quantity = 1`, `Max Position Quantity = 2`, `Daily Loss Lock USD =
  200`, and `Daily Profit Lock USD = 650`.
- The daily loss lock is not a substitute for sizing. With a 10-point stop,
  `5 MES + 5 MES` can lose roughly `-$500` before costs, so it does not fit the
  preferred `-$150` to `-$250` daily-loss band.

Update after the first replay mechanics pass:

- On `2026-06-30`, Sierra replay on `ESU26-CME` submitted the first
  simulation entry with the current, unrelaxed guard settings.
- Replay signal bar: `2026-06-25 12:45:00`, long
  `vwap_delta_exhaustion_fade_2pt_10d_cl0.5`, entry `7418.50`.
- Bot CSV row: `execution_entry_submitted`, `order_result = 2`,
  `parent_internal_order_id = 43`, `target1_internal_order_id = 41`,
  `target2_internal_order_id = 44`, `stop_all_internal_order_id = 42`.
- Manual Sierra visual check passed: parent order, two targets, and common stop
  appeared correctly; observed mechanics were clean.
- Follow-up CSV state was consistent with attached-order behavior: position
  moved from `2` to `1` after the first target, then later to flat with no
  working orders and `daily_profit_loss = 900`.
- Keep live trade-service routing disabled. The next validation is additional
  replay/simulation coverage, especially flatten/cancel and loss-side behavior,
  not live promotion.

Update after the second replay mechanics pass:

- On `2026-06-30`, Sierra replay on `ESU26-CME` submitted a short simulation
  entry for the loss-side mechanics test.
- Replay signal bar: `2026-06-18 10:42:00`, short
  `vwap_delta_exhaustion_fade_2pt_10d_cl0.5`, entry `7558.50`.
- Bot CSV row: `execution_entry_submitted`, `order_result = 2`,
  `parent_internal_order_id = 49`, `target1_internal_order_id = 47`,
  `target2_internal_order_id = 50`, `stop_all_internal_order_id = 48`.
- The daily loss lock and flatten path worked: at `2026-06-18 10:45:00`, the
  bot logged `execution_flatten_submitted` with
  `daily loss lock active; loss_view=-825; limit=200`.
- The bot then blocked a later valid setup at `2026-06-18 10:57:00` with
  `daily_loss_lock_blocked`, confirming that the daily lock prevents same-day
  re-entry after the loss condition is reached.
- Mechanics coverage now includes long entry, short entry, attached targets,
  common stop, first-target scale-out state, flatten/cancel submission, and
  post-loss daily lockout.

Update after expanded ES 300-second candidate research:

- On `2026-07-01`, the expanded ES export produced a non-rejected
  `AxonTradeVwapDeltaExecutionBot` candidate:
  `space300_all_exit7_12_10_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400`.
- Full-sample accepted-trade result: `588` trades, `$66,584` net,
  `$113.24` average/trade, `1.2953` profit factor, `-$12,462` max
  trade-sequence drawdown, and `-$3,160` worst day.
- Rolling robustness passed all five tested window shapes. Weakest total
  guarded holdout net was `$56,660`; weakest average was `$107.93`; maximum
  negative-window rate was `0.3478`; worst guarded window was `-$6,642`.
- The higher-net `7 / 12 / 8 / initial` variant was rejected because it failed
  negative-window-rate robustness on three wider window shapes.
- The active execution bot defaults now use `300` second raw candidate spacing,
  `7 / 12 / 10 / initial` exits, `lookback_directional_move_points <= -15`,
  `session_range_points >= 30`, `risk_to_average_bar_range <= 1.7142857`,
  `directional_open_distance_points >= -80`, `session_range_points <= 100`,
  and `Daily Loss Lock USD = 2400`.
- Evidence files:
  `reports/sierra-vwap-delta-execution-bot-space300-candidate-robustness.md`,
  and
  `reports/sierra-vwap-delta-execution-bot-space300-7-12-10-primary.md`.
  The large CSV search artifacts are generated outputs and are not required as
  durable Git evidence unless intentionally promoted.

Update after MNQ top-runner research:

- On `2026-07-05`, the MNQ breakeven-frequency path was parked and a different
  normal-profitability family was researched: lookback-breakout continuation
  runners with fixed target/stop exits.
- The active lead is `MNQ_TOP_RUNNER`: `20` bar lookback breakout,
  `10:00-11:00`, no Friday, delta `600`, directional close location `>= 0.9`,
  `2 MNQ`, `160 / 70` point target/stop.
- Frozen validation result: `87` trades, `$11772` net, `2.15` PF, `54.0%` win
  rate, `-$1854` max trade-sequence drawdown, and `$7089` latest-year net.
- The lower-DD variant keeps the same signal with `120 / 70`, `$10135` net,
  `2.08` PF, and `-$1146` drawdown.
- Slippage stress through `6` total ticks per contract stayed positive across
  the high-PF, lower-DD, and higher-sample frozen variants; rolling holdouts
  were mostly positive across `120x40`, `180x40`, and `240x60`.
- A new Sierra study, `AxonTrade MNQ Top Runner Sim Bot`, was added for
  replay/mechanics only with confirmation text `MNQ_TOP_RUNNER_SIM`.
- Live trade-service routing is intentionally rejected. The next gate is Sierra
  replay/mechanics validation, not live promotion.

Update after MNQ top-runner mechanics validation:

- On `2026-07-05`, operator replay/mechanics validation passed for
  `AxonTrade MNQ Top Runner Sim Bot`.
- This confirms the simulation/replay study is usable as the mechanics
  reference for the top-runner family.
- Live routing remains intentionally blocked in this study.
- The next gate is a live-capable implementation review: choose between the
  high-PF `160 / 70`, lower-DD `120 / 70`, and higher-sample `cl >= 0.8`
  variants, then define account-level daily locks and multi-account scaling
  rules.

Update after MNQ top-runner live-capable build:

- The first live-capable top-runner build uses the lower-DD variant rather than
  the high-PF variant: `2 MNQ`, `120 / 70`, directional close location `>= 0.9`.
- Rationale: the high-PF `160 / 70` row has stronger net/PF but larger
  drawdown; first controlled live staging should prioritize the smoother
  `-$1146` historical drawdown profile from the lower-DD row.
- Default live risk lock is `$300` daily loss, which is roughly one full
  `2 MNQ` stop before costs.
- New Sierra study: `AxonTrade MNQ Top Runner Live Bot`.
- Confirmation text: `MNQ_TOP_RUNNER_LIVE`.
- The existing `AxonTrade MNQ Top Runner Sim Bot` remains simulation-only and
  continues to reject live trade-service routing.
- This is a controlled live-staging candidate, not approved unattended
  automation.

Update after scaling-roadmap review:

- Scaling strategy is account-count first, not contract-size first.
- Eval acquisition lead is `AxonTrade MNQ Eval Pass Combined Bot`; it remains
  an eval-pass tool and should not be run on a fresh funded 25K account because
  the A+ side can use `12 MNQ`, above the funded day-zero `10` micro scaling
  tier.
- Funded survival lead is `AxonTrade MGC Normal BreakEven Bot`; funded growth
  can add `AxonTrade MNQ Eval Live Bot` after account buffer and aggregate risk
  review.
- `AxonTrade MNQ Top Runner Live Bot` stays future growth/staging until
  controlled live staging passes.
- README now includes Sierra manual build/arming steps and a scaling roadmap
  covering LucidFlex 25K assumptions, parallel eval math, account allocation,
  payout constraints, and rough time-to-profit planning.

Update after MNQ top-runner deep validation:

- The Top Runner family is now marked `100%` researched for the current MNQ
  export, meaning the static-rule offline research budget is exhausted for this
  dataset. This is not a profit guarantee.
- Deep validation added `8/10/12` tick slippage stress, wider rolling holdouts,
  period attribution, Monte Carlo trade-order risk, direct-parameter
  neighborhood testing, and candidate overlap.
- Important implementation finding: the strongest frozen research row is a
  two-stage filtered rule, not a direct strict close-location rule. It uses a
  broad raw `10:00-12:30` lookback-breakout stream with raw close-location
  `0.65`, then a final `10:00-11:00` directional close-location filter. Raw
  one-hour spacing is applied before the final filter.
- Direct strict `10:00-11:00 / close-location 0.9` tested worse than the frozen
  filtered lower-DD row: `120` trades, `$8635` net, `1.57` PF, `-$1712` DD
  versus `87` trades, `$10135` net, `2.08` PF, `-$1146` DD.
- The ACSIL Top Runner sim/live studies were aligned to the filtered frozen
  rule and now expose `rawLast` on the chart status banner.
- Prior Top Runner mechanics validation is superseded for the aligned signal
  filter. Fresh replay/mechanics and controlled live staging are required
  before any Top Runner live approval.

Update after filtered MNQ top-runner replay/mechanics pass:

- Operator built the Sierra DLL and confirmed fresh replay/mechanics passed for
  the aligned filtered-rule `AxonTrade MNQ Top Runner Sim Bot`.
- This clears the replay/mechanics gate that was reopened by the two-stage
  filter alignment.
- Top Runner is still not approved for unattended live automation. The next
  gate is controlled live staging of `AxonTrade MNQ Top Runner Live Bot` with
  `MNQ_TOP_RUNNER_LIVE`, exact account whitelist, `2 MNQ`, lower-DD `120 / 70`,
  and `$300` daily loss lock.

Update after MGC final validation:

- `AxonTrade MGC Normal BreakEven Bot` is now marked `100%` researched for the
  current MGC one-minute order-flow export. This means the fixed-rule offline
  research budget is saturated for this dataset, not that future profitability
  is guaranteed.
- Final validation reproduced the frozen live rule at `343` sequenced trades:
  `$13298` net, `1.76` PF, `-$677` chronological drawdown, and about `2.86`
  trades/week at base cost.
- Six-tick stress remains strong at `$11583` net, `1.64` PF, and `-$722`
  chronological drawdown. Twelve-tick stress remains net positive at `$9525`
  and roughly `1.50` PF.
- Wider holdouts, period attribution, sensitivity digest, and context-exclusion
  review did not replace the current `10:30 / cl0.45 / delta125 / 25-15 /
  BE+20` live rule.
- Monte Carlo trade-order risk is the main caution: base-cost shuffled paths
  had median drawdown around `-$1131` and P95 around `-$1761`, so controlled
  `1 MGC` sizing and account-level risk buffers remain mandatory.
- Next gate is operational forward evidence, not more static tuning or size
  increase.

Update after MNQ Eval Live final validation:

- `AxonTrade MNQ Eval Live Bot` is now marked `100%` researched for the current
  MNQ export. This means the fixed-rule offline research budget is saturated
  for this dataset, not that future profitability is guaranteed.
- Final validation separates the legacy independent audit from the executable
  live-sequenced path. The legacy audit remains `186` trades, `$9584.50` net,
  `2.09` PF, and `-$976` DD, but it includes overlapping paper trades that the
  ACSIL position/working-order gate would reject.
- The executable live-sequenced baseline is now the headline: `166` trades,
  `$8897` net, `2.12` PF, `82.5%` win rate, `-$924.50` chronological DD, and
  about `1.62` trades/week.
- Six-tick live-sequenced stress remains strong at `$8067` net, `2.00` PF, and
  `-$944.50` chronological DD. Twelve-tick stress remains positive at `$7071`
  and `1.85` PF.
- A `15552` row neighborhood search tested local entry thresholds, spacing
  alternatives, exits, and runner-stop modes. No row replaced the current live
  defaults under the final live-sequenced lens.
- Main caution remains path risk: live-sequenced Monte Carlo median drawdown is
  about `-$1193`, P95 about `-$1931`, so this bot still needs account-level
  buffer and aggregate risk control before scaling.
- Next gate is monitored forward evidence, not more static tuning or default
  changes.

Update after the NinjaTrader/Tradeify 50K Select strategy pivot (`2026-08-05`):

- The active branch is strategy-only. No NinjaScript or NinjaTrader live route
  was created on Linux.
- Official Tradeify 50K Select assumptions were versioned in
  `config/firms/tradeify_50k_select.yaml`: `$3000` target, `$2000` end-of-day
  trailing drawdown enforced in real time, `40%` evaluation consistency, and
  no firm evaluation daily loss limit.
- Fresh MNQ opening-drive, session-sweep, gap-fade, and VWAP-pullback families
  failed the final chronological holdout. The frozen MNQ VWAP/delta adaptation
  reached `76.8%` wins and `1.69` PF but was rejected after shuffled P95
  drawdown reached about `-$2845`.
- MGC replaced MNQ as the primary instrument for this account geometry. The
  frozen `10`-bar breakout, `cl0.45`, `delta<=125`, `25/15`, `BE+20` strategy
  remains the strongest path-stable local signal.
- Using Tradeify's `$2.12` MGC round-trip fee plus two total slippage ticks,
  fixed `1 MGC` produced `343` trades, `$12570.84` net, `1.71` PF, `55.1%`
  wins, and `-$696.08` chronological drawdown. Six-tick stress remained at
  `$11198.84`, `1.61` PF, and `-$732.08` drawdown.
- Fixed `1 MGC` is the only non-rejected account policy. Historical rolling
  365-day starts passed `91.9%` with median successful duration `236` calendar
  days. This is a survival-first strategy, not a quick-pass claim.
- A high-win `8/15` MGC plus logistic entry filter reached `76.5%` holdout
  wins, `1.60` PF, and `-$621` drawdown, but the development-selected faster
  sizing policy risk-locked `15.0%` of final bootstrap paths. It remains
  rejected.
- The next gate is Windows/NinjaTrader data parity, high-resolution historical
  testing, Playback, and simulation. Static tuning on the same exports is
  frozen.

Follow-up after quality-model collinearity and account-policy audit:

- The first high-win quality model contained two duplicate predictors:
  aligned delta duplicated absolute delta, and aligned VWAP distance duplicated
  absolute VWAP distance for this breakout stream. They were removed.
- Account sizing selection now requires both chronological development and
  development block-bootstrap gates before the final-period bootstrap is read.
- The cleaned fixed `8 / 15` quality model froze at logistic threshold `0.70`
  and produced `198` one-MGC trades: `$4787.24` net, `1.74` PF, `76.3%` wins,
  and `-$542.96` drawdown. Six-tick stress remained `$3995.24`, `1.60` PF,
  `75.8%` wins, and `-$574.96` drawdown.
- The development-selected account policy uses `3 MGC` within `$500` of the
  EOD high-water mark, `2 MGC` from `-$500` to `-$1000`, and `1 MGC` below
  `-$1000`, always subject to a full-stop plus `$100` reserve check.
- Account paths: development bootstrap `66.9%` pass / `4.2%` risk lock; final
  bootstrap `80.5%` pass / `8.2%` risk lock; full historical 365-day starts
  `99.4%` pass with median `215` calendar days. The historical funded
  `+$2100` drawdown-lock objective passed `100%` with median `126` calendar
  days.
- Numerical gates pass, but the final period had already been inspected during
  the earlier failed model iteration. Status is therefore
  `PROVISIONAL_GATES_PASS_REQUIRES_INDEPENDENT_REPLAY`, not independently
  validated production approval.
- `AxonTrade Tradeify MGC Select v1` becomes the provisional NinjaTrader
  research lead. Fixed `1 MGC` Core v1 remains the non-rejected fallback.
