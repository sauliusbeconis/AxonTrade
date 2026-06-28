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
- Generated baseline signals: `4869`
- Entry window: `09:45` to `15:45` New York time
- Non-random rule spacing: `300` seconds
- Random baseline: `25` entries per day, random side, deterministic seed
  `20260628`
- Exit grid: first target `0.5,1,1.5` points; stop `1,1.5,2` points; runner
  target `1.5,2,3,5` points; runner stop `breakeven,initial`
- Cost model: current ES two-contract scaled-scalp assumption from
  `config/research/default_costs.yaml`

Best row by generated entry family:

| Entry family | Trades | Net USD | Avg/trade | Full stops | First target hits | Runner targets | Runner stops | Best exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `impulse_continue_3bar_1.5pt` | `433` | `-9881.00` | `-22.82` | `222` | `210` | `105` | `104` | `1.5 / 1 / 5 / initial` |
| `vwap_extension_fade_4pt` | `422` | `-11104.00` | `-26.31` | `228` | `194` | `103` | `91` | `1.5 / 1 / 5 / initial` |
| `impulse_continue_5bar_2pt` | `435` | `-11132.50` | `-25.59` | `187` | `247` | `92` | `154` | `1.5 / 1.5 / 5 / breakeven` |
| `vwap_extension_fade_3pt` | `429` | `-14353.00` | `-33.46` | `239` | `190` | `79` | `111` | `1.5 / 1 / 5 / breakeven` |
| `random_25_per_day` | `550` | `-25500.00` | `-46.36` | `319` | `230` | `82` | `148` | `1.5 / 1 / 5 / breakeven` |

## Read

Random entries were not better than the current setup. They were heavily
negative after ES two-contract costs. The least bad simple rule was short-term
impulse continuation, not mean-reversion, but it was still negative.

This says the current scalp model is too expensive/coarse for random or simple
bar-close entries. The next useful test is not more random entry generation; it
is either lower cost/smaller size assumptions or genuinely microstructural
entries from bid/ask depth, touch-pull-stack, or one-second/order-flow data.
