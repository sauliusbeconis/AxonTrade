# ACSIL Sources

This directory contains Sierra Chart ACSIL C++ source files.

Most Phase 0 studies are indicator-only. They may draw chart objects and write
simulation-safe research logs, but they must not submit, modify, cancel,
flatten, or route orders.

The only approved exception is `AxonTradeVwapDeltaExecutionBot.cpp`, which is a
simulation-only mechanics harness. It rejects live trade-service routing in code
and is isolated by `scripts/check_repo.sh`.

## Smoke Test

`OrderFlowSignalSmokeTest.cpp` draws a configurable signal line, stop, target,
invalidation line, and label. It writes CSV rows using
`config/research/signal_log_schema.yaml`.

The study uses deterministic drawing identifiers and add-or-adjust behavior so
repeated recalculation updates the same drawings instead of creating duplicates.
CSV rows use deterministic event keys so recalculation does not create duplicate
rows for the same event.

## Volume At Price Logger

`AxonTradeVolumeAtPriceLogger.cpp` writes one CSV row per chart bar price level
using Sierra Chart's `sc.VolumeAtPriceForBars` data. The study is indicator-only
and uses an explicit one-shot `Export Now` input so it does not continuously
rewrite files during replay.

The output contract is documented in
`config/research/sierra_volume_at_price_export.yaml`.

## Liquidity Sweep Signal Overlay

`AxonTradeLiquiditySweepSignalOverlay.cpp` evaluates the first bar-level
liquidity-sweep absorption rule on the active chart, draws candidate markers,
and writes candidate/rejection rows using
`config/research/signal_log_schema.yaml`.

Build and load instructions are documented in
`docs/sierra-liquidity-sweep-signal-overlay.md`.

## Delta Impulse Continuation Overlay

`AxonTradeDeltaImpulseContinuationOverlay.cpp` evaluates the fixed-exit
`delta_impulse_continue_10bar_2.5pt_50d` research lead on the active chart,
draws candidate markers and fixed stop/target lines, and writes
candidate rows using `config/research/signal_log_schema.yaml`. Rejection rows
are optional diagnostics and are disabled by default to keep historical
backfills small.

Build and load instructions are documented in
`docs/sierra-delta-impulse-continuation-overlay.md`.

## VWAP Delta Live Sim Bot

`AxonTradeVwapDeltaLiveSimBot.cpp` forward-tests the current
`vwap_delta_exhaustion_fade_2pt_10d_cl0.5` validation candidate on rolling
Sierra Chart data. It draws and logs virtual two-contract paper trades with the
fixed context guard, `6 / 10 / 12 / initial` exits, and realized
`daily3600_dd4000` health gate. First-leg and runner quantities are inputs so
the same signal can be modeled as ES-sized or MES-sized exposure. It is
simulation-only and does not route orders.

Build and load instructions are documented in
`docs/sierra-vwap-delta-live-sim-bot.md`.

## VWAP Delta Execution Bot

`AxonTradeVwapDeltaExecutionBot.cpp` submits Sierra Chart simulation orders for
mechanics testing of the selected VWAP/delta exhaustion fade. It uses explicit
arming, simulation-mode, confirmation-text, symbol-prefix, position, daily-loss,
session-open trend-day gates, an accepted-setup alert sound, and chart drawings
for submitted entry/stop/target levels plus bot fill markers. Live trade-service
routing is rejected in this build. Current defaults target the accepted
300-second ES profile with
`7 / 12 / 10 / initial` exits, `lookback_directional_move_points <= -15`,
`risk_to_average_bar_range <= 1.7142857`, `directional_open_distance_points >=
-80`, `session_range_points <= 100`, and a `$2400` daily loss lock.

Build, load, and first mechanics-test instructions are documented in
`docs/sierra-vwap-delta-execution-bot.md`.

The same source also exports `AxonTrade MES Eval Live Bot` and `AxonTrade MNQ
Eval Live Bot`, separate live-capable prop-eval studies. MES defaults to
`1 + 1 MES`, `$240` daily loss lock, `$650` daily profit lock, `$1000` eval
trailing drawdown lock, an exact account whitelist, and `MES_EVAL_LIVE`
confirmation text. MNQ defaults to the local `80pt_400d_cl0.4` research lead
with `25 / 140 / 40 / initial` exits, no Friday entries, no `11:00` or `15:00`
exchange-time entries, `$650` daily loss/profit locks, `$1000` eval trailing
drawdown lock, an exact account whitelist, and `MNQ_EVAL_LIVE` confirmation
text. Both live profiles require Sierra trade simulation mode to be off before
they can route to the trade service.

Live/eval setup instructions are documented in
`docs/sierra-vwap-delta-mes-eval-live-bot.md` and
`docs/sierra-vwap-delta-mnq-eval-live-bot.md`.

## Build Workflow

1. Sync sources with `bash scripts/sync_to_sierra.sh`.
2. Compile through Sierra Chart's custom study build workflow.
3. Load the study on a replay or simulation chart.
4. Follow `docs/phase-0-verification.md`.

Official Sierra ACSIL references are recorded in
`docs/sierra-acsil-reference-audit.md`.
