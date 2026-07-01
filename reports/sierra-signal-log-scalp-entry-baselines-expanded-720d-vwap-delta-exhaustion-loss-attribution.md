# Scaled Context Loss Attribution

Status: **targeted guard research lead, not live-ready**

## Source Summary

- Context rows: `5972`
- Daily rows: `485`

## Worst Days

| Trade Date | Trades | Net USD | Full Stops | Runner Stops |
| --- | ---: | ---: | ---: | ---: |
| 2025-02-05 | 19 | -15420.5 | 14 | 4 |
| 2026-04-13 | 20 | -15040 | 13 | 7 |
| 2025-01-23 | 16 | -13312 | 12 | 4 |
| 2024-11-19 | 19 | -12933 | 12 | 3 |
| 2025-01-06 | 15 | -12780 | 13 | 1 |
| 2025-07-15 | 20 | -12540 | 14 | 3 |
| 2025-09-19 | 15 | -12305 | 13 | 0 |
| 2025-07-02 | 14 | -12173 | 10 | 0 |

## Fixed Theory Guard

- Best fixed guard: `lookback_fade_push_session_range_30_risk_avg_2.5`
- Kept trades: `2276` of `5972`
- Net USD: `10755.5`
- Average/trade: `4.72561511`
- Profit factor: `1.01186291`
- Max trade-sequence drawdown: `-109565.5`
- Worst day: `2025-08-07`, `-10448`

## Walk-Forward Theory Guard

- Holdout input trades: `5429`
- Holdout kept trades: `3712`
- Unfiltered holdout net USD: `-236753`
- Guarded holdout net USD: `-80546.5`
- Guard improvement USD: `156206.5`

Selected holdout guard counts:

- `none`: `34`
- `lookback_fade_push_session_range_30`: `25`
- `lookback_fade_push_session_range_30_after_90m`: `21`
- `lookback_fade_push_session_range_30_risk_avg_2.5`: `5`
- `lookback_fade_push`: `2`
- `lookback_fade_push_risk_avg_2.5`: `2`

## Interpretation

The damage clusters around failed fades where the market does not make a clean push into the fade setup or where the 10-point risk is large relative to recent bar range. The compact guard family keeps the entry hypothesis intact: fade only after a real direction-aware lookback push, prefer at least 30 points of session range, and avoid compressed volatility when the stop is too wide for the current tape.

This is still research. The next validation step is to rerun the same guard family on a later export and then wire only the selected fixed conditions into Sierra if the improvement survives.
