# Sierra Scalp Entry Baselines

Manual help needed: **No**.

## Theory

Online research points to a narrower scalp hypothesis than "random entries
should work":

- E-mini S&P 500 price/flow effects are real but extremely short-lived.
  Takahashi finds price and flow impacts at the one-second horizon, with shocks
  dissipating almost entirely within a second, and strong intraday/news
  variation:
  https://arxiv.org/html/2508.06788
- CME's liquidity work emphasizes that ES liquidity must be judged by fill
  quality, price dispersion, volatility, and time of day, not just volume or
  depth:
  https://www.cmegroup.com/articles/2025/reassessing-liquidity-beyond-order-book-depth.html

Practical hypothesis tested here: random entries should be a negative
transaction-cost baseline; simple scalp candidates should only improve if they
use very short-term continuation or extension/mean-reversion structure.

## Test

Command:

```bash
.venv/bin/python scripts/run_signal_scalp_entry_baselines.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  reports/sierra-signal-log-scalp-entry-baselines-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth
```

Sample and assumptions:

- Dates: `22`
- Generated baseline signals: `6654`
- Entry window: `09:45` to `15:45` New York time
- Non-random rule spacing: `300` seconds
- Random baseline: `25` entries per day, random side, deterministic seed
  `20260628`
- Entry families: random, VWAP-extension fade, impulse fade, impulse
  continuation, delta impulse continuation, delta absorption fade, and
  VWAP/delta exhaustion fade
- Exit grid: first target `0.5,1,1.5` points; stop `1,1.5,2` points; runner
  target `1.5,2,3,5` points; runner stop `breakeven,initial`
- Cost model: current ES two-contract scaled-scalp assumption from
  `config/research/default_costs.yaml`

Best row by generated entry family:

| Entry family | Trades | Net USD | Avg/trade | Full stops | First target hits | Runner targets | Runner stops | Best exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `140` | `-2780.00` | `-19.86` | `46` | `94` | `67` | `27` | `1.5 / 2 / 3 / initial` |
| `delta_absorption_fade_20d_cl0.35` | `187` | `-3484.00` | `-18.63` | `92` | `95` | `37` | `58` | `1.5 / 1 / 5 / breakeven` |
| `vwap_delta_exhaustion_fade_3pt_20d_cl0.5` | `158` | `-3506.00` | `-22.19` | `56` | `102` | `55` | `47` | `1.5 / 2 / 5 / initial` |
| `delta_absorption_fade_30d_cl0.4` | `157` | `-5049.00` | `-32.16` | `57` | `100` | `52` | `48` | `1.5 / 2 / 3 / breakeven` |
| `random_25_per_day` | `550` | `-25500.00` | `-46.36` | `319` | `230` | `82` | `148` | `1.5 / 1 / 5 / breakeven` |

Zero-slippage sensitivity:

```bash
.venv/bin/python scripts/run_signal_scalp_entry_baselines.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  reports/sierra-signal-log-scalp-entry-baselines-slip0-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --slippage-ticks-per-side 0
```

Best zero-slippage rows:

| Entry family | Trades | Net USD | Avg/trade | Best exit |
| --- | ---: | ---: | ---: | --- |
| `impulse_continue_3bar_1.5pt` | `433` | `11769.00` | `27.18` | `1.5 / 1 / 5 / initial` |
| `impulse_continue_5bar_2pt` | `435` | `10617.50` | `24.41` | `1.5 / 1.5 / 5 / breakeven` |
| `vwap_extension_fade_4pt` | `422` | `9996.00` | `23.69` | `1.5 / 1 / 5 / initial` |
| `delta_absorption_fade_20d_cl0.35` | `187` | `5866.00` | `31.37` | `1.5 / 1 / 5 / breakeven` |
| `random_25_per_day` | `550` | `2000.00` | `3.64` | `1.5 / 1 / 5 / breakeven` |

Passive-touch zero-slippage sensitivity:

```bash
.venv/bin/python scripts/run_signal_scalp_entry_baselines.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  reports/sierra-signal-log-scalp-entry-baselines-passive-touch-slip0-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --slippage-ticks-per-side 0 \
  --entry-fill-mode passive_touch \
  --maximum-passive-fill-seconds 60
```

This requires a later bar within `60` seconds to touch the generated entry
price before the trade is considered filled. The outcome scan starts after the
fill bar.

Best passive-touch zero-slippage rows:

| Entry family | Filled trades | Net USD | Avg/trade | Best exit |
| --- | ---: | ---: | ---: | --- |
| `impulse_continue_3bar_1.5pt` | `262` | `3966.00` | `15.14` | `1.5 / 1 / 5 / initial` |
| `vwap_delta_exhaustion_fade_3pt_20d_cl0.5` | `141` | `1788.00` | `12.68` | `1.5 / 2 / 5 / initial` |
| `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `125` | `1125.00` | `9.00` | `1.5 / 1.5 / 5 / initial` |
| `delta_absorption_fade_10d_cl0.35` | `176` | `843.00` | `4.79` | `1.5 / 2 / 5 / initial` |

Passive-touch wait-window sweep:

| Max wait seconds | Slippage model | Best family | Filled trades | Net USD | Avg/trade | Best exit |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| `10` | `zero` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `76` | `3693.00` | `48.59` | `1.5 / 1.5 / 5 / initial` |
| `30` | `zero` | `impulse_continue_3bar_1.5pt` | `220` | `4010.00` | `18.23` | `1.5 / 1 / 5 / initial` |
| `60` | `zero` | `impulse_continue_3bar_1.5pt` | `262` | `3966.00` | `15.14` | `1.5 / 1 / 5 / initial` |
| `120` | `zero` | `impulse_continue_3bar_1.5pt` | `323` | `2814.00` | `8.71` | `1.5 / 1 / 5 / initial` |
| `300` | `zero` | `impulse_continue_3bar_1.5pt` | `369` | `1467.00` | `3.98` | `1.5 / 1 / 5 / initial` |
| `1` | `exit 1 tick` | `vwap_delta_exhaustion_fade_3pt_20d_cl0.5` | `14` | `627.00` | `44.79` | `1.5 / 1 / 2 / initial` |
| `5` | `exit 1 tick` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `46` | `1578.00` | `34.30` | `1.5 / 2 / 5 / initial` |
| `10` | `exit 1 tick` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `76` | `1793.00` | `23.59` | `1.5 / 1.5 / 5 / initial` |
| `15` | `exit 1 tick` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `94` | `717.00` | `7.63` | `1.5 / 1.5 / 5 / initial` |
| `30` | `exit 1 tick` | `vwap_delta_exhaustion_fade_3pt_20d_cl0.5` | `129` | `-953.00` | `-7.39` | `1.5 / 2 / 5 / breakeven` |
| `60` | `exit 1 tick` | `vwap_delta_exhaustion_fade_3pt_20d_cl0.5` | `141` | `-1737.00` | `-12.32` | `1.5 / 2 / 5 / initial` |
| `120` | `exit 1 tick` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `132` | `-2499.00` | `-18.93` | `1.5 / 1.5 / 5 / initial` |
| `300` | `exit 1 tick` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `137` | `-2309.00` | `-16.85` | `1.5 / 1.5 / 5 / initial` |
| `10` | `round turn 1 tick/side` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `76` | `-107.00` | `-1.41` | `1.5 / 1.5 / 5 / initial` |
| `30` | `round turn 1 tick/side` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `115` | `-4005.00` | `-34.83` | `1.5 / 2 / 5 / initial` |
| `60` | `round turn 1 tick/side` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `125` | `-5125.00` | `-41.00` | `1.5 / 1.5 / 5 / initial` |
| `120` | `round turn 1 tick/side` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `132` | `-5799.00` | `-43.93` | `1.5 / 1.5 / 5 / initial` |
| `300` | `round turn 1 tick/side` | `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `137` | `-5734.00` | `-41.85` | `1.5 / 1.5 / 5 / initial` |

## Read

Random entries were not better after normal ES two-contract costs. The
order-flow proxy rules improved the best regular-cost result from about
`-22.82` per trade to about `-18.63` per trade, but no tested family survived
one tick of slippage per side.

The zero-slippage run changes the interpretation. Several families become
positive before slippage, and random entries also turn slightly positive. This
says the current scalp model is not simply directionally hopeless; it is very
fill-quality sensitive. The next useful test is passive/limit-fill feasibility,
not more target/stop tuning with a fixed market-order slippage assumption.

The first passive-touch test keeps the best simple family positive, but much
smaller than immediate zero-slippage entry. That makes `impulse_continue_3bar`
the current lead hypothesis for a future limit-order scalp prototype, with the
main open question being whether Sierra live/replay data can validate queue and
partial-fill behavior.

The wait-window sweep sharpens this. The zero-slippage passive model remains
positive from `10` to `300` seconds, but expectancy decays as stale fills are
allowed. Splitting slippage into passive entry plus a one-tick market exit
keeps only the fast `1` to `15` second fills positive. With the current
one-tick-per-side round-turn slippage model, every wait window is negative, and
the `10` second best row is only near breakeven.

The strongest practical hypothesis is now a fast passive VWAP/delta exhaustion
fade: require a limit touch inside about `5` to `10` seconds, assume no entry
slippage, and pay one tick on exits. This is still aggregate/in-sample and must
be validated chronologically before bot implementation.

Chronological validation of the fast passive candidates:

```bash
.venv/bin/python scripts/run_signal_scalp_entry_baselines.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  reports/sierra-signal-log-scalp-entry-baselines-passive-touch-10s-exit1tick-walk-forward-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --slippage-ticks-per-contract 1 \
  --entry-fill-mode passive_touch \
  --maximum-passive-fill-seconds 10 \
  --strategy-ids vwap_delta_exhaustion_fade_4pt_30d_cl0.55,vwap_delta_exhaustion_fade_3pt_20d_cl0.5,impulse_continue_3bar_1.5pt \
  --output-mode walk_forward \
  --train-date-count 8 \
  --holdout-date-count 1 \
  --minimum-train-trades 4
```

Walk-forward result:

| Entry mode | Slippage model | Holdout windows | Holdout trades | Holdout net USD | Avg/trade | Read |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| passive-touch `5s` | zero | `12` | `75` | `125.00` | `1.67` | too thin |
| passive-touch `5s` | half tick total/contract | `12` | `75` | `-812.50` | `-10.83` | failed |
| passive-touch `5s` | one tick total/contract | `12` | `75` | `-1750.00` | `-23.33` | failed |
| passive-touch `10s` | zero | `17` | `151` | `2043.00` | `13.53` | positive |
| passive-touch `10s` | half tick total/contract | `17` | `151` | `155.50` | `1.03` | too thin |
| passive-touch `10s` | one tick total/contract | `17` | `151` | `-1732.00` | `-11.47` | failed |
| immediate | zero | `53` | `1006` | `13883.00` | `13.80` | positive before costs |
| immediate | half tick total/contract | `53` | `1006` | `1308.00` | `1.30` | too thin |

The aggregate-positive fast passive idea only partly survived chronological
selection. With perfect fills, passive-touch `10s` and immediate entries are
positive, but the edge is small relative to execution cost. Half a tick total
slippage per contract leaves only a thin result, and one tick total slippage
per contract fails.

Cost threshold: the passive-touch `10s` walk-forward makes about `$13.53` per
trade before slippage. With two ES contracts, one total tick per contract costs
`$25.00` per trade, so the break-even execution budget is about `0.54` ticks
total slippage per contract. This is too tight for market-order execution and
still not strong enough for bot implementation on this sample.

Larger-exit walk-forward check:

```bash
.venv/bin/python scripts/run_signal_scalp_entry_baselines.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_NY_Large.txt \
  reports/sierra-signal-log-scalp-entry-baselines-passive-touch-10s-exit1tick-larger-exit-walk-forward-large-sample.csv \
  --symbol ESU26-CME \
  --chart-number 2 \
  --session-phase rth \
  --slippage-ticks-per-contract 1 \
  --entry-fill-mode passive_touch \
  --maximum-passive-fill-seconds 10 \
  --strategy-ids vwap_delta_exhaustion_fade_4pt_30d_cl0.55,vwap_delta_exhaustion_fade_3pt_20d_cl0.5,impulse_continue_3bar_1.5pt,delta_absorption_fade_20d_cl0.35 \
  --output-mode walk_forward \
  --train-date-count 8 \
  --holdout-date-count 1 \
  --minimum-train-trades 4 \
  --first-target-points 1.5,2,2.5,3 \
  --stop-points 1.5,2,2.5,3,4 \
  --runner-target-points 3,4,5,6,8,10,12,15 \
  --runner-stop-modes breakeven,initial
```

This tested whether the scalp could become less execution-thin by using larger
first targets, wider stops, and larger runners on the lead passive-entry
families.

| Entry mode | Slippage model | Holdout windows | Holdout trades | Holdout net USD | Avg/trade | Read |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| passive-touch `5s` | zero | `16` | `89` | `-1073.00` | `-12.06` | failed |
| passive-touch `5s` | half tick total/contract | `16` | `89` | `-2185.50` | `-24.56` | failed |
| passive-touch `5s` | one tick total/contract | `16` | `89` | `-3298.00` | `-37.06` | failed |
| passive-touch `10s` | zero | `22` | `191` | `-649.50` | `-3.40` | failed |
| passive-touch `10s` | half tick total/contract | `22` | `191` | `-3037.00` | `-15.90` | failed |
| passive-touch `10s` | one tick total/contract | `22` | `191` | `-5424.50` | `-28.40` | failed |

Best-looking larger-exit slice was only the `10s` perfect-fill
`impulse_continue_3bar_1.5pt` subgroup:

| Entry family | Holdout trades | Net USD | Avg/trade | Full stops | First target hits | Runner targets | Runner stops |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `impulse_continue_3bar_1.5pt` | `125` | `1487.50` | `11.90` | `77` | `48` | `14` | `33` |
| `vwap_delta_exhaustion_fade_3pt_20d_cl0.5` | `15` | `120.00` | `8.00` | `6` | `9` | `1` | `8` |
| `vwap_delta_exhaustion_fade_4pt_30d_cl0.55` | `11` | `-477.00` | `-43.36` | `4` | `7` | `2` | `5` |
| `delta_absorption_fade_20d_cl0.35` | `40` | `-1780.00` | `-44.50` | `20` | `20` | `0` | `20` |

Interpretation: widening the exits did not solve the execution problem. Even
the best subgroup made only `$11.90` per trade before slippage, which is less
than half a tick per ES contract on a two-contract scalp. This keeps the
current synthetic scalp research in the microstructure/fill-quality bucket
rather than a robust discretionary-style scalp setup. The next research branch
should either validate true limit-order queue/partial-fill behavior or move to
a different, slower setup family with larger expected movement.
