# Scaled Context Loss Attribution

Status: **targeted guard research lead, not live-ready**

## Source Summary

- Context rows: `1639`
- Daily rows: `180`

## Worst Days

| Trade Date | Trades | Net USD | Full Stops | Runner Stops |
| --- | ---: | ---: | ---: | ---: |
| 2026-04-13 | 16 | -12012 | 10 | 6 |
| 2025-10-27 | 8 | -7506 | 7 | 1 |
| 2025-12-23 | 15 | -5880 | 7 | 0 |
| 2026-03-31 | 8 | -5756 | 6 | 1 |
| 2026-05-28 | 8 | -5743.5 | 5 | 0 |
| 2025-12-09 | 10 | -5570 | 5 | 4 |
| 2026-03-09 | 6 | -5442 | 5 | 1 |
| 2026-02-25 | 12 | -5434 | 5 | 1 |

## Fixed Theory Guard

- Best fixed guard: `lookback_fade_push_session_range_30`
- Kept trades: `971` of `1639`
- Net USD: `55728`
- Average/trade: `57.39237899`
- Profit factor: `1.17462257`
- Max trade-sequence drawdown: `-14255.5`
- Worst day: `2026-04-13`, `-8916`

## Walk-Forward Theory Guard

- Holdout input trades: `1258`
- Holdout kept trades: `672`
- Unfiltered holdout net USD: `17919`
- Guarded holdout net USD: `46996`
- Guard improvement USD: `29077`

Selected holdout guard counts:

- `lookback_fade_push_session_range_30_after_90m`: `15`
- `lookback_fade_push_session_range_30_risk_avg_2.5`: `5`
- `lookback_fade_push_risk_avg_2.5`: `4`
- `none`: `2`
- `lookback_fade_push_session_range_30`: `2`

## Interpretation

The damage clusters around failed fades where the market does not make a clean push into the fade setup or where the 10-point risk is large relative to recent bar range. The compact guard family keeps the entry hypothesis intact: fade only after a real direction-aware lookback push, prefer at least 30 points of session range, and avoid compressed volatility when the stop is too wide for the current tape.

This is still research. The next validation step is to rerun the same guard family on a later export and then wire only the selected fixed conditions into Sierra if the improvement survives.
