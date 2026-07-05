# MNQ Eval-Pass Wave Rider Slippage Stress

Status: first-pass stress note, superseded for current candidate selection by
`reports/mnq-eval-pass-wave-rider-new-lead-refine.md`.

Source report: `reports/mnq-eval-pass-wave-rider-research.md`

Stress model:

- same signals and target/stop point distances as the selected rows;
- commission stays `$0.50/side`;
- total slippage ticks per contract stressed from `1` to `4`;
- this tests extra transaction cost only, not missed fills or partial fills.

## Candidates

| Candidate | Strategy | Qty | Target Points | Stop Points | Role |
| --- | --- | ---: | ---: | ---: | --- |
| practical | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:filterabsdelta1000` | 10 | 33.25 | 31.75 | balanced pass-rate row |
| conservative | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` | 5 | 65.75 | 64.25 | lower-size locked candidate |
| fast | `lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:filterabsdelta1000` | 12 | 30.00 | 32.50 | fastest two-day lead |

The `$650` practical target is preferred over `$625` for eval use because two
`$625` wins can fail the two-day pass objective after worse-than-modeled fills.

## Stress Results

| Candidate | Slippage Ticks | Net | Avg | PF | Max DD | 2026 Net | Worst Quarter | Signal Pass | 2-Day | Signal Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| practical | 1 | 10425 | 208.5 | 2.00 | -1950 | 1300 | -1300 | 88.0% | 38.0% | 8.0% |
| practical | 2 | 10175 | 203.5 | 1.97 | -1965 | 1260 | -1315 | 86.0% | 38.0% | 8.0% |
| practical | 3 | 9925 | 198.5 | 1.94 | -1980 | 1220 | -1330 | 86.0% | 38.0% | 8.0% |
| practical | 4 | 9675 | 193.5 | 1.91 | -1995 | 1180 | -1345 | 86.0% | 38.0% | 8.0% |
| conservative | 1 | 11958 | 209.8 | 2.15 | -1608 | 3690 | -40 | 75.4% | 24.6% | 5.3% |
| conservative | 2 | 11815 | 207.3 | 2.13 | -1628 | 3665 | -50 | 75.4% | 24.6% | 5.3% |
| conservative | 3 | 11672 | 204.8 | 2.11 | -1648 | 3640 | -60 | 75.4% | 24.6% | 7.0% |
| conservative | 4 | 11530 | 202.3 | 2.10 | -1668 | 3615 | -70 | 75.4% | 24.6% | 8.8% |
| fast | 1 | 15312 | 268.6 | 2.20 | -1692 | 2520 | -894 | 86.0% | 47.4% | 7.0% |
| fast | 2 | 14970 | 262.6 | 2.16 | -1716 | 2460 | -918 | 84.2% | 47.4% | 10.5% |
| fast | 3 | 14628 | 256.6 | 2.13 | -1740 | 2400 | -942 | 84.2% | 47.4% | 10.5% |
| fast | 4 | 14286 | 250.6 | 2.09 | -1764 | 2340 | -966 | 84.2% | 47.4% | 10.5% |

## Interpretation

The old `lb10` / `abs_delta<=1172` candidate was superseded after correcting
the main sweep default from `80` minimum signals to the intended `40` minimum.
The stronger family is now:

`lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:filterabsdelta1000`

The conservative `5 MNQ` row is the safest implementation seed: it has the
lowest stressed fail rate and the best worst-quarter behavior, but its two-day
pass rate is lower.

The `12 MNQ` row is the fastest eval-pass lead: it keeps the two-day pass rate
near `47%` under the slippage stress tested here, but it risks about `$800` on a
single stop.

Next gates:

- replay/mechanics test the conservative `5 MNQ` version first;
- only consider the `12 MNQ` fast version after confirming fills, bracket
  behavior, and account risk comfort;
- do not build adaptive parameter selection from the current walk-forward pass.
