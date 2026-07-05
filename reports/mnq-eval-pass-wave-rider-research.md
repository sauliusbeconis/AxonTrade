# MNQ Eval-Pass Wave Rider Research

Status: second-pass MNQ-only research for a LucidFlex-style 25K evaluation objective.

## Objective

- profit target: `$1250`
- max loss: `-$1000`
- consistency: largest winning day must be `<= 50%` of total profit
- desired path: about `$625-$700` on each of two traded days

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique dates: `507`
- instrument: `MNQ`, point value `$2`, tick value `$0.50`
- cost model: `$0.50/side` commission plus `1` total slippage tick per contract

## Search Space

- entry families: opening-range breakout, opening-range retest, lookback breakout, VWAP pullback continuation
- grid: continuation filters plus second-pass clean-breakout filters
- one trade per strategy per day
- quantities: `5`, `6`, `8`, `10`, `12`, `15`, `20` MNQ
- target net/trade: around `$625`, `$650`, `$700`, tick-rounded
- stop net/trade: around `$350`, `$500`, `$650`, `$800`, tick-rounded
- eval attempts: simulated from each rolling calendar start date and from each valid signal date

## Result

Best second-pass row by eval-pass ranking:

| Metric | Value |
| --- | ---: |
| Strategy | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` |
| Quantity | `10` |
| Target net/trade | `$625` |
| Stop net/trade | `$650` |
| Signals/trades | `50` |
| Win rate | `66.0%` |
| Avg trade | `$204.5` |
| Full-sample net | `$10225` |
| Trade-sequence max DD | `$-1950` |
| Latest-year trades | `8` |
| Latest-year net | `$1175` |
| Worst quarter net | `$-1300` |
| Signal-start pass rate | `88.0%` |
| Signal-start two-trade-day pass rate | `40.0%` |
| Signal-start fail rate | `8.0%` |
| Signal-start timeout rate | `4.0%` |
| Signal-start median calendar days to pass | `42.5` |
| Signal-start median traded days to pass | `5` |
| Calendar-start pass rate | `21.1%` |
| Calendar-start fail rate | `3.9%` |

Rows meeting the rough second-pass acceptance lens: `125`.

## Top Rows

| Rank | Family | Qty | Target | Stop | Trades | Latest-Year Net | Signal Pass | 2-Day | Signal Fail | Avg Trade | Strategy |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | lookback_breakout | 10 | 625 | 650 | 50 | 1175 | 88.0% | 40.0% | 8.0% | 204.5 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` |
| 2 | lookback_breakout | 10 | 650 | 650 | 50 | 1300 | 88.0% | 38.0% | 8.0% | 208.5 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` |
| 3 | lookback_breakout | 5 | 625 | 650 | 57 | 3700 | 87.7% | 31.6% | 3.5% | 242.01754386 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 4 | lookback_breakout | 12 | 702 | 798 | 50 | 1116 | 86.0% | 44.0% | 10.0% | 237.96 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` |
| 5 | lookback_breakout | 12 | 630 | 798 | 50 | 756 | 86.0% | 44.0% | 10.0% | 201.6 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` |
| 6 | lookback_breakout | 12 | 702 | 798 | 57 | 2520 | 86.0% | 47.4% | 7.0% | 268.63157895 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 7 | lookback_breakout | 10 | 625 | 650 | 57 | 2425 | 86.0% | 43.9% | 7.0% | 233.77192982 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 8 | lookback_breakout | 10 | 650 | 650 | 57 | 2600 | 86.0% | 42.1% | 7.0% | 239.9122807 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 9 | lookback_breakout | 12 | 630 | 798 | 57 | 2016 | 86.0% | 47.4% | 8.8% | 229.15789474 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 10 | lookback_breakout | 6 | 627 | 798 | 57 | 3420 | 84.2% | 36.8% | 3.5% | 238.94736842 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |

## Fastest Two-Day Leads

| Rank | Qty | Target | Stop | Trades | Latest-Year Net | Signal Pass | 2-Day | Signal Fail | Median Calendar Days | Strategy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 12 | 702 | 798 | 57 | 2520 | 86.0% | 47.4% | 7.0% | 27 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 2 | 12 | 630 | 798 | 57 | 2016 | 86.0% | 47.4% | 8.8% | 27 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 3 | 12 | 654 | 798 | 57 | 2184 | 84.2% | 47.4% | 10.5% | 26 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 4 | 10 | 625 | 800 | 57 | 3400 | 82.5% | 45.6% | 7.0% | 27 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` |
| 5 | 20 | 700 | 800 | 54 | 300 | 70.4% | 44.4% | 24.1% | 18.5 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1172_barrange24_75` |
| 6 | 20 | 650 | 800 | 54 | 50 | 68.5% | 44.4% | 27.8% | 18 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1172_barrange24_75` |
| 7 | 12 | 702 | 798 | 50 | 1116 | 86.0% | 44.0% | 10.0% | 33 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` |
| 8 | 12 | 630 | 798 | 50 | 756 | 86.0% | 44.0% | 10.0% | 33 | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` |

## Interpretation

This is research for eval-passing geometry, not a deployment candidate by itself. A true candidate still needs slippage stress, walk-forward selection, and replay/mechanics validation.

Signal-start metrics assume the account is only exposed after a valid setup appears. Calendar-start metrics are harsher because they also penalize waiting time after a random start date.
