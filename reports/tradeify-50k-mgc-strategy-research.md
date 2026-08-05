# Tradeify 50K MGC Strategy Research

Status: strategy-only validation for a future NinjaTrader implementation. No NinjaTrader or live-routing code is included.

## Instrument Decision

`MGC` is the primary instrument for this account profile. Its frozen strategy has more trades and materially lower path risk than the available MNQ candidates, while one-contract sizing keeps the initial stop near $154 including base friction.

## Frozen Strategy

- strategy: `mgc_lb_be_sensitivity:lb10:buf0:cl0.45:end1030:mtf:delta125:breakeven:t25:s15:trig20`;
- entry: 10-bar breakout, directional close-location >= 0.45, entries through 10:30, Monday/Tuesday/Friday only, absolute entry-bar delta <= 125;
- management: 25-point target, 15-point initial stop, stop to breakeven after +20 points, one trade per session, 16:30 ET flatten;
- source: `813388` one-minute MGC bars, `2024-03-18` through `2026-07-03`;
- raw setups: `2431`; sequenced trades: `343` (`2.87` per week);
- chronological split: `296 / 148 / 149` active dates;
- base friction: Tradeify `$2.12` round trip plus two total slippage ticks per MGC; stress uses six slippage ticks;
- same-bar ambiguity: stop first.

## Strategy Results

| Sample | Trades | Net | PF | Win | DD | Avg/Trade |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Full base | 343 | 12570.84 | 1.70827699 | 55.1% | -696.08 | 36.6496793 |
| Full stress | 343 | 11198.84 | 1.60958276 | 53.1% | -732.08 | 32.6496793 |
| Final holdout base | 86 | 6643.68 | 2.4728777 | 54.7% | -678.84 | 77.25209302 |
| Final holdout stress | 86 | 6299.68 | 2.34992757 | 54.7% | -706.84 | 73.25209302 |

Fixed `1 MGC` shuffled stress drawdown: median `$-1264.74`, P95 `$-2008.88`, P99 `$-2481.28`.

## Evaluation Sizing

Sizing was selected on the first 75% of dates. The final 25% was used only for the final bootstrap gate. `Risk lock` means the remaining drawdown cushion cannot support even one MGC plus the $100 reserve; the strategy stops rather than breaching the account.

| Policy | Dev 180 Pass/Fail/Lock | Dev 365 Pass/Fail/Lock | Dev MC Pass/Fail/Lock | Holdout MC Pass/Fail/Lock | Full 365 Pass | Funded Lock |
| --- | --- | --- | --- | --- | ---: | ---: |
| `fixed_1_mgc` **selected** | 14.2% / 0.0% / 0.0% | 85.5% / 0.0% / 0.0% | 59.3% / 0.0% / 6.7% | 99.0% / 0.0% / 1.0% | 91.9% | 100.0% |
| `fixed_3_mgc` | 83.5% / 0.0% / 15.8% | 89.2% / 0.0% / 10.8% | 49.2% / 0.0% / 50.8% | 78.2% / 0.0% / 21.8% | 83.0% | 86.6% |
| `fixed_2_mgc` | 74.1% / 0.0% / 0.0% | 100.0% / 0.0% / 0.0% | 63.8% / 0.0% / 36.0% | 88.4% / 0.0% / 11.6% | 100.0% | 100.0% |
| `adaptive_2_to_1_dd1000` | 61.7% / 0.0% / 0.0% | 98.4% / 0.0% / 0.0% | 67.8% / 0.0% / 28.7% | 94.6% / 0.0% / 5.4% | 99.1% | 99.4% |
| `adaptive_3_2_1_dd500_1000` | 51.3% / 0.0% / 0.0% | 86.0% / 0.0% / 0.0% | 60.7% / 0.0% / 36.4% | 92.0% / 0.0% / 8.0% | 92.2% | 93.4% |
| `adaptive_3_2_1_dd250_1000` | 46.2% / 0.0% / 0.0% | 86.6% / 0.0% / 0.0% | 63.3% / 0.0% / 32.9% | 94.7% / 0.0% / 5.3% | 92.5% | 94.9% |
| `adaptive_2_to_1_dd500` | 43.7% / 0.0% / 0.0% | 93.0% / 0.0% / 0.0% | 66.9% / 0.0% / 16.3% | 97.8% / 0.0% / 2.2% | 96.1% | 98.8% |
| `adaptive_3_2_1_dd250_750` | 43.7% / 0.0% / 0.0% | 86.0% / 0.0% / 0.0% | 63.8% / 0.0% / 25.8% | 96.3% / 0.0% / 3.7% | 92.2% | 94.6% |
| `adaptive_2_to_1_dd750` | 42.7% / 0.0% / 0.0% | 90.9% / 0.0% / 0.0% | 68.2% / 0.0% / 22.2% | 96.6% / 0.0% / 3.4% | 94.9% | 100.0% |
| `adaptive_2_to_1_dd250` | 21.5% / 0.0% / 0.0% | 83.9% / 0.0% / 0.0% | 63.2% / 0.0% / 11.8% | 98.7% / 0.0% / 1.3% | 91.0% | 96.4% |

## Decision

Selected policy: `fixed_1_mgc`.

- historical rolling 365-day evaluation pass: `91.9%`; fail `0.0%`; risk-lock `0.0%`;
- median successful evaluation: `236` calendar days and `99.5` trade days;
- final-holdout block bootstrap: pass `99.0%`; fail `0.0%`; risk-lock `1.0%`;
- verdict: `NON_REJECTED_STRATEGY_CANDIDATE`.

This clears the offline strategy gate, not the live-trading gate. The future NinjaTrader version must reproduce these fills, use account-aware sizing, reject entries when the risk reserve cannot fit, and flatten before Tradeify's cutoff.

## Research Limits

- The export is Sierra-derived historical data, not NinjaTrader historical or Market Replay data.
- Commission and slippage are modeled, but queue position, partial fills, disconnections, and adverse gaps beyond the bar stop are not.
- Bootstrap results measure sensitivity to sampled historical regimes; they are not probabilities guaranteed for a future evaluation.
- The strategy must remain disabled for live routing until NinjaTrader parity, replay, simulation, and controlled staging pass.
