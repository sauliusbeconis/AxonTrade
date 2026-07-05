# AxonTrade

AxonTrade is a futures trading research and execution laboratory focused on
intraday ES/MES, NQ/MNQ, and MGC bots for Sierra Chart.

It is not a signal service, martingale/grid system, HFT project, or black-box
automation project. Every live-capable path must have explicit research
evidence, Sierra mechanics validation, and hard routing/risk gates.

## Current Situation

Status date: `2026-07-05`.

Overall goal: build a profitable live trading bot, with the near-term practical
path split between controlled MES evaluation trading, controlled MGC
normal-profitability trading, MNQ eval-pass execution, and MNQ normal-runner
research.

Percentages below are engineering readiness estimates, not profit forecasts or
win probabilities. Research stats are backtest/replay evidence after the
documented cost model and filters.

Color key: 🟢 controlled live path; 🟡 research or validation path; 🔴 blocked or
simulation-only.

### MGC

| Status | Bot / Track | Use | Research | Forward | Live | Net | PF | Win Rate | Avg Trades / Week | Current Decision |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 🟢 | `AxonTrade MGC Normal BreakEven Bot` | normal-profitability live bot | 75% | 5% | 75% | `$13298` | `1.76` | `55.4%` | `2.9` | Live staging passed; controlled `1 MGC` routing approved. Next gate is monitored forward sample, not size increase. |

### MES

| Status | Bot / Track | Use | Research | Forward | Live | Net | PF | Win Rate | Avg Trades / Week | Current Decision |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 🟢 | `AxonTrade MES Eval Live Bot` | prop-eval live path | 70% | 35% | 75% | `$66584` | `1.30` | `60.9%` | `5.8` | Approved controlled live-routing path with tight eval locks. Research stats are from the ES-derived accepted candidate after daily loss lock. |

### MNQ

| Status | Bot / Track | Use | Research | Forward | Live | Net | PF | Win Rate | Avg Trades / Week | Current Decision |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 🟢 | `AxonTrade MNQ Eval Pass Combined Bot` | eval-pass A+B wave-rider | 80% | 60% | 75% | `$28988` | `2.29` | `62.3%` | `1.2` | Live test/mechanics passed; controlled live routing approved for the validated A+B eval setup. |
| 🟢 | `AxonTrade MNQ Eval Live Bot` | MNQ VWAP/delta profitability lead | 75% | 20% | 75% | `$9584.50` | `2.09` | `80.1%` | `1.8` | Live test/mechanics passed; controlled live routing approved for the validated VWAP/delta setup. |
| 🟡 | `AxonTrade MNQ Top Runner Live Bot` | normal-profitability runner live candidate | 100% | 0% | 35% | `$10135` | `2.08` | `57.5%` | `0.85` | Offline research is saturated, ACSIL is aligned to the filtered frozen rule, and fresh replay/mechanics passed. Requires controlled live staging before approval. |

Backlog: other instruments such as `MCL` stay at `0%` readiness until MNQ/MGC
work stalls or a new export creates a stronger reason to branch.

## Current Bot Setup Rules

Use this table as the first check before arming anything in Sierra Chart.

| Study | Purpose | Symbol Prefix | Confirmation Text | Routing Mode | Required Account | Core Setup Rules |
| --- | --- | --- | --- | --- | --- | --- |
| `AxonTrade VWAP Delta Execution Bot` | ES simulation/replay mechanics | `ES` | `SIM_ONLY` | `Send Orders To Trade Service = No`; Sierra trade simulation mode on | Not required | Simulation-only by design; arm only on replay/sim chart; rejects live trade-service routing |
| `AxonTrade MES Eval Live Bot` | Current approved controlled live eval path | `MES` | `MES_EVAL_LIVE` | `Send Orders To Trade Service = Yes`; Sierra trade simulation mode off | Exact `Allowed Trade Account` required | `1 + 1 MES`, `$240` daily loss lock, `$650` daily profit lock, `$1000` eval trailing lock, no historical download, no position/working orders |
| `AxonTrade MNQ Eval Live Bot` | MNQ VWAP/delta research implementation | `MNQ` | `MNQ_EVAL_LIVE` | Controlled live routing approved for validated setup | Exact `Allowed Trade Account` required | `1 + 1 MNQ`, `25 / 140 / 40` exits, no Friday, no `11:00`/`15:00`, `$650` daily loss/profit locks, `$1000` eval trailing lock |
| `AxonTrade MNQ Eval Pass Combined Bot` | Built MNQ A+B eval-pass study | `MNQ` | `MNQ_EVAL_PASS_AB_LIVE` | Controlled live routing approved for validated A+B setup | Exact `Allowed Trade Account` required | A+ `12 MNQ` with `31 / 30.5` target/stop; B `4 MNQ` with `82 / 55.5` target/stop; one trade/day; `$900` daily loss lock; `$650` daily profit lock; `$1000` eval trailing lock |
| `AxonTrade MNQ Top Runner Sim Bot` | MNQ top-runner replay/mechanics study | `MNQ` | `MNQ_TOP_RUNNER_SIM` | `Send Orders To Trade Service = No`; Sierra trade simulation mode on | Not required | Simulation-only; `2 MNQ`, filtered lookback breakout: raw `10:00-12:30`/CL `0.65`/delta `600`, final `10:00-11:00` directional CL `0.9`, no Friday, `160 / 70`, `3600s` raw spacing, `15:45` flatten |
| `AxonTrade MNQ Top Runner Live Bot` | MNQ top-runner controlled live candidate | `MNQ` | `MNQ_TOP_RUNNER_LIVE` | `Send Orders To Trade Service = Yes`; Sierra trade simulation mode off | Exact `Allowed Trade Account` required | Live-capable lower-DD variant; `2 MNQ`, filtered lookback breakout: raw `10:00-12:30`/CL `0.65`/delta `600`, final `10:00-11:00` directional CL `0.9`, no Friday, `120 / 70`, `$300` daily loss lock, `3600s` raw spacing, `15:45` flatten |
| `AxonTrade MGC Normal BreakEven Bot` | Built MGC normal-profitability study | `MGC` | Sim: `MGC_NORMAL_SIM`; live: `MGC_NORMAL_LIVE` | Controlled live routing approved for validated `1 MGC` setup | Exact `Allowed Trade Account` required only for live routing | `1 MGC`, `10` bar lookback breakout, Mon/Tue/Fri, `08:20-10:30`, abs delta `<=125`, `25 / 15`, stop to breakeven after `+20`, one trade/day, `$500` daily loss lock, `16:30` flatten |

Common live-capable setup gates:

- `Arm Execution = Yes` only after the chart, account, confirmation text, and
  routing mode are intentionally staged.
- `Allowed Trade Account` must exactly match the selected Sierra Trade Window
  account.
- The chart symbol must start with the required prefix.
- The bot must not be armed while Sierra is downloading historical data.
- No bot should be armed on broken, gapped, or untrusted chart data.
- Live routing requires Sierra trade simulation mode off unless a replay test
  deliberately disables the `Require Trade Simulation Mode Off` gate.

## Sierra Manual Steps

Use this sequence any time a new ACSIL build or live-capable study is staged.

1. Sync the source:
   `bash scripts/sync_to_sierra.sh`
2. In Sierra Chart, open `Analysis >> Build Custom Studies DLL`.
3. Select `AxonTradeVwapDeltaExecutionBot.cpp`.
4. Build the DLL.
5. Add only the intended study from the setup table above.
6. Confirm the chart symbol prefix, data quality, and that Sierra is not
   downloading historical data.
7. Confirm `Trade >> Trade Simulation Mode On` matches the intended mode:
   off for controlled live routing, on for sim/replay studies.
8. Set `Allowed Trade Account` to the exact selected Sierra Trade Window
   account for any live-capable study.
9. Set the exact bot confirmation text from the setup table.
10. Set quantity, max position quantity, daily locks, profit locks, and any
    eval trailing locks from the setup table.
11. Set `Send Orders To Trade Service = Yes` only for the intended live-capable
    study and only on the intended account.
12. Confirm no position and no working orders exist on the account/instrument.
13. Set `Arm Execution = Yes` only when the chart status banner shows all gates
    ready.

To stop a live-capable bot: flatten/cancel if needed, set
`Arm Execution = No`, then set `Send Orders To Trade Service = No`.

MNQ Top Runner live-staging checklist:

1. Add `AxonTrade MNQ Top Runner Live Bot` to a clean MNQ `3 Min` chart.
2. Set `Confirmation Text = MNQ_TOP_RUNNER_LIVE`.
3. Set `Allowed Trade Account` to the exact selected account.
4. Confirm Sierra trade simulation mode is off.
5. Confirm `Send Orders To Trade Service = Yes`.
6. Confirm `Quantity = 2`, `Max Position Quantity = 2`, and
   `Daily Loss Lock USD = 300`.
7. Confirm `Setup Start Time = 10:00:00`, `Setup End Time = 11:00:00`,
   `Directional Close Location Threshold = 0.9`, and
   `Minimum Signal Spacing Seconds = 3600`. The broader raw filter is fixed in
   code at `10:00-12:30` with raw close-location `0.65`.
8. Confirm no other automated MNQ bot is running on the same account.
9. Arm only when the banner reaches `ARMED - READY`.

## Scaling Roadmap

This is a planning roadmap, not a profit guarantee. It uses current repo
research plus a LucidFlex 25K rule snapshot checked on `2026-07-05`.
Rules, prices, data quality, and bot behavior can change; verify the account
rules in the dashboard before buying or arming anything.

Current external account assumptions:

- LucidFlex 25K evaluation: `$1,250` target, `$1,000` max loss, `50%`
  consistency, `20` micros max size, no evaluation daily loss limit, and no
  evaluation scaling restriction.
- LucidFlex funded 25K: max size starts at `10` micros at `$0-$999` simulated
  profit and rises to `20` micros after `$1,000` profit.
- Lucid allows automated systems and trade copiers when they comply with all
  rules.
- Lucid currently allows a maximum of `5` funded accounts per household.
- LucidFlex payout planning: `90%` trader split, `5` profitable days required
  per payout cycle, `$500` minimum payout request, and 25K max payout request
  of `50%` of profit up to `$1,000`.
- Account pricing is dynamic. Let `E` be the current one-time 25K evaluation
  checkout cost. A `5` account campaign needs `5E`; keep at least `2E` extra
  as reset/redo reserve before scaling aggressively.

Rule sources checked for this snapshot:
[LucidFlex evaluation](https://support.lucidtrading.com/en/articles/12945790-lucidflex-evaluation-account),
[consistency](https://support.lucidtrading.com/en/articles/12945805-lucidflex-consistency-percentage),
[drawdown](https://support.lucidtrading.com/en/articles/12945815-lucidflex-drawdown),
[scaling plan](https://support.lucidtrading.com/en/articles/12945808-lucidflex-scaling-plan),
[payouts](https://support.lucidtrading.com/en/articles/12945796-lucidflex-payouts),
[permitted activities](https://support.lucidtrading.com/en/articles/11404728-permitted-activities),
and [Lucid FAQ](https://lucidtrading.com/).

### Viability Call

The current path is viable as a staged prop-account portfolio if we scale by
account count and evidence gates, not by increasing contracts on one account.
It is not viable as an immediate guaranteed income machine.

Why it is viable enough to proceed:

- The MNQ A+B eval bot is specifically shaped for the 25K eval geometry and has
  controlled live-routing mechanics passed.
- Random-start eval simulation for the selected A+B policy showed `52.5%`
  pass, `5.5%` fail within `30` calendar days, with successful attempts taking
  median `17` calendar days and `3` trade days.
- Signal-start simulation was stronger: `85.2%` pass, `8.2%` fail, median
  `4` traded signals.
- MGC and MNQ normal-profitability bots provide a separate funded-stage path so
  we are not relying on one eval-only edge for all income.

Why scaling must stay conservative:

- The A+B eval bot has `-$1950` historical trade-sequence drawdown and can use
  `12 MNQ`; it is an eval-pass tool, not a funded day-zero income bot.
- The 25K funded scaling plan starts at `10` micros. The A+ side of the A+B bot
  can exceed that, so do not run the combined eval bot on a fresh funded 25K
  account.
- Normal bots still have historical drawdowns near the 25K max-loss envelope.
  Correlated losses across accounts can happen on the same market day.
- Backtest net scales cleanly on paper; live slippage, platform faults, broker
  routing, and payout withdrawals do not.

### Bot Roles

| Role | Primary Bot | Why | Do Not Use For |
| --- | --- | --- | --- |
| Eval acquisition | `AxonTrade MNQ Eval Pass Combined Bot` | Best current fit for `$1,250` target, `50%` consistency, and 25K max size | Fresh funded 25K accounts before scaling allowance and buffer |
| Eval backup | `AxonTrade MES Eval Live Bot` | Already guarded and live-approved with tight locks | Fastest pass plan; MES data quality has been unreliable |
| Funded survival | `AxonTrade MGC Normal BreakEven Bot` | Small `1 MGC` size, live staging passed, lower dollar risk per trade | Fast eval pass |
| Funded growth | `AxonTrade MNQ Eval Live Bot` | Positive MNQ-specific research and live mechanics passed | Running without account buffer or aggregate account risk lock |
| Future growth | `AxonTrade MNQ Top Runner Live Bot` | Strong normal-profitability candidate with lower-DD live build | Any unattended live use until live staging passes |

### Eval Account Campaign

Use `AxonTrade MNQ Eval Pass Combined Bot` as one combined bot per eval account.
Do not run separate A+ and B bots on the same account.

| Parallel 25K Evals | Fee Model | Chance At Least One Pass Within 30 Days | Expected Passes Within 30 Days | Expected Fails Within 30 Days | Use |
| ---: | ---: | ---: | ---: | ---: | --- |
| `1` | `1E` | `52.5%` | `0.53` | `0.06` | Pilot and operational validation |
| `2` | `2E` | `77.4%` | `1.05` | `0.11` | First scale step after pilot pass/clean operation |
| `3` | `3E` | `89.3%` | `1.58` | `0.17` | Practical early campaign size |
| `5` | `5E` | `97.6%` | `2.63` | `0.28` | Maximum household-funded-account target campaign |

Planning interpretation:

- First funded account: plan around `2-3` calendar weeks when the attempt
  passes; do not plan around a guaranteed two-day pass.
- Three funded accounts: plan around `30-45` calendar days if running multiple
  evals and operations are clean.
- Five funded accounts: plan around `60-90` calendar days, because one 30-day
  cycle is expected to leave some accounts still open or waiting for signal.
- If the first live eval shows platform/order/account issues, stop at one
  account until the issue is fixed. Do not multiply a broken operation.

### Funded Account Allocation

Phase 1: first funded account, zero buffer.

- Run only one approved low-risk normal bot at a time.
- Preferred first bot: `AxonTrade MGC Normal BreakEven Bot`.
- Goal: build `$500-$1000` account cushion and confirm payout-cycle operations.
- Do not run `MNQ Eval Pass Combined Bot` on a fresh funded 25K account.

Phase 2: account has `$500-$1000` cushion.

- Add `AxonTrade MNQ Eval Live Bot` only if account-level daily exposure remains
  below the current max-loss comfort zone.
- Keep total simultaneous micros within the funded scaling plan.
- Do not run more than one MNQ bot on the same account until the Top Runner live
  staging gate passes and the aggregate risk lock is reviewed.

Phase 3: portfolio mode.

- Target `3-5` funded accounts before increasing complexity.
- Prefer one main bot per account until there is enough forward evidence.
- Example conservative allocation at `5` accounts: `3` MGC accounts and `2`
  MNQ VWAP/delta accounts.
- Example balanced allocation after buffers: MGC plus MNQ VWAP/delta on each
  account, with account-level risk reviewed before arming.
- Add MNQ Top Runner only after controlled live staging passes.

### Income Model

These are planning rates from historical research, not promises.

| Bot / Stack | Current Status | Gross Planning Rate Per Account | Main Risk |
| --- | --- | ---: | --- |
| MGC Normal `1 MGC` | controlled live approved | about `$110/week` | slow growth |
| MNQ VWAP/delta `1+1 MNQ` | controlled live approved | about `$90-$110/week` | wide stop, near-`$1000` historical DD |
| MNQ Top Runner `2 MNQ` lower-DD | staging only | about `$95-$100/week` | not live-staging approved yet |
| MGC + MNQ VWAP/delta | buffer-required stack | about `$200-$225/week` | combined account drawdown |
| MGC + MNQ VWAP/delta + Top Runner | future stack | about `$295-$325/week` | needs Top Runner live approval and aggregate risk lock |

Approximate trader-side profit time after a full `5` funded accounts are active,
using the `90%` split and ignoring payout-processing delays:

| Trader Profit Goal | Conservative `5` Accounts, One Bot Each | Balanced `5` Accounts, MGC + MNQ | Future `5` Accounts With Top Runner |
| ---: | ---: | ---: | ---: |
| `$5,000` | `70-84` calendar days | `35-42` calendar days | about `28` calendar days |
| `$10,000` | `133-161` calendar days | `70-84` calendar days | about `56` calendar days |
| `$25,000` | `336-392` calendar days | `175-196` calendar days | about `133` calendar days |
| `$50,000` | `672-784` calendar days | `350-392` calendar days | about `259` calendar days |

Cash payout timing can be slower than account-profit timing. On 25K LucidFlex,
each account needs `5` profitable days per payout cycle, and the max request is
`50%` of profit up to `$1,000` gross per account. A five-account fleet can
request at most `$5,000` gross per payout cycle, paid as about `$4,500` to the
trader before any external fees or taxes.

### Operating Rules For Scaling

- Scale accounts before contract size.
- One broken chart, data feed, DLL setting, or account whitelist mistake stops
  the whole campaign.
- Never arm multiple bots on the same account unless the combined worst-case
  open risk and daily lock are explicitly reviewed.
- Do not promote a bot from staging to income allocation until it has controlled
  live staging evidence.
- Use account-level stop policy outside Sierra if the firm dashboard supports
  it; bot-level locks do not know every other bot's P/L unless we explicitly
  build an aggregate risk layer.
- After every payout or reset, recheck funded scaling tier before arming.

## Bot Inventory

### MES Eval Live Bot

`AxonTrade MES Eval Live Bot` is the guarded live-capable prop-eval bot exported
from `src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`.

Strengths:

- ES-derived VWAP/delta exhaustion setup with accepted historical research.
- Sierra mechanics test passed on live feed.
- Live routing requires `MES_EVAL_LIVE`, exact account whitelist, simulation
  mode off, route-on gate, arm gate, symbol gate, historical-download guard, and
  chart status banner.
- Evaluation controls are explicit: `$240` daily loss lock, `$650` daily profit
  lock, `$1000` eval trailing drawdown lock.

Weaknesses:

- MES data/backfill quality has been unreliable under some Sierra/Rithmic
  combinations, so chart data quality remains an operating gate.
- Evaluation risk limits are tight; the bot is risk-controlled, not optimized
  for the fastest possible two-day pass.
- Forward live sample is still small.

Primary docs:

- [MES live setup](docs/sierra-vwap-delta-mes-eval-live-bot.md)
- [strategy outline](docs/strategy-outline.md)

### ES Simulation Execution Bot

`AxonTrade VWAP Delta Execution Bot` is the simulation-only ES replay/mechanics
study from the same ACSIL source.

Strengths:

- Strongest ES historical research path remains useful for mechanics and
  parameter translation.
- Live trade-service routing is rejected by design unless using the separate
  live-eval exports.

Weaknesses:

- ES sizing is not suitable for the `$1000` eval drawdown constraint.
- Simulation evidence does not replace MES/MNQ live-routing validation.

Primary docs:

- [ES sim execution bot](docs/sierra-vwap-delta-execution-bot.md)
- [accepted ES research](reports/sierra-vwap-delta-execution-bot-space300-7-12-10-primary.md)

### MNQ Eval Live Bot

`AxonTrade MNQ Eval Live Bot` is the guarded MNQ live-capable export in
`AxonTradeVwapDeltaExecutionBot.cpp`.

Strengths:

- Separate MNQ-sized VWAP/delta research lead, not a copied ES/MES setup.
- Best local lead: `80pt_400d_cl0.4`, no Friday and no `11:00`/`15:00`
  entries, exit `25 / 140 / 40 / initial`.
- Research sample: `186` trades, `$9584.50` net, `2.09` profit factor,
  `-$976` max realized drawdown, positive `2024`, `2025`, and `2026`.

Weaknesses:

- Stop is wide at `140` MNQ points.
- It is a profitability research lead, not specifically optimized for the
  fastest eval pass.
- Live test/mechanics passed on `2026-07-05`; keep the validated sizing and
  routing gates until forward sample justifies changes.

Primary docs:

- [MNQ live setup](docs/sierra-vwap-delta-mnq-eval-live-bot.md)
- [MNQ VWAP/delta research](reports/mnq-vwap-delta-expanded-720d-research.md)

### MNQ Eval-Pass Combined Bot

`AxonTrade MNQ Eval Pass Combined Bot` is the ACSIL implementation of the MNQ
eval-pass wave-rider research. It is built in
`src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`, and live test/mechanics passed
on `2026-07-05`. It is approved for controlled live routing under the documented
MNQ eval gates.

- [research script](scripts/run_mnq_eval_pass_wave_rider.py)
- [research report](reports/mnq-eval-pass-wave-rider-research.md)
- [slippage stress](reports/mnq-eval-pass-wave-rider-slippage-stress.md)
- [walk-forward](reports/mnq-eval-pass-wave-rider-walk-forward.md)
- [deep search](reports/mnq-eval-pass-wave-rider-deep-search.md)
- [new lead refinement](reports/mnq-eval-pass-wave-rider-new-lead-refine.md)
- [cadence refinement](reports/mnq-eval-pass-wave-rider-cadence-refine.md)
- [cadence validation](reports/mnq-eval-pass-wave-rider-cadence-validation.md)
- [trailing refinement](reports/mnq-eval-pass-wave-rider-trailing-refine.md)
- [trailing walk-forward](reports/mnq-eval-pass-wave-rider-trailing-walk-forward.md)
- [trailing candidate review](reports/mnq-eval-pass-wave-rider-trailing-candidate-review.md)
- [combined A+B research](reports/mnq-eval-pass-combined-ab.md)
- [Sierra combined bot setup](docs/sierra-mnq-eval-pass-combined-bot.md)

It directly targets the LucidFlex-style `25K` eval geometry: `$1250` profit
target, `-$1000` max loss, `50%` consistency, ideally around `$625-$700` on two
traded days.

Current combined build candidate:

- policy: `ab_earliest_one_per_day_fast`
- implementation shape: one combined bot, A+ and B signals both enabled, exactly
  one trade per day, earliest valid signal wins, exact same-bar ties choose B
  for lower per-trade risk
- sample: `122` trades, `36` A+ trades, `86` B trades
- full sample: `$28988` net, `62.3%` win rate, `2.29` PF,
  `-$1950` max trade-sequence drawdown
- eval shape from random calendar starts: `52.5%` pass, `5.5%` fail within the
  `30` calendar-day horizon; successful attempts had median `17` calendar days
  and `3` trade days to pass
- eval shape from valid signal starts: `85.2%` pass, `8.2%` fail, median `21.5`
  calendar days and `4` traded signals to pass
- frozen holdout: `120x40`, `180x40`, and `240x60` holdout slices all stayed
  positive; calendar pass ranged `52.2%` to `57.5%`
- rough planning estimate: when it passes, expect about `2-3` calendar weeks
  from a random start; this is not a guaranteed two-day pass

Decision: run this as one combined MNQ eval-pass bot under controlled live
routing. Do not run separate A+ and B bots on the same account/instrument, and
do not take every signal from both modules. The rejected take-all policy had
higher calendar pass but pushed calendar fail to `10.1%`.

Sparse A+ standalone lead:

- strategy:
  `lookback_breakout_deep:lb40:buf2.5:delta600:cl0.5:start1000:end1230:skipfri0:filterabs1000`
- practical version: `12 MNQ`, target/stop about `$726 / $750`
- full sample: `43` trades, `$14982` net, `2.82` PF, `-$1500` max trade-sequence
  DD, worst quarter `-$24`
- latest year: `9` trades, `+$3582` net
- original fixed-loss eval shape: `90.7%` signal-start pass, `51.2%` two-day
  pass, `2.3%` fail; trailing signal-start fail is `4.7%` in the combined
  comparison
- stress: through `6` total slippage ticks per contract, target/stop degrades to
  about `$696 / $780` while pass/two-day/fail remain `90.7% / 51.2% / 2.3%`

Decision: strongest standalone A+ quality lead, but superseded as the build
target by the combined A+B policy. The older `5 MNQ` `$650/$650` row remains a
conservative fallback. Higher-quantity rows can pass faster on paper, but
planned stops above `$800` are treated as aggressive because the eval max loss
is only `-$1000`.

Walk-forward result: adaptive parameter selection fails badly, but locked
candidate benchmarks are materially better and positive across the tested
chronological holdout windows. Continue only by freezing one candidate family;
do not build an adaptive optimizer from this pass.

Faster-cadence B setup under validation:

- strategy: `cadence_trailing:tue_wed:short:1000_1230:none`
- practical version: `4 MNQ`, target/stop about `$650 / $450`
- full sample: `86` trades, `$16136` net, `-$1800` max trade-sequence DD,
  worst quarter `-$500`
- trailing eval shape: `38.9%` calendar-start pass, `3.2%` calendar-start fail,
  `80.2%` signal-start pass, `15.1%` signal-start fail, median `2` traded days
  from random calendar starts and `4` traded days from signal starts
- frozen walk-forward: `120x40`, `180x40`, and `240x60` holdout slices all
  stayed positive, with `37.2%` to `48.3%` trailing calendar pass and `4.4%` to
  `6.7%` trailing calendar fail
- all-candidate frozen leaderboard: ranked `#1` of `6336` faster B rows under
  the robustness screen; the `1000_1130` variant ranked `#2` with identical
  holdout behavior
- defensive fallback: `4 MNQ` `$500/$450` lowers trailing fail to `0.0%` and
  trade-sequence drawdown to `-$1250`, but usually needs more than two winning
  trades to pass
- decision: best faster B research lead after applying the trailing drawdown
  floor; freeze this row if testing it, do not build an adaptive optimizer

### MNQ Top-Runner Lookback Candidate

This is the active MNQ normal-profitability research lead after explicitly
skipping the breakeven-frequency path. It now has a simulation/replay ACSIL
study, but it is not approved for live routing.

- [first-pass scan](reports/mnq-top-runner-research.md)
- [refinement](reports/mnq-top-runner-refine.md)
- [frozen validation](reports/mnq-top-runner-validation.md)
- [deep validation](reports/mnq-top-runner-deep-validation.md)
- [mechanics validation](reports/mnq-top-runner-mechanics-validation-2026-07-05.md)
- [Sierra sim/replay setup](docs/sierra-mnq-top-runner-sim-bot.md)
- [Sierra live setup](docs/sierra-mnq-top-runner-live-bot.md)

Current lead:

- family: filtered `20` bar lookback breakout, continuation direction, no Friday
- raw setup: `10:00-12:30`, delta `600`, raw close-location `>= 0.65`,
  one-hour raw setup spacing
- final tradable filter: `10:00-11:00`, directional close-location `>= 0.9`
- exits: fixed target/stop with session flatten; no breakeven/eval geometry
- high-PF reference: `2 MNQ`, `160 / 70` points, `87` trades, `$11772` net,
  `2.15` PF, `54.0%` win rate, `-$1854` max trade-sequence DD, `$7089`
  latest-year net
- lower-DD reference: same signal/filter with `120 / 70`, `$10135` net, `2.08`
  PF, `-$1146` DD
- higher-sample reference: close-location `>= 0.8` with `160 / 70`, `158`
  trades, `$17334` net, `1.86` PF, `-$1811` DD
- slippage stress through `6` total ticks per contract stayed positive for all
  three frozen variants
- rolling holdout stayed mostly positive across `120x40`, `180x40`, and
  `240x60` trade-date windows
- deep validation added `8/10/12` tick slippage stress, wider holdouts,
  period attribution, Monte Carlo trade-order risk, parameter-neighborhood
  checks, and candidate overlap

Sierra implementation:

- study name: `AxonTrade MNQ Top Runner Sim Bot`
- confirmation text: `MNQ_TOP_RUNNER_SIM`
- CSV log path: `C:\SierraChart\Data\AxonTrade_MnqTopRunnerSimBot.csv`
- mode: simulation/replay only; live trade-service routing is rejected
- default build variant: filtered high-PF `2 MNQ`, `160 / 70`, final
  close-location `0.9`
- fresh replay/mechanics validation passed on `2026-07-05` after the
  filtered-rule alignment

Live-capable implementation:

- study name: `AxonTrade MNQ Top Runner Live Bot`
- confirmation text: `MNQ_TOP_RUNNER_LIVE`
- CSV log path: `C:\SierraChart\Data\AxonTrade_MnqTopRunnerLiveBot.csv`
- default live staging variant: lower-DD `2 MNQ`, `120 / 70`,
  final close-location `0.9`
- default daily loss lock: `$300`, roughly one full `2 MNQ` stop before costs
- routing gates: route-on, Sierra sim mode off, exact account whitelist,
  symbol prefix, confirmation text, data-download guard, no position/working
  orders

Implementation alignment finding: the strongest frozen research used a
two-stage filtered signal. A direct `close-location 0.9` implementation tested
worse (`120` trades, `$8635` net, `1.57` PF, `-$1712` DD for `120 / 70`) than
the filtered frozen lower-DD row (`87` trades, `$10135` net, `2.08` PF,
`-$1146` DD). The ACSIL Top Runner studies now implement the filtered rule.

Decision: offline research on this family is complete for the current export,
and the aligned sim/replay mechanics gate has passed. The lower-DD live build
exists, but controlled live staging has not passed for the aligned
implementation. Do not treat it as approved unattended live automation until
that gate is recorded.

### MNQ Breakeven-Frequency Candidate (Parked)

This is a research-only MNQ risk-management candidate. It is not implemented as
an ACSIL bot and is not approved for live routing.

- [baseline scan](reports/mnq-breakeven-frequency-research.md)
- [filter refinement](reports/mnq-breakeven-frequency-refine.md)
- [risk refinement](reports/mnq-breakeven-frequency-risk-refine.md)
- [candidate validation](reports/mnq-breakeven-frequency-candidate-validation.md)
- [fixed holdout](reports/mnq-breakeven-frequency-walk-forward.md)

Parked reference:

- signal: short-only MNQ lookback continuation,
  `lb20 / buf2.5 / delta600 / cl0.55 / end12:30 / skip Friday`
- filter: directional VWAP distance `<= 120`
- management: first target `30`, initial stop `50`, runner target `120`, move
  runner stop to breakeven after target one
- balanced reference: `3 MNQ`, split `2+1`, `128` trades, `$5235.50` net,
  `1.54` PF, `75.0%` target-one reach, `-$1249.50` max trade-sequence DD
- growth reference: `4 MNQ`, split `3+1`, `$7603.50` net, `1.59` PF,
  `-$1624` max trade-sequence DD
- slippage stress through `6` ticks stayed positive on `2`, `3`, and `4` MNQ
- fixed `240x60` holdouts were positive; shorter `40`-day holdouts remained
  noisy with losing windows

Decision: parked by user decision on `2026-07-05`. Do not spend more time on
this path unless it is explicitly revived.

### MGC Normal BreakEven Bot

`AxonTrade MGC Normal BreakEven Bot` is the ACSIL implementation of the frozen
MGC lookback-breakout lead. It is built as a full Sierra execution study and
both mechanics validation and live staging have passed. It is approved for
controlled `1 MGC` live routing under the documented gates, not unattended
deployment.

Perks:

- normal-profitability bot, not an eval-pass consistency-rule bot
- `1 MGC` default sizing keeps risk granular while still using the gold futures
  behavior found in research
- simple fixed rule: no adaptive optimizer, no hidden retraining
- one trade per chart date, so it avoids runaway signal stacking
- target/stop/BE management is attached to the parent order: `25` point target,
  `15` point stop, stop to breakeven after `+20` favorable points
- chart status banner shows arm/routing/simulation/account/symbol/data/risk
  gates
- separate confirmation texts for sim and controlled live routing:
  `MGC_NORMAL_SIM` and `MGC_NORMAL_LIVE`
- CSV event log plus submitted-trade levels and bot fill markers on the chart
- replay/mechanics validation passed on `2026-07-05`
- supervised live staging passed on `2026-07-05`

Sierra setup:

- study name: `AxonTrade MGC Normal BreakEven Bot`
- source file: `src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`
- Sierra source path after sync:
  `C:\SierraChart\ACS_Source\AxonTradeVwapDeltaExecutionBot.cpp`
- setup doc: [MGC Sierra setup](docs/sierra-mgc-normal-break-even-bot.md)
- replay/sim confirmation: `MGC_NORMAL_SIM`
- live confirmation: `MGC_NORMAL_LIVE`
- CSV log path:
  `C:\SierraChart\Data\AxonTrade_MgcNormalBreakEvenBot.csv`
- symbol prefix: `MGC`
- chart requirement: clean `1 Min` MGC order-flow chart with bid/ask volume
  available
- sim/replay mode: `Send Orders To Trade Service = No`, Sierra trade simulation
  mode on, `Confirmation Text = MGC_NORMAL_SIM`
- controlled live mode: `Send Orders To Trade Service = Yes`, Sierra trade
  simulation mode off, `Confirmation Text = MGC_NORMAL_LIVE`, and `Allowed
  Trade Account` exactly matching the selected Sierra Trade Window account

Core default inputs:

- `Arm Execution = No` by default
- `Quantity = 1`
- `Max Position Quantity = 1`
- `Setup Start Time = 08:20:00`
- `Setup End Time = 10:30:00`
- `Flatten Time = 16:30:00`
- `Lookback Bars = 10`
- `Buffer Points = 0`
- `Delta Threshold = 0`
- `Directional Close Location Threshold = 0.45`
- `Max Absolute Delta = 125`
- `Target Points = 25`
- `Stop Points = 15`
- `Break Even Trigger Points = 20`
- `Break Even Offset Ticks = 0`
- `Daily Loss Lock USD = 500`
- `Daily Profit Lock USD = 0`, disabled

Research status:

MGC is being researched as a normal profitability bot, not an eval-pass bot.

Primary docs:

- [MGC export quality](reports/mgc-orderflow-export-quality.md)
- [normal scan](reports/mgc-normal-bot-research.md)
- [normal refinement](reports/mgc-normal-bot-refine.md)
- [slippage stress](reports/mgc-normal-bot-stress.md)
- [comprehensive normal scan](reports/mgc-comprehensive-normal-search.md)
- [lookback breakout refinement](reports/mgc-lookback-breakout-refine.md)
- [lookback breakout slippage stress](reports/mgc-lookback-breakout-stress.md)
- [lookback breakout walk-forward](reports/mgc-lookback-breakout-walk-forward.md)
- [lookback breakout candidate review](reports/mgc-lookback-breakout-candidate-review.md)
- [lookback breakout robustness](reports/mgc-lookback-breakout-robustness.md)
- [lookback trade management](reports/mgc-lookback-trade-management.md)
- [lookback break-even sensitivity](reports/mgc-lookback-breakeven-sensitivity.md)
- [lookback context stress](reports/mgc-lookback-context-stress.md)

Current higher-frequency offline lead:

- strategy:
  `mgc_lb_be_sensitivity:lb10:buf0:cl0.45:end1030:mtf:delta125:breakeven:t25:s15:trig20`
- source sample: `813388` one-minute rows, `2024-03-17` through `2026-07-03`
- signal sample: `343` trades, one trade per day, Monday/Tuesday/Friday only
- exits: `25` point target, `15` point initial stop, move stop to breakeven
  after `+20` points
- `1 MGC`: `$13298` net, `$38.77` average/trade, `1.76` PF, `-$677`
  max trade-sequence drawdown, `+$6046` latest-year net, `+$5208` recent
  120 trade-day net, `-$397` worst quarter
- rolling frozen holdout, using `120x40`, `180x40`, and `240x60` trade-date
  windows: `$32533` aggregate holdout net, `1.97` holdout PF, `25 / 26`
  positive windows, `-$141` worst holdout window
- slippage stress at `6` total slippage ticks/contract stays positive:
  `$11583` full-sample net, `1.64` PF, `+$5666` latest-year net, `+$4858`
  recent 120 trade-day net, `$29283` aggregate holdout net, `1.84` holdout PF,
  `25 / 26` positive holdout windows, and `-$261` worst holdout window
- broad search context: `7` families and `2511` compact variants were tested;
  lookback breakout was the only family that improved sample size and stayed
  close enough to refine
- adaptive walk-forward selection is rejected: the fixed lead held up, but
  adaptive selection produced negative aggregate holdout net on the `180x40`
  and `240x60` views
- weekday filtering is a fixed research rule here, not an adaptive scheduler:
  Wednesday and Thursday were excluded after context diagnostics showed them as
  persistent drag buckets in this export
- fixed-exit robustness kept the older `delta100` row, but the later
  trade-management pass found a stronger break-even family
- sensitivity screen around the break-even lead keeps the `cl0.45/end1030/
  delta125` row as the practical replacement: it improves net, PF, drawdown,
  latest-year net, recent 120 trade-day net, and aggregate holdout versus the
  old fixed-exit baseline under both base and six-tick stress cost
- context stress did not promote any extra live-rule exclusion; weak buckets
  include Tuesday, early `2024`, VWAP distance `2-5`, day range below `10`, and
  entry-bar absolute delta `50-75`, but exclusions that improved one metric
  either reduced full-sample net or worsened holdout quality
- higher-net growth variant to monitor:
  `mgc_lb_be_sensitivity:lb10:buf0:cl0.45:end1045:mtf:delta125:breakeven:t25:s15:trig20`
  with `$13449` base net and `$11714` stress net, but worse max drawdown
  than the `10:30` risk-balanced row

Secondary lower-frequency quality lead:

- strategy:
  `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:none`
- signal sample: `116` trades
- fixed exits: `30` point target, `15` point stop
- `1 MGC`: `$3880` net, `$33.45` average/trade, `49.1%` win rate, `1.50`
  PF, `-$790` max trade-sequence drawdown, `+$1608` latest-year net,
  `+$1468` recent 120 trade-day net, `-$177` worst quarter
- slippage stress at `6` total slippage ticks/contract still holds: `1 MGC`
  `$3300` net, `1.41` PF, `+$1408` latest-year net, `+$1293` recent 120
  trade-day net

Decision: MGC now has a serious fixed-rule offline candidate and a matching
ACSIL implementation with a simple break-even management rule. Sierra mechanics
validation and supervised live staging have passed. It is approved for
controlled `1 MGC` live routing with clean chart data, exact account whitelist,
`MGC_NORMAL_LIVE`, Sierra simulation mode off, and no other automated bot on the
same account/instrument. The next evidence gate is monitored forward sample,
not size increase.

## Operating Rules

- `AxonTrade MES Eval Live Bot` is approved for controlled live routing.
- `AxonTrade MNQ Eval Live Bot` is approved for controlled live routing under
  its documented `MNQ_EVAL_LIVE` gates.
- `AxonTrade MNQ Eval Pass Combined Bot` is approved for controlled live routing
  under its documented `MNQ_EVAL_PASS_AB_LIVE` gates.
- `AxonTrade MNQ Top Runner Sim Bot` is simulation/replay-only and rejects live
  trade-service routing.
- `AxonTrade MNQ Top Runner Live Bot` is live-capable for controlled staging
  only; it is not approved for unattended live operation yet.
- `AxonTrade MGC Normal BreakEven Bot` is approved for controlled `1 MGC` live
  routing under its documented gates.
- `AxonTrade VWAP Delta Execution Bot` remains simulation-only.
- No bot is armed on broken or gapped chart data.
- Development logs, decision logs, and markdown reports are durable evidence.
- Large CSV exports, sweeps, and audits are generated artifacts unless promoted
  intentionally.

## Platform Stack

- Sierra Chart for charts, replay, trade routing, and ACSIL studies.
- ACSIL C++ for chart-side studies, visual state, and guarded order routing.
- Python for offline research, export validation, sweeps, and reports.
- YAML for profile/risk/instrument configuration.
- Pop!_OS Linux with Sierra Chart under Wine as the target workstation.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
bash scripts/check_repo.sh
```

## Sierra Sync

The sync script copies ACSIL sources into Sierra Chart. It does not compile,
launch Sierra Chart, or place orders.

```bash
export WINEPREFIX="/home/saulius/WinePrefixes/SierraChart"
bash scripts/sync_to_sierra.sh
```

## Repo Map

- [architecture](docs/architecture.md)
- [strategy outline](docs/strategy-outline.md)
- [decision log](docs/decision-log.md)
- [acceptance gates](docs/acceptance-gates.md)
- [research methodology](docs/research-methodology.md)
- [repo hygiene](docs/repo-hygiene.md)
- [Sierra export workflow](docs/sierra-export-workflow.md)
- [Pop!_OS and Wine setup](docs/popos-wine-setup.md)

## Safety Status

The only approved ACSIL order-routing source is
`src/acsil/AxonTradeVwapDeltaExecutionBot.cpp`.

Live routing is allowed only through explicitly live-capable exports with all
gates passing. At this snapshot, approved controlled live-routing exports are
`AxonTrade MES Eval Live Bot`, `AxonTrade MNQ Eval Live Bot`,
`AxonTrade MNQ Eval Pass Combined Bot`, and
`AxonTrade MGC Normal BreakEven Bot`.

`AxonTrade MNQ Top Runner Live Bot` is present as a controlled live-staging
candidate, not as approved unattended automation. `AxonTrade MNQ Top Runner Sim
Bot` remains simulation/replay-only.
