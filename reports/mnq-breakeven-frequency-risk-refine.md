# MNQ Breakeven-Frequency Risk Refinement

Status: risk-geometry refinement around the first filtered MNQ breakeven-frequency near-leads.

## Fixed Signal Family

- base strategy: `lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:end1230:skipfri1:maxday1:space30`
- filters tested: `short_only, short_only__vwapdist_lte120, weekday_mon_tue_wed__lbmove_lte80, weekday_mon_tue_wed__lbmove_lte120, weekday_not_thu__lbmove_lte80, weekday_not_thu__lbmove_lte120, prev5_lte30, weekday_tue_wed_thu__absdelta_lte1600`
- source rows: `67300`
- source dates: `2024-07-15` through `2026-07-02`
- risk grid: first target `15-35`, initial stop `25-50`, runner target `40-120`, splits `1+1`, `2+1`, `3+1`, `2+2`

## Result

Accepted rows by the current risk lens: `390`.

Best accepted row:

| Metric | Value |
| --- | ---: |
| Filter | `short_only__vwapdist_lte120` |
| Quantity / split | `4 / 3+1` |
| First target / stop / runner | `30 / 50 / 120` |
| Trades | `128` |
| Trades/week | `1.24965132` |
| First-target reach | `75.0%` |
| Full-stop rate | `25.0%` |
| Net | `$7603.5` |
| PF | `1.58524477` |
| Latest-year net | `$2236` |
| Worst quarter | `$-638` |
| Max trade-sequence DD | `$-1624` |

## Top Rows

| Rank | Filter | Qty | Split | T1 / Stop / Runner | Trades | /Wk | T1 Hit | Stop | Net | PF | Latest | Worst Q | DD |
| ---: | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `short_only__vwapdist_lte120` | 4 | 3+1 | 30 / 50 / 120 | 128 | 1.24965132 | 75.0% | 25.0% | 7603.5 | 1.58524477 | 2236 | -638 | -1624 |
| 2 | `short_only__vwapdist_lte120` | 4 | 3+1 | 30 / 50 / 100 | 128 | 1.24965132 | 75.0% | 25.0% | 7563.5 | 1.58216595 | 2276 | -638 | -1624 |
| 3 | `short_only__vwapdist_lte120` | 4 | 3+1 | 30 / 50 / 80 | 128 | 1.24965132 | 75.0% | 25.0% | 7443.5 | 1.5729295 | 2076 | -652 | -1624 |
| 4 | `short_only__vwapdist_lte120` | 4 | 3+1 | 30 / 45 / 120 | 128 | 1.24965132 | 72.7% | 27.3% | 7263.5 | 1.56701795 | 2436 | -792 | -1746 |
| 5 | `short_only__vwapdist_lte120` | 4 | 3+1 | 30 / 45 / 100 | 128 | 1.24965132 | 72.7% | 27.3% | 7223.5 | 1.56389539 | 2476 | -832 | -1692 |
| 6 | `short_only__vwapdist_lte120` | 4 | 3+1 | 30 / 45 / 80 | 128 | 1.24965132 | 72.7% | 27.3% | 7103.5 | 1.55452771 | 2276 | -872 | -1692 |
| 7 | `short_only__vwapdist_lte120` | 3 | 2+1 | 30 / 50 / 120 | 128 | 1.24965132 | 75.0% | 25.0% | 5235.5 | 1.53730501 | 1632 | -598.5 | -1249.5 |
| 8 | `short_only__vwapdist_lte120` | 3 | 2+1 | 30 / 50 / 100 | 128 | 1.24965132 | 75.0% | 25.0% | 5195.5 | 1.53319992 | 1672 | -619 | -1322 |
| 9 | `short_only__vwapdist_lte120` | 4 | 3+1 | 30 / 50 / 60 | 128 | 1.24965132 | 75.0% | 25.0% | 6832 | 1.52586207 | 1996 | -692 | -1624 |
| 10 | `short_only__vwapdist_lte120` | 3 | 2+1 | 30 / 45 / 120 | 128 | 1.24965132 | 72.7% | 27.3% | 5025.5 | 1.52308093 | 1782 | -729 | -1474.5 |
| 11 | `short_only__vwapdist_lte120` | 3 | 2+1 | 30 / 50 / 80 | 128 | 1.24965132 | 75.0% | 25.0% | 5075.5 | 1.52088465 | 1472 | -659 | -1249.5 |
| 12 | `short_only__vwapdist_lte120` | 3 | 2+1 | 30 / 45 / 100 | 128 | 1.24965132 | 72.7% | 27.3% | 4985.5 | 1.51891751 | 1822 | -769 | -1344 |

## Best By Filter

| Filter | Qty | Split | T1 / Stop / Runner | Trades | Net | PF | Latest | Worst Q | DD |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `short_only__vwapdist_lte120` | 4 | 3+1 | 30 / 50 / 120 | 128 | 7603.5 | 1.58524477 | 2236 | -638 | -1624 |
| `short_only` | 4 | 3+1 | 25 / 50 / 80 | 158 | 6632 | 1.45374932 | 1568 | -1190 | -1818 |
| `weekday_mon_tue_wed__lbmove_lte80` | 4 | 3+1 | 35 / 40 / 100 | 144 | 6247.5 | 1.3527668 | 984.5 | -494 | -2299.5 |
| `weekday_not_thu__lbmove_lte80` | 4 | 3+1 | 35 / 40 / 100 | 144 | 6247.5 | 1.3527668 | 984.5 | -494 | -2299.5 |
| `weekday_mon_tue_wed__lbmove_lte120` | 2 | 1+1 | 30 / 45 / 100 | 206 | 2768.5 | 1.22731751 | 652.5 | -1112 | -1614 |
| `weekday_not_thu__lbmove_lte120` | 2 | 1+1 | 30 / 45 / 100 | 206 | 2768.5 | 1.22731751 | 652.5 | -1112 | -1614 |
| `prev5_lte30` | 4 | 2+2 | 30 / 45 / 80 | 84 | 4970 | 1.5431694 | 903 | -460 | -1444 |
| `weekday_tue_wed_thu__absdelta_lte1600` | 3 | 2+1 | 30 / 45 / 100 | 106 | 4189 | 1.49227334 | 2848 | -1187.5 | -2099 |

## Interpretation

This pass tests whether the breakeven-frequency idea is a risk-management problem or an entry-quality problem. If the accepted set stays empty, the answer is entry quality: the target-one touch is real, but the entry family is not strong enough to carry a robust managed-exit bot.
