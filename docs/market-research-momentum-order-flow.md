# Market Research: Momentum And Order Flow

Source retrieval date: `2026-06-29`.

Manual help needed: **No**.

This note summarizes evidence relevant to AxonTrade's ES/NQ research. It does
not validate any current strategy. Each finding must still pass instrument-level
export validation, costs, slippage, and chronological walk-forward tests.

## Time-Series Momentum

Moskowitz, Ooi, and Pedersen document time-series momentum across `58` liquid
futures and forward contracts in equity index, currency, commodity, and bond
markets. Their result supports the broad idea that an instrument's own prior
return can carry predictive information across asset classes.

Important limitation: this evidence is mostly monthly and cross-asset. It does
not directly justify a `3 Min` ES/NQ bot. Kim, Tse, and Wald argue that much of
the original futures result is driven by volatility scaling rather than the raw
directional timing rule. For AxonTrade, long-horizon time-series momentum should
be treated as context or regime evidence, not as proof that intraday entries
have edge.

Bot implication:

- Track trend/regime context separately from entry triggers.
- Do not use broad futures momentum literature to justify tight intraday scalps.
- Test volatility-normalized versions against unscaled versions.

## Intraday Momentum

Gao, Han, Li, and Zhou find that the first half-hour market return, measured
from the prior close, predicts the last half-hour return in SPY data from
`1993` through `2013`. The effect is stronger on high-volatility days,
high-volume days, recession days, and major macro-news days. They also report
evidence across other actively traded ETFs.

This is closer to AxonTrade because it is intraday and equity-index related,
but the documented effect is not the same as a mid-day 3-minute entry rule.
It suggests that time-of-day, opening impulse, volume, volatility, and news
state should be explicit features rather than ignored controls.

Bot implication:

- Preserve `minutes_after_open`, first-30-minute direction, first-30-minute
  range, and relative activity features.
- Do not assume the same entry logic should work at the open, mid-day, and close.
- Treat macro-news days as a separate regime, not just rows to remove.

## Order-Flow Imbalance

Cont, Kukanov, and Stoikov show that short-interval price changes are strongly
related to order-flow imbalance at the best bid and ask, with price impact
linked to market depth. They also report that volume alone is less robust than
order-flow imbalance for explaining short-interval price changes.

The Federal Reserve's 2025 Treasury-market note reinforces the practical
microstructure point: one-sided order flow can amplify price moves when
liquidity is thin, and volume spikes alone are not enough to explain observed
price pressure.

This supports AxonTrade's use of Sierra bid/ask volume, delta, volume-at-price,
and depth/liquidity context. It does not mean raw delta is a standalone signal.

Bot implication:

- Keep order-flow features as explanatory inputs: delta, bid/ask imbalance,
  VAP zone aggression, and relative volume/trade count.
- Normalize order-flow measures by recent activity and volatility.
- Prefer tests that compare price-only baseline versus baseline plus order-flow
  features.
- Add liquidity/depth proxies before trusting one-sided flow in thin conditions.

## Practical Direction

The literature points away from random parameter search and toward a structured
research stack:

- session structure first;
- opening impulse and activity regime;
- price-only baseline;
- order-flow feature ablation;
- cost and slippage stress tests;
- walk-forward and untouched holdout validation.

Current AxonTrade work already follows much of this. The main remaining gap is
larger samples across more market regimes before promoting any setup from
diagnostic to candidate.

## Sources

- Moskowitz, Ooi, and Pedersen, "Time Series Momentum", SSRN:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2089463
- Moskowitz, Ooi, and Pedersen, "Time series momentum", Journal of Financial
  Economics entry:
  https://econpapers.repec.org/RePEc:eee:jfinec:v:104:y:2012:i:2:p:228-250
- Kim, Tse, and Wald, "Time series momentum and volatility scaling", Journal of
  Financial Markets entry:
  https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html
- Gao, Han, Li, and Zhou, "Market intraday momentum", Journal of Financial
  Economics entry:
  https://ideas.repec.org/a/eee/jfinec/v129y2018i2p394-414.html
- Cont, Kukanov, and Stoikov, "The Price Impact of Order Book Events", arXiv:
  https://arxiv.org/abs/1011.6402
- Dobrev, Liu, Kim, and Rodriguez, "Order Flow Imbalances and Amplification of
  Price Movements", Federal Reserve FEDS Notes:
  https://www.federalreserve.gov/econres/notes/feds-notes/order-flow-imbalances-and-amplification-of-price-movements-evidence-from-u-s-treasury-markets-20251103.html
