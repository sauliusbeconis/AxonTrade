# Tradeify 50K MGC High-Win Management

Status: strategy-only management search around the frozen MGC entry. No NinjaTrader code is included.

## Method

- source bars: `813388`; frozen raw setups: `2431`;
- chronological active-date split: `296 / 148 / 149`;
- profiles: `204` across 8-25 point targets, 8-15 point stops, fixed or breakeven management;
- selection used only train and validation; final holdout was excluded;
- Tradeify fee plus two slippage ticks for selection, six ticks for final stress; same-bar stop first.

## Decision

No management profile combined at least 65% wins with PF >= 1.50 on both development periods.

Verdict: `REJECT_AFTER_DEVELOPMENT`.
