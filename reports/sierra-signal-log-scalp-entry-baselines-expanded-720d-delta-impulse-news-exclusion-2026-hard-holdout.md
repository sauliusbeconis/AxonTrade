# Delta Impulse News Exclusion 2026 Hard Holdout

Status: research lead, not live-ready.

## Setup

- Candidate: `delta_impulse_continue_3bar_1pt_20d`
- Exit: `first_target=6`, `stop=12`, `runner_target=20`, `runner_stop=initial`
- Entry throttle: `max_rule_entries_per_day=8`, `minimum_spacing_seconds=900`
- Cost model: ES, `slippage_ticks_per_contract=1`
- Train/selection period: 2024-2025 only
- Hard holdout: 2026 only
- Local news calendar used: `data/processed/AxonTrade_US_news_events.csv`
- Calendar coverage found locally: June 2026 only, 17 scheduled events on 9 dates

## Results

| Variant | 2026 Raw Net | 2026 Fixed Health Gate Net | Accepted | Skipped | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| No news filter | -66318.5 | -6848 | 389 | 619 | -18680 |
| Event windows from local calendar | -64090.5 | -12796 | 378 | 626 | -21144 |
| 30m before / 60m after | -60998.5 | -7748 | 389 | 609 | -18680 |
| 60m before / 120m after | -56298.5 | -10572 | 371 | 602 | -22332 |
| 120m before / 180m after | -53834.5 | -4468 | 374 | 572 | -18413.5 |
| Entire local news dates skipped | -49214.5 | 152 | 364 | 572 | -18413.5 |

## Interpretation

The available June-only news calendar is too incomplete to validate a 2026 news filter.

However, the direction is useful: skipping entire available news dates removed 72 trades with combined raw net `-17104`, and moved the fixed health-gated 2026 hard holdout from `-6848` to `152`.

This suggests scheduled-news/day-risk interaction may matter, but the current local calendar cannot justify implementation in the live bot. The next research step is to build a complete 2026 official scheduled-event calendar, then rerun the same hard-holdout test.
