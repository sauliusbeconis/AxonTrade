# AxonTrade Strategy Outline

Status date: 2026-07-01.

## Objective

Build a profitable live futures bot through a narrow, auditable path:

- keep one production candidate active at a time;
- preserve the research and development log;
- translate ES research to MES only through explicit sizing and risk controls;
- keep NQ/MNQ as separate research, not a copy of ES/MES parameters.

## Active Production Track

The active live track is `AxonTrade MES Eval Live Bot`, exported from
`src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`.

Its job is to trade the ES-derived VWAP/delta exhaustion setup on MES with prop
evaluation risk limits:

- required symbol prefix: `MES`;
- confirmation text: `MES_EVAL_LIVE`;
- exact allowed trade account required;
- Sierra trade simulation mode must be off;
- `Send Orders To Trade Service = Yes` and `Arm Execution = Yes` are both
  required;
- no entries while Sierra is downloading historical data;
- no entries while a position or working orders already exist.

Current eval sizing:

- first leg quantity: `1`;
- runner quantity: `1`;
- initial stop: `12` points;
- first target: `7` points;
- runner target: `10` points;
- daily loss lock: `$240`;
- daily profit lock: `$650`;
- eval trailing drawdown lock: `$1000`.

The daily profit lock is an evaluation-phase constraint only. It should not be
treated as a permanent post-evaluation profit cap.

## Current Strategy

The active signal family is a VWAP/delta exhaustion fade:

- bar closes at least `2` points beyond VWAP in the fade direction;
- bar delta must be at least `10` in the exhaustion direction;
- close-location threshold is `0.5`;
- context filters require a meaningful directional move into the signal;
- trend-day veto blocks strong session-open extension conditions.

The accepted ES research candidate currently reflected in the execution source
is:

`space300_all_exit7_12_10_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400`

Core parameters:

- minimum raw candidate spacing: `300` seconds;
- maximum lookback directional move: `-15` points;
- minimum session range: `30` points;
- maximum risk-to-average-bar-range: `1.7142857`;
- minimum directional open distance: `-80` points;
- maximum session range: `100` points;
- ES research daily loss lock: `$2400`;
- ES research daily profit lock: disabled.

## Evidence

Primary ES research evidence:

- report: `reports/sierra-vwap-delta-execution-bot-space300-7-12-10-primary.md`;
- robustness report:
  `reports/sierra-vwap-delta-execution-bot-space300-candidate-robustness.md`;
- decision log: `docs/decision-log.md`.

Accepted ES result:

| Metric | Value |
| --- | ---: |
| Accepted trades | `588` |
| Net USD | `$66,584` |
| Average/trade | `$113.24` |
| Profit factor | `1.2953` |
| Max trade-sequence drawdown | `-$12,462` |
| Worst day | `-$3,160` |
| Rolling robustness windows passed | `5 / 5` |

This evidence supports continued live-eval work on MES. It does not prove that
the same parameters are optimal for NQ/MNQ.

## Bot Inventory

`AxonTrade VWAP Delta Execution Bot`

- simulation-only mechanics/replay study;
- requires `SIM_ONLY`;
- rejects live trade-service routing;
- intended for ES replay and mechanics validation.

`AxonTrade MES Eval Live Bot`

- live-capable prop-eval study;
- requires `MES_EVAL_LIVE`;
- requires an exact account whitelist;
- intended for controlled MES live evaluation.

## Live Operating Rules

Only the MES eval study may route live orders. The sim-only execution study must
continue rejecting live trade-service routing.

Before arming:

- selected chart symbol starts with `MES`;
- selected trade account matches `Allowed Trade Account`;
- Sierra trade simulation mode is off;
- no open position;
- no working orders;
- daily loss, profit, and trailing drawdown locks are not active.

If the platform data is broken, the bot is not armed. Recent Sierra/Rithmic ES
and MES historical backfill problems mean chart data quality remains a live
operational gate, not a one-time setup detail.

## Data And Research Policy

Development logs, decision logs, and markdown conclusions are durable project
evidence.

Large CSV sweeps, raw exports, trade audits, and context diagnostics are
generated artifacts by default. They can be regenerated from Sierra exports and
scripts, so they stay out of Git unless intentionally promoted as curated
evidence.

Use `scripts/scan_sierra_scid.py` when Sierra Chart data coverage is in doubt.
It inspects local `.scid` files quickly without loading multi-gigabyte tick
files into memory.

## Next Research Tracks

MES:

- continue live-eval operation only under the current MES risk gates;
- export the larger MES dataset after enough usable data is available;
- evaluate maximum trade-sequence drawdown and eval trailing drawdown behavior,
  not only full-sample equity drawdown;
- tune evaluation-stage sizing separately from post-evaluation sizing.

NQ/MNQ:

- create a separate research branch when starting serious work;
- begin with MNQ, not NQ, because MNQ gives finer risk granularity;
- do not copy ES/MES thresholds directly;
- require separate MNQ data coverage, parameter search, walk-forward robustness,
  and mechanics testing before any live consideration.
