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

## B. Failed Auction / Absorption Proxy Reversal

Thesis: when price tests a prior level with aggressive activity but fails to continue, a reclaim away from the level may indicate failed auction behavior.

Initial components:

- test of prior level;
- aggressive volume into the level;
- failure to continue;
- reclaim away from the level;
- optional stacked imbalance confirmation;
- strict invalidation.

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

## Required Output

Each tested hypothesis must produce a report with instrument-specific results, rejected signals, costs, slippage, parameter log, and failure-mode review.
