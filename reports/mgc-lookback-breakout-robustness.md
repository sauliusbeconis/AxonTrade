# MGC Lookback Breakout Robustness

Status: sensitivity test around the promoted fixed MGC lookback-breakout lead.

## Source

- rows: `813388`
- dates: `2024-03-17` through `2026-07-03`
- holdout windows: `120x40, 180x40, 240x60`
- minimum trades per reported row: `100`

## Top Base-Cost Rows

| Rank | Variant | Trades | Net | PF | DD | Latest | Recent120 | Worst Q | Holdout Net | Holdout PF | Pos/Windows | Worst Window |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `promoted_lead` | 338 | 10893 | 1.58479626 | -827 | 4735 | 4047 | -397 | 27710 | 1.75936532 | 25/26 | -400 |
| 2 | `robust:lb10:cl0.55:mon_tue_fri:delta100:0820_1030:both:t25:s15` | 337 | 10775 | 1.58161503 | -771 | 4335 | 3647 | -397 | 27383 | 1.7566873 | 25/26 | -299 |
| 3 | `robust:lb10:cl0.5:mon_tue_fri:delta150:0820_1030:both:t25:s15` | 348 | 11777 | 1.60145039 | -791 | 4308 | 4020 | -397 | 28657 | 1.73205436 | 25/26 | -77 |
| 4 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0820_1030:both:t30:s15` | 338 | 9950 | 1.51323052 | -946 | 4864 | 4101 | -397 | 24172 | 1.62838277 | 24/26 | -413 |
| 5 | `robust:lb10:cl0.5:mon_tue_fri:delta50:0820_1030:both:t25:s15` | 284 | 7881 | 1.51419064 | -947 | 3834 | 3400 | -316 | 16924 | 1.58544348 | 22/26 | -867 |
| 6 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0820_1030:both:t20:s12` | 338 | 7340 | 1.4157227 | -1366 | 3475 | 2927 | -371 | 18241 | 1.53522491 | 22/26 | -779 |
| 7 | `robust:lb5:cl0.5:mon_tue_fri:delta100:0820_1030:both:t25:s15` | 352 | 7271 | 1.33396105 | -1492 | 3677 | 3389 | -435 | 19380 | 1.44860073 | 21/26 | -840 |
| 8 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0820_1030:long:t25:s15` | 262 | 6907 | 1.47955287 | -1143 | 2575 | 2135 | -316 | 18049 | 1.64203899 | 20/26 | -978 |
| 9 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0900_1030:both:t25:s15` | 326 | 5589 | 1.28512397 | -1348 | 2516 | 1834 | -465 | 12720 | 1.32456431 | 19/26 | -701 |
| 10 | `robust:lb15:cl0.5:mon_tue_fri:delta100:0820_1030:both:t25:s15` | 325 | 3082 | 1.15213743 | -1200 | 1191 | 999 | -327 | 5292 | 1.12829402 | 17/26 | -1006 |
| 11 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0930_1030:both:t25:s15` | 293 | 5194 | 1.32759382 | -1367 | 3534 | 3252 | -758 | 6474 | 1.1915668 | 16/26 | -955 |
| 12 | `robust:lb10:cl0.5:mon_fri:delta100:0820_1030:both:t25:s15` | 224 | 10061 | 1.90063557 | -792 | 4135 | 3543 | -170 | 23099 | 2.07009173 | 24/26 | -516 |
| 13 | `robust:lb10:cl0.5:mon_tue:delta100:0820_1030:both:t25:s15` | 228 | 7485 | 1.62121338 | -945 | 3087 | 2895 | -245 | 20767 | 1.84849847 | 24/26 | -99 |
| 14 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0820_1030:short:t25:s15` | 200 | 2615 | 1.20796882 | -1090 | 1516 | 1268 | -157 | 4982 | 1.20824277 | 18/26 | -938 |

## Top Stress Rows

| Rank | Variant | Trades | Net | PF | DD | Latest | Recent120 | Worst Q | Holdout Net | Holdout PF | Pos/Windows | Worst Window |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `promoted_lead` | 338 | 9203 | 1.47474852 | -872 | 4365 | 3707 | -422 | 24520 | 1.64722186 | 25/26 | -520 |
| 2 | `robust:lb10:cl0.55:mon_tue_fri:delta100:0820_1030:both:t25:s15` | 337 | 9090 | 1.47137523 | -822 | 3965 | 3307 | -422 | 24208 | 1.64413815 | 25/26 | -419 |
| 3 | `robust:lb10:cl0.5:mon_tue_fri:delta150:0820_1030:both:t25:s15` | 348 | 10037 | 1.49331564 | -836 | 3928 | 3670 | -422 | 25332 | 1.62417149 | 24/26 | -197 |
| 4 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0820_1030:both:t30:s15` | 338 | 8260 | 1.40945819 | -981 | 4494 | 3761 | -422 | 20982 | 1.52540378 | 24/26 | -533 |
| 5 | `robust:lb10:cl0.5:mon_tue_fri:delta50:0820_1030:both:t25:s15` | 284 | 6461 | 1.40436851 | -1022 | 3574 | 3160 | -341 | 14414 | 1.47922069 | 22/26 | -982 |
| 6 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0820_1030:both:t20:s12` | 338 | 5650 | 1.30580212 | -1436 | 3105 | 2587 | -561 | 15051 | 1.4227809 | 21/26 | -894 |
| 7 | `robust:lb5:cl0.5:mon_tue_fri:delta100:0820_1030:both:t25:s15` | 352 | 5511 | 1.24333274 | -1872 | 3287 | 3029 | -635 | 16010 | 1.35692788 | 21/26 | -960 |
| 8 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0820_1030:long:t25:s15` | 262 | 5597 | 1.37323286 | -1349 | 2305 | 1890 | -341 | 15619 | 1.53504385 | 20/26 | -1078 |
| 9 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0900_1030:both:t25:s15` | 326 | 3959 | 1.19379314 | -1793 | 2161 | 1504 | -665 | 9700 | 1.23819463 | 19/26 | -821 |
| 10 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0930_1030:both:t25:s15` | 293 | 3729 | 1.2249638 | -1655 | 3239 | 2982 | -913 | 3839 | 1.10918968 | 14/26 | -1055 |
| 11 | `robust:lb15:cl0.5:mon_tue_fri:delta100:0820_1030:both:t25:s15` | 325 | 1457 | 1.06914061 | -1528 | 846 | 674 | -479 | 2287 | 1.05340463 | 14/26 | -1126 |
| 12 | `robust:lb10:cl0.5:mon_tue:delta100:0820_1030:both:t25:s15` | 228 | 6345 | 1.50590018 | -1045 | 2847 | 2675 | -265 | 18597 | 1.73306003 | 24/26 | -179 |
| 13 | `robust:lb10:cl0.5:mon_fri:delta100:0820_1030:both:t25:s15` | 224 | 8941 | 1.76812715 | -842 | 3890 | 3318 | -185 | 20999 | 1.93520086 | 23/26 | -596 |
| 14 | `robust:lb10:cl0.5:mon_tue_fri:delta100:0820_1030:short:t25:s15` | 200 | 1615 | 1.12315083 | -1165 | 1321 | 1078 | -287 | 3277 | 1.13180758 | 17/26 | -1008 |

## Promoted Lead Rows

| Slip | Trades | Net | PF | DD | Latest | Recent120 | Worst Q | Holdout Net | Holdout PF | Pos/Windows | Worst Window |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 338 | 10893 | 1.58479626 | -827 | 4735 | 4047 | -397 | 27710 | 1.75936532 | 25/26 | -400 |
| 6 | 338 | 9203 | 1.47474852 | -872 | 4365 | 3707 | -422 | 24520 | 1.64722186 | 25/26 | -520 |

## Interpretation

This is a robustness screen, not a replacement optimizer. If a nearby variant beats the promoted lead, it should be treated as a lead for manual review only if it keeps enough trades, holds under slippage, and improves the same holdout windows without relying on a tiny time or direction subset.

Result from this pass: keep the promoted fixed rule. The `delta150` variant has slightly higher full-sample and holdout net, and the Mon/Fri-only variant has higher PF, but the promoted lead has the best overall base/stress balance with `338` trades and `25 / 26` positive holdout windows under both base and stress cost.
