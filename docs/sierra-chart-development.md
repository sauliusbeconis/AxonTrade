# Sierra Chart Development

AxonTrade uses ACSIL C++ for Sierra Chart studies. Phase 0 studies are indicator-only.

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

## Manual References To Collect

Add verified Sierra Chart documentation links in `docs/research-backlog.md` as they are collected.
