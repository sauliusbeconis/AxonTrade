# ACSIL Sources

This directory contains Sierra Chart ACSIL C++ source files.

Phase 0 studies must be indicator-only. They may draw chart objects and write simulation-safe research logs, but they must not submit, modify, cancel, flatten, or route orders.

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

## Build Workflow

1. Sync sources with `bash scripts/sync_to_sierra.sh`.
2. Compile through Sierra Chart's custom study build workflow.
3. Load the study on a replay or simulation chart.
4. Follow `docs/phase-0-verification.md`.
