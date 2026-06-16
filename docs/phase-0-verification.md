# Phase-0 Verification

Use this checklist on the target Pop!_OS and Wine workstation.

## Manual Checklist

- Clone the repository.
- Install Python dependencies.
- Run `python -m pytest`.
- Run `bash scripts/check_repo.sh`.
- Launch Sierra Chart under Wine.
- Enable Sierra Chart Linux compatibility settings as needed for the local installation.
- Sync ACSIL files with `bash scripts/sync_to_sierra.sh`.
- Compile the custom study through Sierra Chart remote build.
- Load `OrderFlowSignalSmokeTest` on a chart.
- Confirm the horizontal line appears.
- Confirm the label appears.
- Recalculate repeatedly.
- Run chart replay.
- Confirm no duplicate drawings appear.
- Confirm no duplicate CSV rows appear for the same deterministic smoke-test event.
- Record Wine-specific issues in `docs/decision-log.md` or a GitHub issue.

## Expected Result

The custom study should behave as an indicator-only visual/logging smoke test. No orders should be submitted, modified, canceled, flattened, or routed.
