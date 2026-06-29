# Sierra Delta Impulse Fixed Row Context And Regime Filters

Status: **diagnostic only**

## Sources

- Bars export:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport_DeltaImpulse_3Min_Large.txt`
- Signal log:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_DeltaImpulseSignalLog.csv`
- Fixed-row outcomes:
  `data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv`
- Context diagnostics:
  `reports/sierra-delta-impulse-fixed-row-context-diagnostics.csv`
- Main walk-forward output:
  `reports/sierra-delta-impulse-fixed-row-context-filter-walk-forward.csv`
- Old-shape non-overlap output:
  `reports/sierra-delta-impulse-fixed-row-context-filter-oldshape-nonoverlap-walk-forward.csv`
- Regime test outputs:
  `reports/sierra-delta-impulse-fixed-row-regime-filter-walk-forward.csv`
  `reports/sierra-delta-impulse-fixed-row-regime-net-filter-walk-forward.csv`
  `reports/sierra-delta-impulse-fixed-row-regime-filter-oldshape-nonoverlap-walk-forward.csv`
  `reports/sierra-delta-impulse-fixed-row-regime-net-filter-oldshape-nonoverlap-walk-forward.csv`

## Method

- context rows: `163`
- trade dates: `41`
- all fixed-row net USD: `-15716`
- base exit row: `5 / 10 / 8 / initial`
- context lookback: `20` prior 3-minute bars
- base features: normalized risk, normalized runner target, normalized signal
  delta sum, entry volume ratio, entry trade-count ratio
- added regime features: session range position, continuation/fade edge,
  opening-range continuation edge, directional opening-range breakout,
  lookback efficiency/choppiness, entry/session volume ratio, and
  lookback/session volume ratio

## Walk-Forward Results

| Variant | Windows | Selected Trades | Selected Net USD | Selected Avg USD | Unfiltered Trades | Unfiltered Net USD | Unfiltered Avg USD | Participation | Improvement Vs Unfiltered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20x5 default net | 4 | 13 | -2191 | -168.54 | 111 | -7927 | -71.41 | 11.7% | 5736 |
| 20x5 regime efficiency | 4 | 23 | -6811 | -296.13 | 111 | -7927 | -71.41 | 20.7% | 1116 |
| 20x5 regime net | 4 | 31 | -9567 | -308.61 | 111 | -7927 | -71.41 | 27.9% | -1640 |
| 8x2 default net non-overlap | 16 | 64 | -1198 | -18.72 | 141 | -12862 | -91.22 | 45.4% | 11664 |
| 8x2 regime efficiency non-overlap | 16 | 61 | -4627 | -75.85 | 141 | -12862 | -91.22 | 43.3% | 8235 |
| 8x2 regime net non-overlap | 16 | 65 | -5705 | -87.77 | 141 | -12862 | -91.22 | 46.1% | 7157 |

## Interpretation

The user challenge was correct: the context-filter family should not be treated
as worthless just because the unfiltered fixed Delta Impulse row failed.

The best expanded-sample evidence is the `8x2 default net non-overlap` run. It
reduced average holdout loss from `-$91.22` to `-$18.72` per trade while taking
about `45%` of same-window holdout trades. That is a real exposure-quality
improvement and a large loss-avoidance effect.

The same evidence is not yet deployable. The selected holdout is still negative
after costs, and the first added regime filters did not improve the result.
Trend-edge, opening-range breakout, efficiency, choppiness, and session-volume
thresholds made the broad tests worse in both the `20x5` and `8x2` walk-forward
shapes.

The current decision is:

- reject raw unfiltered Delta Impulse continuation;
- reject the first broad regime-filter grid;
- keep normalized context filtering as an active research direction because it
  materially reduces bad exposure on the expanded sample.

The next useful test is not another broad grid. It should be a targeted veto or
quality model for the losing selected windows, using the enriched context CSV to
identify which selected states still produce full-stop clusters.
