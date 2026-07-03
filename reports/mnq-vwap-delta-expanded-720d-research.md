# MNQ VWAP Delta Expanded 720D Research

Status: **research lead found, not implementation-ready**

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

## Shortlist

| Candidate | Exit | Trades | Net | Avg | PF | Max DD | 2024 | 2025 | 2026 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `80pt_500d_cl0.4` | `20 / 120 / 40 / initial` | 236 | 5671.50 | 24.03 | 1.4020 | -1257.00 | 198.00 | 4487.50 | 986.00 |
| `40pt_500d_cl0.4` | `10 / 120 / 20 / initial` | 492 | 5222.50 | 10.61 | 1.2780 | -1300.00 | 447.00 | 3696.50 | 1079.00 |
| `20pt_1500d_cl0.4` | `60 / 120 / 100 / initial` | 57 | 4873.00 | 85.49 | 1.8245 | -1902.00 | 298.50 | 2833.50 | 1741.00 |

The best balance is currently:

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

The `80pt_500d_cl0.4` row is the first MNQ research lead that is not immediately
rejected:

- positive full sample
- positive 2024, 2025, and 2026
- positive fixed walk-forward
- survives 3 ticks total slippage per contract
- lower drawdown than the higher-net full-sample rows

It is still not live-ready because the stop is wide (`120` MNQ points), the
sample has only `236` trades, and no risk gate or mechanics replay has been
tested yet.

## Next Step

Continue research on the `80pt_500d_cl0.4` candidate:

1. run daily risk lock and drawdown-control sweeps;
2. check month/day loss attribution, especially 2025 and 2026 loss clusters;
3. verify mechanics in Sierra replay with MNQ before any live version;
4. only then decide whether this becomes an MNQ bot branch.
