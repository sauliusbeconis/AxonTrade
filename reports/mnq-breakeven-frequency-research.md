# MNQ Breakeven-Frequency Research

Status: first-pass risk-management scan for frequent MNQ entries.

## Thought Being Tested

The key event is not the final runner target. The key event is whether a setup reaches target one often enough to pay the first leg, move the runner stop to breakeven, and turn many uncertain trades into protected outcomes. A target-one hit followed by breakeven is acceptable in this research pass.

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique dates: `507`
- instrument: `MNQ`, point value `$2`, tick value `$0.50`
- cost model: `$0.50/side` commission plus `1` total slippage tick per contract

## Search Shape

- tested sizes/splits: `2 MNQ = 1 + 1`, `3 MNQ = 2 + 1`, `4 MNQ = 3 + 1`, and `4 MNQ = 2 + 2`
- entries: frequent lookback breakouts and VWAP pullback continuations
- trade cap: `1` or `2` raw signals per day, with at least `30` minutes spacing
- management: first leg exits at target one; runner target is separate; runner stop moves to entry immediately after target one
- no overlapping trades inside a strategy; later signals are skipped while a prior managed trade is open
- same-bar ambiguity is conservative: initial stop wins before target one; after target one, breakeven wins before runner target

## Result

Best first-pass row by risk-management ranking:

| Metric | Value |
| --- | ---: |
| Strategy | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1230:skipfri1:maxday1:space30` |
| Quantity | `4` |
| Split | `3 + 1` |
| First target / initial stop / runner target | `25 / 40 / 80` |
| Evaluated trades | `362` |
| Trades/week | `3.53417015` |
| First-target reach | `65.2%` |
| Full-stop rate | `34.3%` |
| Runner breakeven rate | `51.1%` |
| Runner target rate | `12.4%` |
| Net | `$1173.5` |
| Avg trade | `$3.24171271` |
| Profit factor | `1.02895386` |
| Max trade-sequence DD | `$-3986` |
| Latest-year trades | `93` |
| Latest-year net | `$-246.5` |
| Worst quarter | `$-2728` |
| Median hold | `12` minutes |

Rows meeting the rough risk-first lens: `0`.

## Positive Rows Audit

Positive rows found: `5` out of `134400`. These are not accepted candidates unless the latest-year and quarter risk also hold up.

| Rank | Qty | Split | Trades | /Wk | T1 / Stop / Runner | T1 Hit | Full Stop | Net | PF | Latest-Year Net | Worst Quarter | Strategy |
| ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 4 | 3+1 | 362 | 3.53417015 | 25 / 40 / 80 | 65.2% | 34.3% | 1173.5 | 1.02895386 | -246.5 | -2728 | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1230:skipfri1:maxday1:space30` |
| 2 | 4 | 3+1 | 392 | 3.82705718 | 25 / 40 / 80 | 65.1% | 34.4% | 847 | 1.01919938 | -1300.5 | -2318 | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1430:skipfri1:maxday1:space30` |
| 3 | 4 | 3+1 | 683 | 6.66806137 | 25 / 40 / 80 | 64.4% | 34.7% | 585.5 | 1.00756382 | -504 | -2992.5 | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1430:skipfri1:maxday2:space30` |
| 4 | 4 | 3+1 | 362 | 3.53417015 | 25 / 40 / 60 | 65.2% | 34.3% | 103 | 1.00254133 | -448 | -2848 | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1230:skipfri1:maxday1:space30` |
| 5 | 4 | 3+1 | 362 | 3.53417015 | 25 / 40 / 40 | 65.2% | 34.3% | 28 | 1.00069085 | -528 | -2888 | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1230:skipfri1:maxday1:space30` |

## Top Rows

| Rank | Family | Qty | Split | Trades | /Wk | T1 / Stop / Runner | T1 Hit | Full Stop | BE | Runner | Net | PF | Latest-Year Net | Strategy |
| ---: | --- | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | lookback_be_frequency | 4 | 3+1 | 362 | 3.53417015 | 25 / 40 / 80 | 65.2% | 34.3% | 51.1% | 12.4% | 1173.5 | 1.02895386 | -246.5 | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1230:skipfri1:maxday1:space30` |
| 2 | lookback_be_frequency | 4 | 3+1 | 392 | 3.82705718 | 25 / 40 / 80 | 65.1% | 34.4% | 50.8% | 11.7% | 847 | 1.01919938 | -1300.5 | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1430:skipfri1:maxday1:space30` |
| 3 | lookback_be_frequency | 4 | 3+1 | 683 | 6.66806137 | 25 / 40 / 80 | 64.4% | 34.7% | 49.6% | 11.9% | 585.5 | 1.00756382 | -504 | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1430:skipfri1:maxday2:space30` |
| 4 | lookback_be_frequency | 4 | 3+1 | 362 | 3.53417015 | 25 / 40 / 60 | 65.2% | 34.3% | 49.7% | 15.2% | 103 | 1.00254133 | -448 | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1230:skipfri1:maxday1:space30` |
| 5 | lookback_be_frequency | 4 | 3+1 | 362 | 3.53417015 | 25 / 40 / 40 | 65.2% | 34.3% | 42.5% | 22.7% | 28 | 1.00069085 | -528 | `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1230:skipfri1:maxday1:space30` |
| 6 | lookback_be_frequency | 4 | 3+1 | 704 | 6.87308229 | 25 / 40 / 60 | 63.6% | 35.2% | 46.9% | 15.5% | -3106 | 0.9617563 | 196.5 | `lookback_be_frequency:lb20:buf2.5:delta0:cl0.55:end1430:skipfri1:maxday2:space30` |
| 7 | lookback_be_frequency | 4 | 3+1 | 724 | 7.06834031 | 25 / 40 / 80 | 63.1% | 35.6% | 49.2% | 11.2% | -3856 | 0.9543485 | 182 | `lookback_be_frequency:lb20:buf0:delta0:cl0.55:end1430:skipfri1:maxday2:space30` |
| 8 | lookback_be_frequency | 4 | 3+1 | 731 | 7.13668061 | 25 / 40 / 60 | 63.3% | 35.4% | 46.8% | 15.5% | -4080 | 0.95188225 | 588.5 | `lookback_be_frequency:lb20:buf0:delta0:cl0.55:end1430:skipfri1:maxday2:space30` |
| 9 | lookback_be_frequency | 4 | 3+1 | 740 | 7.22454672 | 25 / 40 / 40 | 63.5% | 35.3% | 40.7% | 22.6% | -4225 | 0.95055241 | 386.5 | `lookback_be_frequency:lb20:buf0:delta0:cl0.55:end1430:skipfri1:maxday2:space30` |
| 10 | lookback_be_frequency | 4 | 3+1 | 706 | 6.89260809 | 25 / 40 / 60 | 63.5% | 35.4% | 47.3% | 14.9% | -4238 | 0.94823374 | 76.5 | `lookback_be_frequency:lb20:buf2.5:delta0:cl0.45:end1430:skipfri1:maxday2:space30` |
| 11 | lookback_be_frequency | 4 | 3+1 | 727 | 7.09762901 | 20 / 40 / 80 | 69.3% | 29.8% | 59.8% | 7.3% | -3902.5 | 0.94518191 | 488 | `lookback_be_frequency:lb20:buf0:delta600:cl0.55:end1430:skipfri1:maxday2:space30` |
| 12 | lookback_be_frequency | 4 | 3+1 | 731 | 7.13668061 | 20 / 40 / 60 | 69.4% | 29.8% | 58.7% | 9.7% | -4850 | 0.93218301 | 366.5 | `lookback_be_frequency:lb20:buf0:delta600:cl0.55:end1430:skipfri1:maxday2:space30` |

## Robust Rows By Family

No family produced a row that met the rough risk-first lens. The next step is to widen the entry families or adjust the target-one/stop grid.

## Interpretation

This is not a deployment candidate yet. A usable candidate needs the same work we require elsewhere: expanded families if needed, slippage stress, walk-forward or holdout review, and replay/mechanics testing.

The useful early signal is the relationship between first-target rate and full-stop rate. If target one is reached often and full stops stay controlled, then the idea has room for better runner research.
