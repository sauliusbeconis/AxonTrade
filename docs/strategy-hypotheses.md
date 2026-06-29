# Strategy Hypotheses

These are research hypotheses only. No strategy is assumed profitable.

## A. Contextual Momentum Reclaim / Pullback

Thesis: after price reclaims a meaningful reference level, a controlled pullback may offer continuation if context supports directional participation.

Reference levels:

- opening range high and low;
- overnight high and low;
- prior value area high and low;
- VWAP.

Initial rules to define before testing:

- reclaim condition;
- pullback depth;
- continuation trigger;
- invalidation level;
- excluded market states;
- optional order-flow confirmation.

## B. Liquidity Sweep / Absorption Reversal

Thesis: during mid-day RTH, ES/NQ breakouts beyond an established intraday
range often fail unless larger participants are motivated to continue the
auction. When price sweeps liquidity beyond a range edge and closes back inside
despite aggressive activity, the breakout may be a trap and the higher-quality
trade may be a fade back toward value.

Initial components:

- test or sweep of opening range, prior high/low, value area, or overnight
  level;
- close back inside the swept level;
- mid-day time filter that excludes the open and close;
- aggressive volume into the level;
- absorption or failed continuation after the sweep;
- optional stacked imbalance confirmation;
- strict invalidation.

Current first implementation:

- `config/research/price_only_liquidity_sweep_reversal.yaml`
- `scripts/run_price_only_liquidity_sweep.py`
- `docs/price-only-liquidity-sweep.md`

This implementation is price-only. It is the control sample for later
footprint/volume-at-price absorption filters.

First order-flow layer:

- `config/research/liquidity_sweep_absorption_reversal.yaml`
- `config/research/sierra_orderflow_bar_export.yaml`
- `scripts/run_liquidity_sweep_absorption.py`
- `docs/liquidity-sweep-absorption.md`

This layer requires bid/ask volume export fields from Sierra Chart.

## C. Price-Only Baseline

Thesis: a transparent control strategy is needed before evaluating order-flow complexity.

The baseline uses no footprint features. It may use price, time, opening range, overnight levels, prior value area levels, and VWAP if those references are explicitly defined.

## D. Order-Flow Feature Ablation

Thesis: order-flow features are only useful if they improve the baseline after costs and without increasing fragility.

Required comparisons:

- baseline versus baseline plus volume-profile context;
- baseline versus baseline plus stacked imbalances;
- baseline versus baseline plus absorption proxy;
- full model versus simpler versions.

Source context:

- Market-research summary:
  [market-research-momentum-order-flow.md](market-research-momentum-order-flow.md)
- Broad time-series momentum evidence supports regime context, not direct
  proof of intraday ES/NQ edge.
- Intraday momentum evidence supports explicit session/time-of-day controls.
- Order-flow imbalance literature supports delta/VAP/depth features as
  ablated inputs, not standalone signals.

## Required Output

Each tested hypothesis must produce a report with instrument-specific results, rejected signals, costs, slippage, parameter log, and failure-mode review.
