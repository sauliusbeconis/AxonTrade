# Repo Hygiene

## What Belongs In Git

Keep:

- source code and tests;
- Sierra ACSIL source files;
- strategy outlines and operating docs;
- decision logs and development logs;
- markdown research conclusions;
- small curated fixtures needed by tests.

Avoid committing by default:

- raw Sierra exports;
- `.scid` and `.dly` data files;
- generated CSV sweeps;
- generated trade-audit CSVs;
- generated context diagnostics;
- local Sierra runtime logs and account-specific CSV logs.

## Reports Directory Policy

`reports/*.md` is the preferred format for durable conclusions.

`reports/*.csv` is ignored by default because most CSV reports are reproducible
intermediate artifacts and can become very large. If a CSV is genuinely needed
as a curated evidence artifact, add it intentionally with `git add -f` and make
the corresponding markdown report explain why that CSV is not just temporary
output.

## Current Evidence Anchors

The current ES-to-MES production path is anchored by:

- `docs/strategy-outline.md`;
- `docs/decision-log.md`;
- `docs/sierra-vwap-delta-execution-bot.md`;
- `docs/sierra-vwap-delta-mes-eval-live-bot.md`;
- `reports/sierra-vwap-delta-execution-bot-space300-7-12-10-primary.md`;
- `reports/sierra-vwap-delta-execution-bot-space300-candidate-robustness.md`;
- `reports/sierra-vwap-delta-execution-bot-mechanics-replay-2026-06-30.md`.
