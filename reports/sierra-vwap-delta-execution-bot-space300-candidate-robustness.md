# VWAP Delta Execution Bot 300s Candidate Robustness

Status: research validation for full-sample gate-passing candidates.

- Source export: `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_Expanded.txt`
- Signals: `6215` at 300-second raw candidate spacing
- Robustness CSV: generated local artifact; this Markdown table is the durable
  evidence anchor.

| Candidate | Train | Holdout | Step | Windows | Unguarded Net | Guarded Net | Improvement | Kept Trades | Avg | Neg Rate | Worst Window | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| space300_all_exit7_12_8_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400 | 20 | 5 | 5 | 97 | -239079 | 68257 | 307336 | 574 | 118.91 | 0.268 | -5316 | True |
| space300_all_exit7_12_8_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400 | 40 | 5 | 5 | 93 | -198870 | 65695 | 264564 | 565 | 116.27 | 0.280 | -5316 | True |
| space300_all_exit7_12_8_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400 | 40 | 10 | 10 | 46 | -201280 | 57185 | 258464 | 545 | 104.93 | 0.391 | -6584 | False |
| space300_all_exit7_12_8_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400 | 60 | 10 | 10 | 44 | -208526 | 56679 | 265204 | 528 | 107.35 | 0.386 | -6584 | False |
| space300_all_exit7_12_8_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400 | 80 | 10 | 10 | 42 | -157742 | 55757 | 213498 | 524 | 106.41 | 0.381 | -6584 | False |
| space300_all_exit7_12_10_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400 | 20 | 5 | 5 | 97 | -249766 | 68560 | 318326 | 570 | 120.28 | 0.278 | -5118 | True |
| space300_all_exit7_12_10_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400 | 40 | 5 | 5 | 93 | -206044 | 65298 | 271342 | 561 | 116.40 | 0.290 | -5118 | True |
| space300_all_exit7_12_10_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400 | 40 | 10 | 10 | 46 | -207354 | 58388 | 265742 | 541 | 107.93 | 0.348 | -6642 | True |
| space300_all_exit7_12_10_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400 | 60 | 10 | 10 | 44 | -222750 | 56782 | 279532 | 524 | 108.36 | 0.341 | -6642 | True |
| space300_all_exit7_12_10_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400 | 80 | 10 | 10 | 42 | -167879 | 56660 | 224539 | 520 | 108.96 | 0.333 | -6642 | True |
| space300_short_exit5_10_10_initial_lb-2.5_smin30_risk1.75_omin-60_smax100_after0_daily2400 | 20 | 5 | 5 | 97 | -275166 | 58918 | 334084 | 551 | 106.93 | 0.268 | -5198 | True |
| space300_short_exit5_10_10_initial_lb-2.5_smin30_risk1.75_omin-60_smax100_after0_daily2400 | 40 | 5 | 5 | 93 | -232707 | 54802 | 287509 | 539 | 101.67 | 0.280 | -5198 | True |
| space300_short_exit5_10_10_initial_lb-2.5_smin30_risk1.75_omin-60_smax100_after0_daily2400 | 40 | 10 | 10 | 46 | -232342 | 56186 | 288528 | 527 | 106.61 | 0.304 | -5486 | True |
| space300_short_exit5_10_10_initial_lb-2.5_smin30_risk1.75_omin-60_smax100_after0_daily2400 | 60 | 10 | 10 | 44 | -231300 | 55076 | 286376 | 507 | 108.63 | 0.295 | -5486 | True |
| space300_short_exit5_10_10_initial_lb-2.5_smin30_risk1.75_omin-60_smax100_after0_daily2400 | 80 | 10 | 10 | 42 | -191029 | 53486 | 244515 | 502 | 106.55 | 0.310 | -5486 | True |

## Failures

- `space300_all_exit7_12_8_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400` 40x10 step 10: `negative_rate>0.35`
- `space300_all_exit7_12_8_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400` 60x10 step 10: `negative_rate>0.35`
- `space300_all_exit7_12_8_initial_lb-15_smin30_risk1.71429_omin-80_smax100_after0_daily2400` 80x10 step 10: `negative_rate>0.35`
