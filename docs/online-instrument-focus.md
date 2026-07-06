# Online Instrument Focus

Status date: `2026-07-06`

Branch: `research/online-instrument-focus`

Purpose: choose the single No. 1 instrument family for the next research phase,
using both current online market/account facts and our existing AxonTrade
research evidence.

## Decision

Primary focus: `NQ/MNQ`, executed as `MNQ` for prop evaluation and early funded
accounts.

Secondary stabilizer: `MGC`.

Do not make `MES`, `MCL`, `M2K`, `MYM`, FX, crypto, or full-size futures the
primary focus yet.

This is not because those markets cannot be traded. It is because the current
goal is narrower: find the best instrument for bot trading activity, passing
LucidFlex-style evaluations, and then compounding into funded-account wealth.
Under that combined objective, MNQ is the best current match.

## Why MNQ Wins

MNQ is the only instrument family where all four pieces line up at the same
time:

- strong online market structure: MNQ is the micro version of the highly liquid
  NQ contract, with small tick granularity and enough volatility to make
  meaningful evaluation progress;
- prop-account fit: LucidFlex 25K allows up to `20` micros during evaluation,
  with `$1250` target, `$1000` max loss, and `50%` consistency;
- existing repo evidence: we already have three distinct MNQ research tracks,
  including one eval-pass policy and two normal-profitability candidates;
- scaling path: MNQ can run on small accounts now, while the same research can
  later inform NQ/full-size logic after account size and risk budget improve.

MGC is stronger as a funded-account stabilizer, but it is slower for evaluation
passing. MES has broad market quality but our current MES path is weaker and
has had data/provider reliability problems. MCL has attractive movement and low
commission but has no local AxonTrade research base yet and carries larger
event-risk uncertainty.

## Scoring Model

Weights:

- bot trading activity: `25`
- eval passing fit: `30`
- wealth accumulation fit: `25`
- AxonTrade research readiness: `15`
- operational/data reliability: `5`

| Rank | Instrument Family | Score | Bot Activity | Eval Fit | Wealth Fit | Research Ready | Ops/Data | Decision |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `NQ/MNQ` | `88` | `23` | `27` | `23` | `12` | `3` | Primary focus |
| 2 | `GC/MGC` | `65` | `18` | `12` | `17` | `14` | `4` | Secondary funded stabilizer |
| 3 | `ES/MES` | `60` | `18` | `17` | `15` | `8` | `2` | Keep as backup only |
| 4 | `CL/MCL` | `58` | `20` | `16` | `19` | `0` | `3` | Future exploratory branch after MNQ |
| 5 | `RTY/M2K`, `YM/MYM` | `41` | `14` | `12` | `12` | `0` | `3` | Not first |
| 6 | FX futures | `28` | `10` | `8` | `8` | `0` | `2` | Not first |
| 7 | Crypto futures | `20` | `14` | `2` | `4` | `0` | `0` | Not a Lucid-approved base in current source set |

The score is deliberately practical, not academic. A market with beautiful
global volume but no clean data, no prop-account fit, or no current AxonTrade
edge does not outrank a market we can actually research, validate, route, and
scale.

## Current AxonTrade Evidence

### MNQ

Research tracks already in repo:

- `AxonTrade MNQ Eval Pass Combined Bot`: eval-pass A+B wave-rider.
  Research sample: `$28988` net, `2.29` PF, `62.3%` win rate, about `1.2`
  trades/week. Random-start eval pass simulation: `52.5%` pass within `30`
  calendar days; signal-start pass simulation: `85.2%` pass.
- `AxonTrade MNQ Eval Live Bot`: VWAP/delta profitability lead.
  Final live-sequenced baseline: `166` executable trades, `$8897` net, `2.12`
  PF, `82.5%` win rate, `-$924.50` chronological DD, about `1.6`
  trades/week.
- `AxonTrade MNQ Top Runner Live Bot`: normal-profitability runner candidate.
  Research sample: `$10135` net, `2.08` PF, `57.5%` win rate, about `0.85`
  trades/week. Fresh replay/mechanics passed; live staging still required.

Interpretation: MNQ has the deepest current AxonTrade portfolio. It already has
an eval-specific candidate, a higher-win-rate VWAP/delta candidate, and a
runner-style candidate. That makes it the best instrument for a dedicated,
online-assisted research push.

### MGC

Current bot:

- `AxonTrade MGC Normal BreakEven Bot`: `343` trades, `$13298` net, `1.76` PF,
  `55.4%` win rate, `-$677` chronological DD, about `2.9` trades/week.

Interpretation: MGC is currently the best lower-size funded survival/growth
instrument. It is not the best No. 1 eval instrument because the edge is slower
and smaller per trade.

### MES

Current bot:

- `AxonTrade MES Eval Live Bot`: `$66584` net, `1.30` PF, `60.9%` win rate,
  about `5.8` trades/week.

Interpretation: MES has trade frequency, but the PF is much weaker and the
recent Sierra/provider data quality issues reduce confidence. Keep MES as a
backup, not the primary research focus.

## Online Facts Checked

Sources checked on `2026-07-06`:

- CME MNQ page:
  `https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.html`
- CME NQ page:
  `https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.html`
- CME MES page:
  `https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.html`
- CME MGC page:
  `https://www.cmegroup.com/markets/metals/precious/e-micro-gold.html`
- CME MCL page:
  `https://www.cmegroup.com/markets/energy/crude-oil/micro-wti-crude-oil.html`
- CME CL page:
  `https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.html`
- LucidFlex evaluation rules:
  `https://support.lucidtrading.com/en/articles/12945790-lucidflex-evaluation-account`
- LucidFlex consistency:
  `https://support.lucidtrading.com/en/articles/12945805-lucidflex-consistency-percentage`
- LucidFlex scaling:
  `https://support.lucidtrading.com/en/articles/12945808-lucidflex-scaling-plan`
- Lucid approved products and commissions:
  `https://support.lucidtrading.com/en/articles/11508978-approved-products-and-commissions`
- Lucid permitted activities:
  `https://support.lucidtrading.com/en/articles/11404728-permitted-activities`

Key points from the online check:

- MNQ is `$2 x Nasdaq-100` with `0.25` point minimum tick, so one tick is
  `$0.50`.
- MES is `$5 x S&P 500` with `0.25` point minimum tick, so one tick is `$1.25`.
- MGC is `1/10` the size of benchmark GC and is explicitly positioned as
  smaller-margin gold exposure.
- MCL is `1/10` the size of benchmark WTI and gives `100` barrel increments.
- NQ and ES both have deep liquidity and tight-spread claims from CME; NQ also
  carries enough movement to make MNQ useful for prop-account eval geometry.
- LucidFlex 25K currently shows `$1250` target, `$1000` max loss, `50%`
  consistency, and `20` micros max size.
- Lucid lists MNQ/MES/M2K/MYM/MCL at `$0.50` per side, MGC at `$0.80` per
  side, and full-size NQ/ES at `$1.75` per side.
- Lucid permits automated strategies and trade copiers as long as they comply
  with all rules.

## Rejection Notes

### Why Not MGC As No. 1

MGC is currently our best stabilizer, but not the best primary growth engine.
The current research is strong and robust, yet its role is slower compounding:
lower weekly net, lower eval velocity, and less evidence for a two-to-four-day
pass objective. Keep it as the first funded-account stabilizer and a portfolio
diversifier.

### Why Not MES As No. 1

MES has excellent market structure and smaller point risk than MNQ, but current
AxonTrade evidence is less attractive: lower PF, ES-derived logic, and recent
broker/data backfill issues. MES remains useful as a backup and a comparison
market, not as the next main research commitment.

### Why Not MCL As No. 1

MCL is interesting. It has low per-side commission, enough movement, and the
full CL market is extremely liquid. The problem is zero local research readiness
and larger event specificity: inventory releases, OPEC headlines, geopolitical
oil shocks, and contract behavior need their own data and controls. MCL should
be a future exploratory branch after MNQ is exhausted.

### Why Not Full-Size NQ/ES/GC/CL

Full-size contracts are not the first executable path under a `$1000` max loss
eval. They are future scaling instruments. The correct sequence is:

1. research and route MNQ safely;
2. build funded-account cushion and multi-account process;
3. only then consider NQ/full-size translation.

## Research Protocol For The New Direction

The next MNQ phase should use more online context without turning the bot into
a news-chasing discretionary system.

Use online data for:

- instrument ranking and rule changes;
- scheduled event labels: CPI, FOMC, NFP, Fed speakers, treasury auctions,
  major tech earnings windows;
- current contract, rollover, and volume/open-interest sanity checks;
- volatility regime labels from public sources where available.

Do not use online data for:

- curve-fitting one news day;
- overriding tested risk limits manually;
- adding discretionary "headline interpretation" to live routing.

## Next Work Items

1. Build an `MNQ Online Context Pack`:
   - source list;
   - event/calendar labels;
   - contract rollover notes;
   - volume/open-interest snapshot notes;
   - Lucid rule snapshot.
2. Re-run MNQ strategy family research with context columns:
   - existing A+B wave-rider;
   - VWAP/delta;
   - top-runner breakout;
   - opening-range breakout/reversal;
   - trend-day continuation;
   - volatility-compression expansion.
3. Promote only candidates that beat the current MNQ portfolio on a combined
   score:
   - PF;
   - net;
   - chronological and Monte Carlo drawdown;
   - pass-rate geometry;
   - trade cadence;
   - slippage stress;
   - live implementation simplicity.
4. Keep MGC running as the stabilizer track while MNQ research continues.

## Current Operating Recommendation

Make `MNQ` the main research and execution instrument for the next phase.

Keep `MGC` as the funded survival/growth stabilizer.

Do not spend serious time on MCL, M2K, MYM, FX, or crypto until the MNQ online
context phase either produces a stronger candidate or clearly stalls.
