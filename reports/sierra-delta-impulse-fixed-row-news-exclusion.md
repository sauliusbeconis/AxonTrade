# Sierra Delta Impulse Fixed Row News Exclusion

Status: **diagnostic only**

## Sources

- Scheduled news calendar: `config/research/us_scheduled_news_events_2026_06.csv`
- Annotated outcomes:
  `reports/sierra-delta-impulse-fixed-row-news-annotated-outcomes.csv`
- Outcome source:
  `data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv`
- Official source URLs are stored per event row in the calendar CSV.
- Retrieved date for calendar rows: `2026-06-29`

## Summary

- calendar events: `17`
- annotated fixed-row outcomes: `163`
- rows inside scheduled-news blackout windows: `1`
- all-row net USD: `-15716`
- news-excluded trades: `162`
- news-excluded net USD: `-15409`

## Blackout Row

| Entry Time | Signal ID | Direction | Exit Reason | Net USD | Event | Minutes From Event |
| --- | --- | --- | --- | ---: | --- | ---: |
| `2026-06-24 10:15:00` | `delta_impulse_continue_10bar_2.5pt_50d_ESU26-CME_7610` | `short` | `runner_initial_stop_hit` | `-307` | `census-new-home-sales-2026-06-24` | `15` |

## Interpretation

The June scheduled-news calendar removes one losing current-sample trade, but
the fixed row remains strongly negative. News exclusion does not rescue the
Delta Impulse fixed row on the expanded sample.
