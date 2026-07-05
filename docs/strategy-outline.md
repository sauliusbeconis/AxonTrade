# AxonTrade Strategy Outline

Status date: 2026-07-04.

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

## Active Research Tracks

MNQ now has two distinct tracks:

- `AxonTrade MNQ Eval Live Bot`: guarded ACSIL implementation of the MNQ
  VWAP/delta local lead. Live test/mechanics passed on `2026-07-05`, and it is
  approved for controlled live routing under the `MNQ_EVAL_LIVE` gates.
- `AxonTrade MNQ Eval Pass Combined Bot`: guarded ACSIL implementation of the
  MNQ eval-pass wave-rider A+B policy. It directly targets the `$1250` target,
  `-$1000` max loss, and `50%` consistency eval geometry. Live test/mechanics
  passed on `2026-07-05`, and it is approved for controlled live routing under
  the `MNQ_EVAL_PASS_AB_LIVE` gates.

The MNQ eval-pass wave-rider research first superseded the older `lb10` /
`absdelta1172` lead after correcting the sweep acceptance lens to `40` minimum
signal-start days. The later deep-search pass then improved the lead again with
a breakout buffer and denser risk refinement. The current build candidate is a
combined A+ plus faster-B policy:

- `ab_earliest_one_per_day_fast`;
- one combined bot, A+ and B signals both enabled;
- exactly one trade per day;
- earliest valid signal wins;
- exact same-bar ties choose B for lower per-trade risk;
- `122` trades: `36` A+ trades and `86` B trades;
- `$28988` net, `62.3%` win rate, `2.29` PF;
- `-$1950` max trade-sequence drawdown;
- random calendar-start eval shape: `52.5%` pass, `5.5%` fail, median `17`
  calendar days and `3` trade days for successful passes;
- valid signal-start eval shape: `85.2%` pass, `8.2%` fail, median `21.5`
  calendar days and `4` traded signals for successful passes;
- rough planning estimate: about `2-3` calendar weeks when a random-start eval
  attempt passes, not a guaranteed two-day pass.

The take-all A+B policy is rejected because it raises calendar fail to `10.1%`.
The current report is `reports/mnq-eval-pass-combined-ab.md`; Sierra setup is
documented in `docs/sierra-mnq-eval-pass-combined-bot.md`.

The sparse A+ module family to preserve is:

`lookback_breakout_deep:lb40:buf2.5:delta600:cl0.5:start1000:end1230:skipfri0:filterabs1000`

Current frozen candidates:

- practical lead `12 MNQ`, target/stop about `$726 / $750`: `43` trades,
  `$14982` net, `2.82` PF, `-$1500` max trade-sequence drawdown, worst quarter
  `-$24`, `+$3582` latest-year net, `90.7%` signal-start pass, `51.2%`
  two-day pass, `2.3%` fail at base slippage;
- conservative fallback `5 MNQ`, target/stop about `$650 / $650`: slower
  two-day pass behavior but lower size and simpler risk profile;
- aggressive variants above `$800` planned stop can pass faster on paper, but
  are not the practical default because the eval max loss is only `-$1000`.

The `12 MNQ` `$726/$750` row is no longer the standalone implementation target,
but remains the A+ module inside the combined candidate. It remains stable
through the tested slippage stress: with `6` total slippage ticks per contract,
target/stop degrades to about `$696 / $780` while pass/two-day/fail remain
`90.7% / 51.2% / 2.3%`. See
`reports/mnq-eval-pass-wave-rider-new-lead-refine.md`.

Sparse A+ walk-forward result: adaptive parameter selection is rejected. It
produced negative selected holdout results and unstable candidate choices.
Locked candidate benchmarks were materially better, so the next path is frozen
candidate validation only. The `5 MNQ` and `12 MNQ` frozen benchmarks stayed
positive across the tested chronological holdout windows. See
`reports/mnq-eval-pass-wave-rider-walk-forward.md`.

Faster-cadence B setup under validation:

- `cadence_trailing:tue_wed:short:1000_1230:none`;
- `4 MNQ`, target/stop about `$650 / $450`;
- `86` trades, `$16136` net, `-$1800` max trade-sequence drawdown;
- trailing calendar-start pass/fail/timeout: `38.9% / 3.2% / 58.0%`;
- trailing signal-start pass/fail/timeout: `80.2% / 15.1% / 4.7%`;
- median pass time is `16` calendar days and `2` trade days from random
  calendar starts, and `4` trade days from valid signal starts.

Frozen walk-forward improved the evidence for this B setup. The locked `4 MNQ`
`$650/$450` row stayed positive across `120x40`, `180x40`, and `240x60`
chronological holdout slices, with `37.2%` to `48.3%` trailing calendar pass
and `4.4%` to `6.7%` trailing calendar fail. Adaptive selection was positive
overall but weaker and less stable than the locked row. The all-candidate
frozen leaderboard ranked this same row `#1` of `6336` faster B rows; the
`1000_1130` variant ranked `#2` with identical holdout behavior.

Focused candidate review keeps the primary row as the replay target. The only
credible defensive fallback is `4 MNQ` `$500/$450`: it reduced trailing fail to
`0.0%` and trade-sequence drawdown to `-$1250`, but it sacrifices the clean
two-winning-trade eval geometry because the target is below `$625-$650`.

This B setup is not a replacement for the sparse A+ lead, but it is now the
best faster-cadence eval-pass research candidate. If it moves to replay or
ACSIL work, freeze the row instead of dynamically optimizing parameters. The
older fixed-loss `$350/$650` B row is superseded because trailing drawdown
materially changes the ranking. See
`reports/mnq-eval-pass-wave-rider-trailing-refine.md` and
`reports/mnq-eval-pass-wave-rider-trailing-walk-forward.md`, plus
`reports/mnq-eval-pass-wave-rider-trailing-candidate-review.md`.

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

`AxonTrade MNQ Eval Live Bot`

- controlled live-routing MNQ prop-eval study;
- requires `MNQ_EVAL_LIVE`;
- based on MNQ-specific VWAP/delta local research;
- live test/mechanics passed on `2026-07-05`; keep validated sizing and risk
  gates until forward sample justifies changes.

MNQ eval-pass wave rider

- research script: `scripts/run_mnq_eval_pass_wave_rider.py`;
- report: `reports/mnq-eval-pass-wave-rider-research.md`;
- ACSIL implementation: `AxonTrade MNQ Eval Pass Combined Bot`;
- Sierra setup: `docs/sierra-mnq-eval-pass-combined-bot.md`;
- intended to search for faster eval-pass geometry, not general profitability;
- live test/mechanics passed on `2026-07-05`; approved for controlled live
  routing under the documented A+B eval gates.

## Live Operating Rules

The MES eval, MNQ VWAP/delta, MNQ eval-pass combined, and MGC normal BreakEven
studies may route live orders only under their documented controlled-live gates.
The sim-only execution study must continue rejecting live trade-service routing.

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

- continue MNQ first because MNQ gives finer risk granularity than NQ;
- keep MNQ VWAP/delta profitability research separate from MNQ eval-pass
  wave-rider research;
- do not copy ES/MES thresholds directly;
- both MNQ candidates passed live test/mechanics on `2026-07-05`; the next gate
  is monitored forward sample, not size increase;
- if MNQ cannot produce an acceptable eval-pass candidate, move fresh research
  to another micro contract such as MGC.

MGC:

- `AxonTrade_MGC_OrderflowExport_Expanded.txt` passed the export quality check
  on `2026-07-03`;
- instrument config exists in `config/instruments/MGC.yaml`;
- initial continuation/pullback scan produced no accepted eval-pass candidate;
- comprehensive normal research tested opening-range breakout, opening-range
  retest, lookback breakout, VWAP pullback, VWAP fade, VWAP reclaim, and delta
  impulse families across `2511` compact variants;
- high-frequency normal research now has a fixed-rule lookback-breakout
  break-even lead:
  `mgc_lb_be_sensitivity:lb10:buf0:cl0.45:end1030:mtf:delta125:breakeven:t25:s15:trig20`;
- exits: `25` point target, `15` point initial stop, move stop to breakeven
  after `+20` points;
- `1 MGC` research stats: `343` trades, `$13298` net, `1.76` PF, `-$677`
  max trade-sequence drawdown, `+$6046` latest-year net, `+$5208` recent 120
  trade-day net, `-$397` worst quarter;
- rolling frozen holdout across `120x40`, `180x40`, and `240x60` trade-date
  windows: `$32533` aggregate holdout net, `1.97` holdout PF, `25 / 26`
  positive windows, and `-$141` worst holdout window;
- at `6` total slippage ticks/contract, the high-frequency lead stays positive
  but thinner: `$11583` net, `1.64` PF, `+$5666` latest-year net, `+$4858`
  recent 120 trade-day net, `$29283` aggregate holdout net, `1.84` holdout PF,
  `25 / 26` positive holdout windows, and `-$261` worst holdout window;
- final validation on `2026-07-05` marks MGC `100%` researched for the current
  export. The pass added extended slippage through `12` ticks, wider rolling
  holdouts, period attribution, Monte Carlo trade-order risk, sensitivity
  digest, and context-exclusion review;
- the final validation keeps the frozen live rule. It remains positive through
  `12` ticks (`$9525` net, `1.50` PF rounded), but Monte Carlo path-risk is
  meaningfully higher than chronological drawdown (`-$677` chronological
  base-cost DD versus about `-$1131` median shuffled DD), so `1 MGC` sizing and
  account-level buffers stay mandatory;
- adaptive walk-forward selection is rejected because it produced negative
  aggregate holdout net on the `180x40` and `240x60` views;
- the weekday rule is fixed, not adaptive: trade Monday/Tuesday/Friday only,
  because Wednesday and Thursday were persistent drag buckets in this export;
- fixed-exit robustness kept the old `delta100` row, but trade-management and
  break-even sensitivity produced a better replacement;
- the practical replacement is the `cl0.45/end1030/delta125` break-even row
  because it improves net, PF, drawdown, latest-year net, recent 120 trade-day
  net, and aggregate holdout versus the old fixed-exit baseline under both base
  and six-tick stress cost;
- context stress did not promote any extra live-rule exclusion; weak buckets
  include Tuesday, early `2024`, VWAP distance `2-5`, day range below `10`, and
  entry-bar absolute delta `50-75`, but exclusions that improved one metric
  either reduced full-sample net or worsened holdout quality;
- higher-net growth variant to monitor:
  `mgc_lb_be_sensitivity:lb10:buf0:cl0.45:end1045:mtf:delta125:breakeven:t25:s15:trig20`
  with `$13449` base net and `$11714` stress net, but worse max drawdown than
  the `10:30` risk-balanced row;
- the earlier lower-frequency quality lead remains useful as a comparison:
  `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:none`;
- its `1 MGC` research stats are `116` trades, `$3880` net, `1.50` PF, `-$790`
  max trade-sequence drawdown, `+$1608` latest-year net, `+$1468` recent 120
  trade-day net, `-$177` worst quarter;
- at `6` total slippage ticks/contract, `1 MGC` still shows `$3300` net,
  `1.41` PF, `+$1408` latest-year net, and `+$1293` recent 120 trade-day net;
- treat MGC as a completed fixed-rule offline research track for this export,
  with a matching ACSIL implementation now built as
  `AxonTrade MGC Normal BreakEven Bot`. Sierra mechanics validation and
  supervised live staging passed on `2026-07-05`. Controlled `1 MGC` live
  routing is approved with clean chart data and exact routing/account gates.
  The next evidence gate is monitored forward sample and account-level risk,
  not more static tuning or size increase.
