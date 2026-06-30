# Sierra Chart Development

AxonTrade uses ACSIL C++ for Sierra Chart studies. Most Phase 0 studies are
indicator-only. The approved exception is the dedicated simulation-only
execution harness documented in `docs/sierra-vwap-delta-execution-bot.md`.

## ACSIL Workflow

1. Edit source files in `src/acsil`.
2. Sync them to Sierra Chart's `ACS_Source` directory with `scripts/sync_to_sierra.sh`.
3. Compile through Sierra Chart's custom study build workflow.
4. Load the custom study on a replay or simulation chart.
5. Confirm drawings and CSV logging are recalculation-safe.

## Smoke-Test Study

`OrderFlowSignalSmokeTest.cpp` is a visual and logging smoke test. It draws an
indicator-only signal line, stop, target, invalidation line, and label. It
writes CSV rows matching `config/research/signal_log_schema.yaml`.

The study must not submit, modify, cancel, flatten, or route orders.

## Recalculation Safety

Use deterministic drawing identifiers and Sierra Chart's add-or-adjust drawing behavior so repeated recalculation adjusts existing drawings instead of creating duplicates.

CSV logging must prevent duplicate event rows during recalculation.

## Official References

Manual help needed: **No**.

Verified source list:

`docs/sierra-acsil-reference-audit.md`

Key source-controlled rules from the official Sierra docs:

- ACSIL source files use `#include "sierrachart.h"`, `SCDLLName(...)`, and
  `SCSFExport`.
- Build through `Analysis >> Build Custom Studies DLL`; use
  `Build >> Remote Build` for the current Wine workflow.
- Use `sc.UseTool()` with stable drawing identifiers and `UTAM_ADD_OR_ADJUST`
  for recalculation-safe AxonTrade drawings.
- Set `sc.MaintainVolumeAtPriceData = 1` in `sc.SetDefaults` before reading
  `sc.VolumeAtPriceForBars`.
