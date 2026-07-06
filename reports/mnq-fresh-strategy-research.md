# MNQ Fresh Strategy Research

Status: first fresh-angle MNQ strategy-family sweep, deliberately not bound by the prior bot families.

## Objective

Find a candidate family with all of the following qualities:

- stable profitability;
- high trade frequency;
- low chronological drawdown;
- high profit factor;
- simple enough to implement safely in Sierra Chart.

The first-pass promotion lens is intentionally strict: at least `200` trades, at least `2` trades/week, positive full-sample and latest-year net, PF `>= 1.6`, drawdown better than `-$1000`, and worst quarter better than `-$750`.

## Online Research Input

The fresh sweep is built around strategy families supported by external market/research evidence:

- CME describes NQ/MNQ as liquid Nasdaq-100 futures products with nearly 24-hour access and tight-spread/deep-liquidity characteristics.
- Opening-range breakout and timely opening-range breakout research motivates testing NY cash-open breakout and failed-breakout families.
- Intraday momentum/noise-area research motivates testing a rolling time-of-day noise band instead of fixed price thresholds.
- Order-flow imbalance literature motivates keeping delta/close-location confirmations in the family tests.

Primary online sources are listed in `docs/online-instrument-focus.md`; this report uses them only to choose strategy families, not to claim profitability.

Specific source URLs used for this pass:

- CME NQ overview: `https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.html`
- CME MNQ overview: `https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.html`
- CME Nasdaq futures page: `https://www.cmegroup.com/markets/equities/nasdaq.html`
- Opening-range breakout paper index: `https://ideas.repec.org/p/hhs/umnees/0845.html`
- Intraday momentum paper: `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172`
- Market intraday momentum futures paper: `https://academicweb.nd.edu/~zda/intramom.pdf`
- Order-flow imbalance / price impact: `https://arxiv.org/abs/1011.6402`

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique trading dates: `507`
- instrument: `MNQ`, point value `$2`, tick value `$0.50`
- base cost model: `$0.50/side` commission plus `1` total slippage tick per contract

## Families Tested

| Family | Raw Strategy Sets | Raw Signals | Best Net | Best PF | Best DD | Best Trades/Wk | Promotion Rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `fresh_failed_or_reversal` | 64 | 36349 | 7303 | 1.40961355 | -2733 | 1.9623431 | 0 |
| `fresh_noise_area_momentum` | 128 | 131225 | 11346 | 1.43869621 | -2892 | 3.59274756 | 0 |
| `fresh_orb_continuation` | 128 | 85654 | 5022 | 1.22153602 | -1961 | 3.53417015 | 0 |
| `fresh_vwap_reclaim_reversal` | 64 | 26097 | 7966 | 1.50141625 | -2535 | 1.38633194 | 0 |

## Result

Rows generated after minimum thresholds: `6912`
Rows promoted by the strict first-pass lens: `0`

| Metric | Value |
| --- | ---: |
| Strategy | `fresh_vwap_reclaim_reversal:stretch80:reclaim0:delta600:cl0.45:end1230:space30:skipfri1` |
| Family | `fresh_vwap_reclaim_reversal` |
| Quantity | `2` |
| Target / Stop | `80 / 60` points |
| Trades | `142` |
| Trades/week | `1.38633194` |
| Net | `$7966` |
| PF | `1.50141625` |
| Win rate | `53.5%` |
| Drawdown | `$-2535` |
| Net/DD | `3.14240631` |
| Latest-year net | `$4724` |
| Worst quarter | `$-1278` |
| Worst month | `$-676` |
| Average hold | `38.00704225` min |
| Lens | `reject:trades<200,freq<2/wk,pf<1.6,dd<-1000,worstQ<-750` |

## Top Rows

| Rank | Lens | Family | Qty | Target | Stop | Trades | /Wk | Net | PF | DD | Latest | Worst Q | Strategy |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `reject:trades<200,freq<2/wk,pf<1.6,dd<-1000,worstQ<-750` | `fresh_vwap_reclaim_reversal` | 2 | 80 | 60 | 142 | 1.38633194 | 7966 | 1.50141625 | -2535 | 4724 | -1278 | `fresh_vwap_reclaim_reversal:stretch80:reclaim0:delta600:cl0.45:end1230:space30:skipfri1` |
| 2 | `reject:trades<200,freq<2/wk,pf<1.6,dd<-1000,worstQ<-750` | `fresh_vwap_reclaim_reversal` | 2 | 80 | 60 | 142 | 1.38633194 | 7966 | 1.50141625 | -2535 | 4724 | -1278 | `fresh_vwap_reclaim_reversal:stretch80:reclaim0:delta600:cl0.45:end1230:space60:skipfri1` |
| 3 | `reject:trades<200,freq<2/wk,pf<1.6,dd<-1000` | `fresh_vwap_reclaim_reversal` | 2 | 80 | 60 | 171 | 1.66945607 | 8798 | 1.45394974 | -1719 | 4365 | -190 | `fresh_vwap_reclaim_reversal:stretch80:reclaim0:delta600:cl0.45:end1230:space60:skipfri1` |
| 4 | `reject:pf<1.6,dd<-1000,worstQ<-750` | `fresh_noise_area_momentum` | 2 | 60 | 30 | 368 | 3.59274756 | 11346 | 1.43869621 | -2892 | 168 | -1365 | `fresh_noise_area_momentum:lb10:mult1.25:delta0:cl0.55:start0945:end1230:space30:skipfri0` |
| 5 | `reject:pf<1.6,dd<-1000,worstQ<-750` | `fresh_noise_area_momentum` | 2 | 60 | 30 | 368 | 3.59274756 | 11346 | 1.43869621 | -2892 | 168 | -1365 | `fresh_noise_area_momentum:lb10:mult1.25:delta0:cl0.55:start0945:end1230:space60:skipfri0` |
| 6 | `reject:pf<1.6,dd<-1000,worstQ<-750` | `fresh_noise_area_momentum` | 2 | 60 | 30 | 294 | 2.87029289 | 8928 | 1.43136686 | -2628 | 345 | -978 | `fresh_noise_area_momentum:lb10:mult1.25:delta0:cl0.55:start0945:end1230:space30:skipfri1` |
| 7 | `reject:pf<1.6,dd<-1000,worstQ<-750` | `fresh_noise_area_momentum` | 2 | 60 | 30 | 294 | 2.87029289 | 8928 | 1.43136686 | -2628 | 345 | -978 | `fresh_noise_area_momentum:lb10:mult1.25:delta0:cl0.55:start0945:end1230:space60:skipfri1` |
| 8 | `reject:pf<1.6,dd<-1000,worstQ<-750` | `fresh_vwap_reclaim_reversal` | 2 | 120 | 60 | 253 | 2.47001395 | 14034 | 1.42416732 | -2930 | 6342 | -1499 | `fresh_vwap_reclaim_reversal:stretch50:reclaim0:delta600:cl0.45:end1230:space30:skipfri1` |
| 9 | `reject:pf<1.6,dd<-1000,worstQ<-750` | `fresh_vwap_reclaim_reversal` | 2 | 120 | 60 | 253 | 2.47001395 | 14034 | 1.42416732 | -2930 | 6342 | -1499 | `fresh_vwap_reclaim_reversal:stretch50:reclaim0:delta600:cl0.45:end1230:space60:skipfri1` |
| 10 | `reject:pf<1.6,dd<-1000,worstQ<-750` | `fresh_vwap_reclaim_reversal` | 2 | 80 | 60 | 253 | 2.47001395 | 11871 | 1.41981115 | -2482 | 5545 | -1077 | `fresh_vwap_reclaim_reversal:stretch50:reclaim0:delta600:cl0.45:end1230:space30:skipfri1` |
| 11 | `reject:pf<1.6,dd<-1000,worstQ<-750` | `fresh_vwap_reclaim_reversal` | 2 | 80 | 60 | 253 | 2.47001395 | 11871 | 1.41981115 | -2482 | 5545 | -1077 | `fresh_vwap_reclaim_reversal:stretch50:reclaim0:delta600:cl0.45:end1230:space60:skipfri1` |
| 12 | `reject:freq<2/wk,pf<1.6,dd<-1000,worstQ<-750` | `fresh_failed_or_reversal` | 2 | 80 | 40 | 201 | 1.9623431 | 7303 | 1.40961355 | -2733 | 2574 | -1349 | `fresh_failed_or_reversal:or30:modemid:buf5:delta0:end1430:space30:skipfri1` |
| 13 | `reject:freq<2/wk,pf<1.6,dd<-1000,worstQ<-750` | `fresh_failed_or_reversal` | 2 | 80 | 40 | 201 | 1.9623431 | 7303 | 1.40961355 | -2733 | 2574 | -1349 | `fresh_failed_or_reversal:or30:modemid:buf5:delta0:end1430:space60:skipfri1` |
| 14 | `reject:trades<200,freq<2/wk,pf<1.6,dd<-1000,worstQ<-750` | `fresh_vwap_reclaim_reversal` | 2 | 80 | 60 | 181 | 1.76708508 | 8569 | 1.40824202 | -2313 | 3636 | -1056 | `fresh_vwap_reclaim_reversal:stretch80:reclaim0:delta600:cl0.45:end1230:space30:skipfri0` |
| 15 | `reject:trades<200,freq<2/wk,pf<1.6,dd<-1000,worstQ<-750` | `fresh_vwap_reclaim_reversal` | 2 | 80 | 60 | 181 | 1.76708508 | 8569 | 1.40824202 | -2313 | 3636 | -1056 | `fresh_vwap_reclaim_reversal:stretch80:reclaim0:delta600:cl0.45:end1230:space60:skipfri0` |
| 16 | `reject:pf<1.6,dd<-1000,latest<=0,worstQ<-750` | `fresh_noise_area_momentum` | 2 | 60 | 30 | 384 | 3.74895397 | 10588 | 1.38892154 | -3138 | -447 | -1734 | `fresh_noise_area_momentum:lb10:mult1.25:delta0:cl0.55:start0945:end1430:space30:skipfri0` |
| 17 | `reject:pf<1.6,dd<-1000,latest<=0,worstQ<-750` | `fresh_noise_area_momentum` | 2 | 60 | 30 | 384 | 3.74895397 | 10588 | 1.38892154 | -3138 | -447 | -1734 | `fresh_noise_area_momentum:lb10:mult1.25:delta0:cl0.55:start0945:end1430:space60:skipfri0` |
| 18 | `reject:trades<200,freq<2/wk,pf<1.6,dd<-1000,worstQ<-750` | `fresh_vwap_reclaim_reversal` | 2 | 120 | 60 | 142 | 1.38633194 | 7575 | 1.38782511 | -3015 | 4242 | -1998 | `fresh_vwap_reclaim_reversal:stretch80:reclaim0:delta600:cl0.45:end1230:space30:skipfri1` |
| 19 | `reject:trades<200,freq<2/wk,pf<1.6,dd<-1000,worstQ<-750` | `fresh_vwap_reclaim_reversal` | 2 | 120 | 60 | 142 | 1.38633194 | 7575 | 1.38782511 | -3015 | 4242 | -1998 | `fresh_vwap_reclaim_reversal:stretch80:reclaim0:delta600:cl0.45:end1230:space60:skipfri1` |
| 20 | `reject:pf<1.6,dd<-1000,latest<=0,worstQ<-750` | `fresh_noise_area_momentum` | 2 | 60 | 30 | 308 | 3.0069735 | 8416 | 1.38584266 | -2874 | -147 | -1347 | `fresh_noise_area_momentum:lb10:mult1.25:delta0:cl0.55:start0945:end1430:space30:skipfri1` |
| 21 | `reject:pf<1.6,dd<-1000,latest<=0,worstQ<-750` | `fresh_noise_area_momentum` | 2 | 60 | 30 | 308 | 3.0069735 | 8416 | 1.38584266 | -2874 | -147 | -1347 | `fresh_noise_area_momentum:lb10:mult1.25:delta0:cl0.55:start0945:end1430:space60:skipfri1` |
| 22 | `reject:pf<1.6,dd<-1000` | `fresh_vwap_reclaim_reversal` | 2 | 80 | 60 | 333 | 3.25104603 | 14591 | 1.38553612 | -2045 | 6898 | -566 | `fresh_vwap_reclaim_reversal:stretch50:reclaim0:delta600:cl0.45:end1230:space60:skipfri1` |
| 23 | `reject:pf<1.6,dd<-1000` | `fresh_vwap_reclaim_reversal` | 2 | 80 | 60 | 216 | 2.10878661 | 9623 | 1.38166819 | -1550 | 2791 | -359 | `fresh_vwap_reclaim_reversal:stretch80:reclaim0:delta600:cl0.45:end1230:space60:skipfri0` |
| 24 | `reject:pf<1.6,dd<-1000` | `fresh_vwap_reclaim_reversal` | 2 | 120 | 60 | 261 | 2.54811715 | 12907 | 1.37076296 | -2404 | 5849 | -668 | `fresh_vwap_reclaim_reversal:stretch50:reclaim0:delta0:cl0.45:end1230:space30:skipfri1` |
| 25 | `reject:pf<1.6,dd<-1000` | `fresh_vwap_reclaim_reversal` | 2 | 120 | 60 | 261 | 2.54811715 | 12907 | 1.37076296 | -2404 | 5849 | -668 | `fresh_vwap_reclaim_reversal:stretch50:reclaim0:delta0:cl0.45:end1230:space60:skipfri1` |

## Decision

No family cleared the strict first-pass lens. The correct next step is not to loosen the lens immediately; it is to inspect near-miss families and decide whether a second data representation is required.

Most likely second representations:

- tick/range bars from MNQ, because the 3-minute export can blur high-frequency order-flow timing;
- depth/order-book imbalance if Sierra market depth history is available;
- daily online context labels for CPI/FOMC/NFP/large tech earnings days.
