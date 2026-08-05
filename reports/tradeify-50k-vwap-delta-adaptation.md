# Tradeify 50K VWAP/Delta Adaptation

Status: Tradeify-specific strategy research using the strongest existing MNQ entry. No NinjaTrader code is included.

## Why This Seed

The fresh opening-drive, gap-fade, prior-session sweep, and VWAP trend-pullback families did not produce a production candidate. The frozen MNQ VWAP/delta exhaustion entry remains the only local signal with the requested high-win/high-PF shape, so this pass changes management and sizing without re-optimizing the entry.

## Scope

- source: `67300` MNQ three-minute bars, `2024-07-15` through `2026-07-02`;
- frozen raw entry signals: `186`;
- chronological periods: `253 / 127 / 127` dates;
- entry: 80-point VWAP extension, delta 400, close-location 0.4, no Friday, no 11:00 or 15:00 entries, 900-second raw spacing;
- management grid: `2-8 MNQ`, first target `20/25/30`, stop `60-140`, runner `40-120`, initial or break-even runner stop;
- Tradeify cost: `$1.82` round trip plus two total slippage ticks per MNQ;
- same-bar ambiguity: stop first; live sequencing blocks overlapping trades;
- profiles evaluated: `1050`; robust: `18`; account-eligible: `3`.

## Top Account Rows

| Rank | Split | T1 / Stop / Runner / Mode | Trades | /Wk | Net | PF | Win | DD | Period PFs | 90d Pass/Fail | 180d Pass/Fail |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 1 | `2+1` | `25 / 80 / 40 / initial` | 168 | 1.64016736 | 8631.72 | 1.68759798 | 76.8% | -1570.8 | `1.50140075 / 2.68957411 / 1.5019427` | 0.0% / 0.0% | 35.7% / 0.0% |
| 2 | `1+1` | `30 / 140 / 120 / initial` | 157 | 1.53277545 | 8348.02 | 1.61754206 | 67.5% | -1738.18 | `1.51408852 / 2.74271059 / 1.34343625` | 0.0% / 0.0% | 31.4% / 0.0% |
| 3 | `1+1` | `25 / 140 / 120 / initial` | 157 | 1.53277545 | 9182.02 | 1.7841232 | 66.2% | -1168.18 | `1.67938303 / 2.53687322 / 1.57790668` | 0.0% / 0.0% | 31.2% / 0.0% |

## Decision

Frozen strategy profile: `tradeify_vwap_delta:split2-1:t125:s80:runner40:initial`.

| Metric | Base | Six-tick stress | Later stress |
| --- | ---: | ---: | ---: |
| Trades | 168 | 168 | 50 |
| Net | 8631.72 | 7623.72 | 1829 |
| PF | 1.68759798 | 1.59600356 | 1.42401565 |
| Win rate | 76.8% | 76.2% | 76.0% |
| Drawdown | -1570.8 | -1600.8 | -1390.14 |

- 130-trading-day block Monte Carlo: `31.7%` pass, `8.2%` fail;
- shuffled trade-order DD: median `$-1801.56`, P95 `$-2845.48`, P99 `$-3494.86`;
- funded `$2100` drawdown-lock objective within 180 calendar days: `59.2%` pass, `0.0%` fail;
- verdict: `REJECT_AFTER_STRESS`.

The profile passed the coarse account screen but failed final stress. Do not implement it as the production bot.
