# MNQ VWAP Delta Expanded 720D Research

Status: **filtered research lead found, not implementation-ready**

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

- `reports/mnq-vwap-delta-80pt-500d-cl04-fixed-filter-same-window-diagnostics.csv`
- `reports/mnq-vwap-delta-80pt-500d-cl04-no-friday-no-11-15-exit20-120-40-slip1-trade-audit.csv`
- `reports/mnq-vwap-delta-80pt-500d-cl04-no-friday-no-11-15-exit20-120-40-slip1-health-gate-sweep.csv`

## Next Step

Continue research on the filtered `80pt_500d_cl0.4` candidate:

1. verify mechanics in Sierra replay with MNQ before any live version;
2. keep account-level hard loss controls, but do not add dynamic gates as alpha filters yet;
3. if replay is clean, implement the MNQ bot on a separate branch with the static schedule filter;
4. after implementation, run the same safety scan and DLL syntax checks used for MES.
