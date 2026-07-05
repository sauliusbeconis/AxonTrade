# MGC Eval-Pass Initial Scan

Status: exploratory MGC-only research. Not a candidate yet.

## Objective

- profit target: `$1250`
- max loss: `-$1000`
- consistency: largest winning day must be `<= 50%` of total profit
- desired path: frequent enough to pass faster than the sparse MNQ lead

## Source

- rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- unique dates: `717`
- instrument: `MGC`, point value `$10`, tick value `$1`
- cost model: `$0.50/side` commission plus `1` total slippage tick per contract
- setup window: `08:20` to `13:30`, flatten by `16:30`

## Search Space

- entry families: COMEX opening-range breakout, lookback breakout, VWAP pullback continuation
- opening range: `08:20` to `08:50`
- quantities: `3`, `4`, `5`, `6`, `8`, `10`, `12` MGC
- target net/trade: around `$625`, `$650`, `$700`, tick-rounded
- stop net/trade: around `$350`, `$500`, `$650`, `$800`, tick-rounded

## Result

Best exploratory row by calendar-start ranking:

| Metric | Value |
| --- | ---: |
| Strategy | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri1` |
| Quantity | `3` |
| Target net/trade | `$702` |
| Stop net/trade | `$348` |
| Trades | `80` |
| Full-sample net | `$5772` |
| Latest-year trades | `50` |
| Latest-year net | `$3630` |
| Worst quarter net | `$-348` |
| Calendar-start pass rate | `8.9%` |
| Calendar-start fail rate | `7.4%` |
| Signal-start pass rate | `47.5%` |
| Signal-start fail rate | `25.0%` |
| Median signal gap | `5` calendar days |

No row met the first-pass acceptance lens of at least `80` trades, positive full sample/latest year, calendar pass rate `>=45%`, and calendar fail rate `<=15%`.

## Top Rows

| Rank | Family | Qty | Target | Stop | Trades | Latest Net | Calendar Pass | Calendar Fail | Signal Pass | Median Gap | Strategy |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | mgc_vwap_pullback | 3 | 702 | 348 | 80 | 3630 | 8.9% | 7.4% | 47.5% | 5 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri1` |
| 2 | mgc_vwap_pullback | 3 | 651 | 348 | 80 | 2814 | 8.9% | 7.4% | 45.0% | 5 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri1` |
| 3 | mgc_vwap_pullback | 3 | 627 | 348 | 80 | 2382 | 8.9% | 7.4% | 43.8% | 5 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri1` |
| 4 | mgc_vwap_pullback | 3 | 702 | 498 | 80 | 4878 | 11.8% | 8.8% | 50.0% | 5 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri1` |
| 5 | mgc_vwap_pullback | 5 | 625 | 500 | 110 | 2250 | 20.7% | 8.9% | 55.5% | 4 | `mgc_vwap_pullback:stretch15:pb2:delta0:cl0.55:end1030:skipfri0` |
| 6 | mgc_vwap_pullback | 5 | 700 | 500 | 87 | 3900 | 16.7% | 8.9% | 49.4% | 6 | `mgc_vwap_pullback:stretch15:pb2:delta0:cl0.55:end1030:skipfri1` |
| 7 | mgc_vwap_pullback | 4 | 700 | 500 | 80 | 3496 | 12.8% | 9.1% | 53.8% | 5 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri1` |
| 8 | mgc_vwap_pullback | 10 | 650 | 500 | 87 | 5200 | 24.6% | 9.3% | 67.8% | 4 | `mgc_vwap_pullback:stretch25:pb2:delta0:cl0.55:end1330:skipfri0` |
| 9 | mgc_vwap_pullback | 10 | 630 | 500 | 87 | 4640 | 24.6% | 9.3% | 67.8% | 4 | `mgc_vwap_pullback:stretch25:pb2:delta0:cl0.55:end1330:skipfri0` |
| 10 | mgc_vwap_pullback | 5 | 625 | 500 | 87 | 2625 | 17.7% | 9.3% | 50.6% | 6 | `mgc_vwap_pullback:stretch15:pb2:delta0:cl0.55:end1030:skipfri1` |
| 11 | mgc_vwap_pullback | 5 | 650 | 500 | 87 | 3050 | 17.4% | 9.3% | 50.6% | 6 | `mgc_vwap_pullback:stretch15:pb2:delta0:cl0.55:end1030:skipfri1` |
| 12 | mgc_vwap_pullback | 3 | 651 | 498 | 80 | 3996 | 13.2% | 9.3% | 48.8% | 5 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri1` |
| 13 | mgc_vwap_pullback | 3 | 627 | 498 | 80 | 3468 | 13.2% | 9.3% | 48.8% | 5 | `mgc_vwap_pullback:stretch25:pb5:delta75:cl0.55:end1330:skipfri1` |
| 14 | mgc_vwap_pullback | 12 | 660 | 492 | 87 | 3384 | 19.4% | 9.4% | 55.2% | 4 | `mgc_vwap_pullback:stretch25:pb2:delta0:cl0.55:end1330:skipfri0` |
| 15 | mgc_vwap_pullback | 12 | 660 | 648 | 87 | 4248 | 26.1% | 9.6% | 66.7% | 4 | `mgc_vwap_pullback:stretch25:pb2:delta0:cl0.55:end1330:skipfri0` |

## Interpretation

This first pass only tests whether MGC has enough continuation behavior to justify deeper work. It is not slippage-stressed, not walk-forwarded, and not ready for Sierra replay.
