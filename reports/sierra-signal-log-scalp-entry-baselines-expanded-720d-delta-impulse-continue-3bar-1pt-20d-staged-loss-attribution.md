# Scaled Context Loss Attribution

Status: **targeted guard research lead, not live-ready**

## Source Summary

- Context rows: `3877`
- Daily rows: `485`

## Worst Days

| Trade Date | Trades | Net USD | Full Stops | Runner Stops |
| --- | ---: | ---: | ---: | ---: |
| 2024-08-21 | 8 | -7156 | 5 | 3 |
| 2025-04-15 | 8 | -7156 | 5 | 3 |
| 2025-05-12 | 8 | -7156 | 5 | 3 |
| 2025-09-15 | 8 | -6993.5 | 6 | 0 |
| 2024-12-17 | 8 | -6706 | 6 | 0 |
| 2024-08-20 | 8 | -6456 | 6 | 1 |
| 2026-06-24 | 8 | -6456 | 6 | 1 |
| 2024-10-10 | 8 | -6256 | 4 | 4 |

## Fixed Theory Guard

- Best fixed guard: `none`
- Kept trades: `3877` of `3877`
- Net USD: `35886`
- Average/trade: `9.25612587`
- Profit factor: `1.01991316`
- Max trade-sequence drawdown: `-97859.5`
- Worst day: `2024-08-21`, `-7156`

## Walk-Forward Theory Guard

- Holdout input trades: `3557`
- Holdout kept trades: `3557`
- Unfiltered holdout net USD: `35451`
- Guarded holdout net USD: `35451`
- Guard improvement USD: `0`

Selected holdout guard counts:

- `none`: `89`

## Interpretation

The damage clusters around failed fades where the market does not make a clean push into the fade setup or where the 10-point risk is large relative to recent bar range. The compact guard family keeps the entry hypothesis intact: fade only after a real direction-aware lookback push, prefer at least 30 points of session range, and avoid compressed volatility when the stop is too wide for the current tape.

This is still research. The next validation step is to rerun the same guard family on a later export and then wire only the selected fixed conditions into Sierra if the improvement survives.
