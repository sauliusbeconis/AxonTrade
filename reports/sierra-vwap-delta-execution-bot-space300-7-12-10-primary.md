# VWAP Delta Execution Bot Primary 300s Candidate

Status: full-sample and rolling robustness accepted; ready for code-default implementation and Sierra replay test.

- Candidate: `space300_all_exit7_12_10_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400`
- Source export: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_Expanded.txt`
- Signal count before guards: `6215`
- Filtered trades before daily loss lock: `640`
- Accepted trades after daily loss lock: `588`
- Daily loss skipped trades: `52`; skipped net `-18464`
- Net USD: `66584`
- Average/trade: `113.24`
- Profit factor: `1.2953`
- Max trade-sequence drawdown: `-12462`
- Worst day: `2025-02-28` `-3160`
- Long/short trades: `303` / `285`

## Period Summary

| Period | Trades | Net | Avg | PF | DD | Worst Day | Long | Short | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 2024 | 63 | 4884 | 77.52 | 1.1924 | -4674 | 2024-08-01 -2464 | 38 | 25 | 5 |
| 2025 | 312 | 8716 | 27.94 | 1.0644 | -12462 | 2025-02-28 -3160 | 170 | 142 | 35 |
| 2026 | 213 | 52984 | 248.75 | 1.8172 | -4562 | 2026-01-02 -2464 | 95 | 118 | 12 |

Detailed trade-audit and period-summary CSVs are generated local artifacts by
default. This Markdown report is the durable evidence anchor.
