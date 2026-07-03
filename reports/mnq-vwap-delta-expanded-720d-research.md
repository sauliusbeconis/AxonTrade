# MNQ VWAP Delta Expanded 720D Research

Status: **local-neighborhood research lead found, not implementation-ready**

## Source

- Export: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_MNQ_OrderflowExport_Expanded.txt`
- Rows: `67300`
- Dates: `2024-07-15` through `2026-07-02`
- Unique trading dates: `507`
- Schema: pass
- Required fields: `VWAP`, `Bid Volume`, `Ask Volume`, `Ask Volume Bid Volume Difference`
- Cost model: `MNQ`, two-contract scaled scalp, `$2/point`, `$0.50/side`, `1` tick total slippage per contract unless stated otherwise

## ES-Sized Baseline Rejection

The existing ES-sized generated strategy families were not transferable to MNQ.

Command output:

- built-in broad sweep, 1 tick total slippage per contract: `0` positive rows
- built-in broad sweep, zero slippage with commissions: `0` positive rows
- best built-in row at 1 tick: `opening_range_breakout_continue_30m_0.5pt`, `1592` trades, `-2995.50`
- best built-in row at zero slippage: same entry family, `1592` trades, `-1403.50`

Interpretation: small ES-style VWAP/delta thresholds are too noisy on MNQ, and
micro-contract costs erase the weak gross edge.

## MNQ-Sized VWAP Delta Sweep

MNQ export distribution:

- median absolute VWAP distance: about `50` points
- p90 absolute VWAP distance: about `147` points
- median absolute delta: about `452`
- p90 absolute delta: about `1452`

Custom sweep:

- VWAP thresholds: `20,40,60,80,120,160,240`
- Delta thresholds: `500,1000,1500,2000,3000`
- Close-location thresholds: `0.4,0.5`
- Spacing: `900` seconds
- Max rule entries/day: `20`
- Exit grid: first target `10,20,30,40,60`; stop `20,30,40,60,80,120`; runner target `20,40,60,100,150,200`; runner stop `initial,breakeven`

Artifacts:

- `reports/mnq-vwap-delta-custom-threshold-sweep-slip1.csv`
- `reports/mnq-vwap-delta-custom-top100-candidate-diagnostics.csv`
- `reports/mnq-vwap-delta-shortlist-fixed-walk-forward-summary.csv`
- `reports/mnq-vwap-delta-80pt-500d-cl04-exit20-120-40-slip1-trade-audit.csv`

## Shortlist

| Candidate | Exit | Trades | Net | Avg | PF | Max DD | 2024 | 2025 | 2026 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `80pt_500d_cl0.4` | `20 / 120 / 40 / initial` | 236 | 5671.50 | 24.03 | 1.4020 | -1257.00 | 198.00 | 4487.50 | 986.00 |
| `40pt_500d_cl0.4` | `10 / 120 / 20 / initial` | 492 | 5222.50 | 10.61 | 1.2780 | -1300.00 | 447.00 | 3696.50 | 1079.00 |
| `20pt_1500d_cl0.4` | `60 / 120 / 100 / initial` | 57 | 4873.00 | 85.49 | 1.8245 | -1902.00 | 298.50 | 2833.50 | 1741.00 |

The best raw balance before attribution was:

`mnq_vwap_delta_exhaustion_fade_80pt_500d_cl0.4`, exit `20 / 120 / 40 / initial`.

It has fewer trades than the 40pt candidate, better average/trade, better profit
factor, positive 2026, and materially lower drawdown than the higher-net
full-sample rows.

## Fixed Walk-Forward

| Candidate | Window | Holdout Windows | Positive | Negative | Holdout Trades | Holdout Net | Avg/Trade | Worst Window |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `80pt_500d_cl0.4` | `20x5` | 30 | 20 | 10 | 206 | 6174.00 | 29.97 | -683.00 |
| `80pt_500d_cl0.4` | `40x10` | 13 | 11 | 2 | 179 | 4726.50 | 26.41 | -509.00 |
| `80pt_500d_cl0.4` | `60x10` | 11 | 9 | 2 | 149 | 4247.50 | 28.51 | -509.00 |
| `40pt_500d_cl0.4` | `20x5` | 57 | 33 | 24 | 454 | 4956.50 | 10.92 | -567.00 |
| `40pt_500d_cl0.4` | `40x10` | 26 | 20 | 6 | 410 | 5748.50 | 14.02 | -578.50 |
| `40pt_500d_cl0.4` | `60x10` | 24 | 18 | 6 | 378 | 5210.50 | 13.78 | -578.50 |
| `20pt_1500d_cl0.4` | `20x5` | 7 | 5 | 2 | 36 | 4365.50 | 121.26 | -605.00 |

## Slippage Stress

| Candidate | Slippage Ticks/Contract | Trades | Net | Avg | Max DD | 2024 | 2025 | 2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `80pt_500d_cl0.4` | 1 | 236 | 5671.50 | 24.03 | -1257.00 | 198.00 | 4487.50 | 986.00 |
| `80pt_500d_cl0.4` | 2 | 236 | 5435.50 | 23.03 | -1274.00 | 158.00 | 4366.50 | 911.00 |
| `80pt_500d_cl0.4` | 3 | 236 | 5199.50 | 22.03 | -1291.00 | 118.00 | 4245.50 | 836.00 |
| `40pt_500d_cl0.4` | 1 | 492 | 5222.50 | 10.61 | -1300.00 | 447.00 | 3696.50 | 1079.00 |
| `40pt_500d_cl0.4` | 2 | 492 | 4730.50 | 9.61 | -1340.00 | 343.00 | 3439.50 | 948.00 |
| `40pt_500d_cl0.4` | 3 | 492 | 4238.50 | 8.61 | -1380.00 | 239.00 | 3182.50 | 817.00 |

## Interpretation

MNQ needs Nasdaq-sized thresholds. The ES/MES candidate should not be copied
directly.

The raw `80pt_500d_cl0.4` row was the first MNQ research lead that was not immediately
rejected:

- positive full sample
- positive 2024, 2025, and 2026
- positive fixed walk-forward
- survives 3 ticks total slippage per contract
- lower drawdown than the higher-net full-sample rows

After attribution, the stronger lead is the same rule with a static schedule
filter: no Friday entries and no entries during the `11:00` or `15:00` exchange
time hours.

It is still not live-ready because the stop is wide (`120` MNQ points), the
filtered sample has only `133` trades, and MNQ Sierra replay/mechanics have not
been tested yet.

## Risk Gates And Attribution

The dedicated audit for `80pt_500d_cl0.4` matched the shortlist exactly:

- trades: `236`
- net: `5671.50`
- average/trade: `24.03`
- max realized equity drawdown: `-1257.00`
- years: `2024=198.00`, `2025=4487.50`, `2026=986.00`
- worst trade: `-483.00`
- worst day: `2025-11-20`, `-849.00`
- max consecutive losing trades: `3`, `-673.00`

Health gates were not accepted as alpha filters for the raw candidate. The
best full-sample gate was effectively the ungated path. Walk-forward
health-gate selection reduced holdout net materially:

| Candidate | Gate WF | Accepted | Skipped | Accepted Net | Skipped Net | Worst Window |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| raw `80pt_500d_cl0.4` | `40x10` | 142 | 37 | 3132.00 | 1594.50 | -787.00 |
| raw `80pt_500d_cl0.4` | `60x10` | 125 | 24 | 2812.50 | 1435.00 | -787.00 |

Interpretation: dynamic health gates can still be account-level safety locks,
but they did not improve the research edge.

Attribution found a simple static schedule filter worth keeping for the next
round: skip Fridays and skip entries during the `11:00` and `15:00` exchange
time hours.

Same-window comparison against the raw audit:

| Variant | Trades | Net | Avg | Max DD | 2024 | 2025 | 2026 | `40x10` Pos | `40x10` Net | `40x10` Worst |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| raw `80pt_500d_cl0.4` | 236 | 5671.50 | 24.03 | -1257.00 | 198.00 | 4487.50 | 986.00 | 11/13 | 4726.50 | -509.00 |
| no Friday, no `11:00`/`15:00` | 133 | 5978.00 | 44.95 | -784.00 | 621.50 | 4486.00 | 870.50 | 12/13 | 5380.50 | -101.00 |

Filtered fixed walk-forward:

| Window | Positive | Negative | Trades | Net | Avg/Trade | Worst Window |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `20x5` | 21 | 9 | 112 | 5958.00 | 53.20 | -517.00 |
| `40x10` | 12 | 1 | 97 | 5380.50 | 55.47 | -101.00 |
| `60x10` | 10 | 1 | 84 | 4498.00 | 53.55 | -101.00 |

Filtered audit artifacts:

- `reports/mnq-vwap-delta-custom-threshold-sweep-slip1-no-friday-no-11-15.csv`
- `reports/mnq-vwap-delta-filtered-top100-candidate-diagnostics.csv`
- `reports/mnq-vwap-delta-80pt-500d-cl04-fixed-filter-same-window-diagnostics.csv`
- `reports/mnq-vwap-delta-80pt-500d-cl04-no-friday-no-11-15-exit20-120-40-slip1-trade-audit.csv`
- `reports/mnq-vwap-delta-80pt-500d-cl04-no-friday-no-11-15-exit20-120-40-slip1-health-gate-sweep.csv`

The filtered grid re-sweep found higher-net rows, but they were rejected by the
risk lens:

| Candidate | Exit | Trades | Net | Avg | PF | Max DD | 2024 | 2025 | 2026 | Decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `80pt_500d_cl0.5`, no Friday/no `11:00`/`15:00` | `40 / 120 / 200 / initial` | 258 | 8118.00 | 31.47 | 1.28 | -3045.00 | 1329.00 | 7611.50 | -822.50 | reject: 2026 loss and drawdown |
| `80pt_500d_cl0.5`, no Friday/no `11:00`/`15:00` | `30 / 120 / 40 / initial` | 258 | 7654.50 | 29.67 | 1.41 | -1610.00 | 858.50 | 5618.00 | 1178.00 | reject: drawdown |
| `80pt_500d_cl0.4`, no Friday/no `11:00`/`15:00` | `30 / 120 / 40 / initial` | 133 | 6575.50 | 49.44 | 1.86 | -1181.00 | 544.50 | 5080.50 | 950.50 | reject: drawdown |
| `80pt_500d_cl0.4`, no Friday/no `11:00`/`15:00` | `20 / 120 / 40 / initial` | 133 | 5978.00 | 44.95 | 1.98 | -784.00 | 621.50 | 4486.00 | 870.50 | keep |

The kept row was the only top-100 filtered candidate with all years positive,
at least `100` trades, and max realized equity drawdown better than `-1000`.

## Local Neighborhood Sweep

There was still useful room around the filtered lead. A higher-resolution local
grid was run around the kept row:

- VWAP thresholds: `60,70,80,90,100,120`
- Delta thresholds: `400,500,600,800`
- Close-location thresholds: `0.35,0.4,0.45`
- Static schedule filter: no Fridays, no `11:00`/`15:00` exchange-time entries
- Exit grid: first target `15,20,25,30,35`; stop `80,100,120,140`; runner target `30,40,50,60,80`; runner stop `initial,breakeven`

Artifacts:

- `reports/mnq-vwap-delta-local-neighborhood-sweep-slip1-no-friday-no-11-15.csv`
- `reports/mnq-vwap-delta-local-neighborhood-candidate-diagnostics.csv`
- `reports/mnq-vwap-delta-local-neighborhood-shortlist-fixed-walk-forward-summary.csv`
- `reports/mnq-vwap-delta-local-neighborhood-shortlist-slippage-stress.csv`
- `reports/mnq-vwap-delta-local-80pt-400d-cl04-no-friday-no-11-15-exit25-140-40-slip1-trade-audit.csv`

The best candidate under the same acceptance lens is now:

`mnq_vwap_delta_local_fade_80pt_400d_cl0.4_nofri_no11_15`, exit `25 / 140 / 40 / initial`.

| Candidate | Exit | Trades | Net | Avg | PF | Max DD | 2024 | 2025 | 2026 | Worst Day |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| local `80pt_400d_cl0.4` | `25 / 140 / 40 / initial` | 186 | 9584.50 | 51.53 | 2.09 | -976.00 | 1676.50 | 5050.50 | 2857.50 | -563.00 |
| local `60pt_600d_cl0.4` | `25 / 140 / 50 / initial` | 153 | 8655.50 | 56.57 | 2.07 | -857.00 | 1795.00 | 5290.50 | 1570.00 | -796.00 |
| previous filtered `80pt_500d_cl0.4` | `20 / 120 / 40 / initial` | 133 | 5978.00 | 44.95 | 1.98 | -784.00 | 621.50 | 4486.00 | 870.50 | -483.00 |

Fixed walk-forward:

| Candidate | Window | Positive | Negative | Trades | Net | Avg/Trade | Worst Window |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| local `80pt_400d_cl0.4` | `20x5` | 21 | 3 | 157 | 8812.50 | 56.13 | -595.00 |
| local `80pt_400d_cl0.4` | `40x10` | 10 | 0 | 128 | 7626.00 | 59.58 | 241.00 |
| local `80pt_400d_cl0.4` | `60x10` | 8 | 0 | 103 | 5643.00 | 54.79 | 241.00 |

Slippage stress for local `80pt_400d_cl0.4`:

| Slippage Ticks/Contract | Trades | Net | Avg | Max DD | 2024 | 2025 | 2026 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 186 | 9584.50 | 51.53 | -976.00 | 1676.50 | 5050.50 | 2857.50 |
| 2 | 186 | 9398.50 | 50.53 | -979.00 | 1633.50 | 4961.50 | 2803.50 |
| 3 | 186 | 9212.50 | 49.53 | -982.00 | 1590.50 | 4872.50 | 2749.50 |

Loss attribution:

- worst trade: `-563.00`
- worst day: `-563.00`
- negative trade days: `29` of `143`
- max consecutive losing trades: `4`, total `-447.50`
- worst months: `2024-10=-394.50`, `2026-07=-309.00`, `2025-02=-299.50`
- minimum cumulative equity from start: `0.00`
- first cumulative `+500`: trade `4`, `2024-07-18 14:30:00`
- first cumulative `+1000`: trade `26`, `2024-09-30 14:30:00`
- max peak-to-trough drawdown: `2025-05-19 13:12:00` through `2025-06-02 14:51:00`

Health gates did not need to be alpha filters. The best full-sample gate skipped
two bad trades and improved net to `9803.00`, but 40x10 walk-forward gate
selection accepted `7106.00` while skipping `520.00` net. Keep gates as
account-level safety, not as a research edge.

## Micro Neighborhood Stability

A final micro-neighborhood pass tested whether the local lead was a one-cell
optimization artifact.

- VWAP thresholds: `75,80,85`
- Delta thresholds: `300,350,400,450,500`
- Close-location thresholds: `0.375,0.4,0.425`
- Exit grid: first target `20,25,30`; stop `130,140,150`; runner target `35,40,45,50`; runner stop `initial`

Artifact:

- `reports/mnq-vwap-delta-micro-neighborhood-diagnostics.csv`

Acceptance filter: at least `100` trades, all years positive, max drawdown
better than `-1000`, at least `6` fixed `40x10` windows, and zero negative
`40x10` windows.

Result:

- rows tested: `1620`
- accepted rows: `146`
- accepted strategies: `17`
- best full net and best `40x10` holdout net remained local `80pt_400d_cl0.4`, exit `25 / 140 / 40 / initial`

Top accepted rows:

| Candidate | Exit | Trades | Net | Avg | PF | Max DD | 2024 | 2025 | 2026 | `40x10` | `40x10` Net | Worst `40x10` |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `80pt_400d_cl0.4` | `25 / 140 / 40 / initial` | 186 | 9584.50 | 51.53 | 2.09 | -976.00 | 1676.50 | 5050.50 | 2857.50 | 10/10 | 7626.00 | 241.00 |
| `75pt_400d_cl0.4` | `25 / 140 / 35 / initial` | 205 | 9541.00 | 46.54 | 1.97 | -976.00 | 1692.00 | 4496.50 | 3352.50 | 11/11 | 7363.50 | 76.00 |
| `80pt_400d_cl0.4` | `25 / 140 / 45 / initial` | 186 | 9315.00 | 50.08 | 1.98 | -976.00 | 1595.00 | 4993.50 | 2726.50 | 10/10 | 7466.00 | 233.50 |
| `80pt_400d_cl0.4` | `25 / 140 / 35 / initial` | 186 | 9059.00 | 48.70 | 2.08 | -976.00 | 1488.00 | 4803.50 | 2767.50 | 10/10 | 7164.50 | 141.00 |

Interpretation: there is a real plateau around the selected rule. The `75pt`
variant is a viable fallback if we later prefer more trades, but it does not
beat the selected rule on full net or fixed `40x10` holdout net.

## Next Step

Research around this idea is now close to saturated. Continue with implementation
of the local `80pt_400d_cl0.4` candidate:

1. verify mechanics in Sierra replay with MNQ before any live version;
2. keep account-level hard loss controls, but do not add dynamic gates as alpha filters yet;
3. if replay is clean, implement the MNQ bot on a separate branch with the static schedule filter;
4. after implementation, run the same safety scan and DLL syntax checks used for MES.
