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
