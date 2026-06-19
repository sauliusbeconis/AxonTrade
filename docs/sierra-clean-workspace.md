# Sierra Clean Workspace

This document defines the AxonTrade clean Sierra Chart workspace blueprint.
It is a manual workspace design, not an importable chartbook and not a
copy of any paid or proprietary Sierra Chart suite.

## Visual Reference

The desired visual direction is similar in spirit to professional Sierra Chart
order-flow workspaces that combine TPO, footprint, DOM, and heatmap views in a
dark, compact trading layout. Use the public BoostYourCharts order-flow suite
page only as a high-level visual reference. Do not copy proprietary chartbooks,
settings, files, thresholds, templates, or paid design details.

Target visual traits:

- Dark neutral background with very low decorative noise.
- White or light gray price bars and TPO text for baseline readability.
- Cyan/blue for positive participation and bid-side emphasis.
- Magenta/red for negative participation and ask-side emphasis.
- Gray volume profiles with blue/red delta accents.
- Amber/yellow reference lines for key levels and session separators.
- Sparse high-contrast labels only where they help trading decisions.
- DOM docked next to the execution chart when screen space allows.
- Footprint calculated values and delta bars along the bottom of the trigger
  chart.
- Heatmap liquidity bands visible but subdued enough that price remains readable.

## Purpose

The workspace should provide a low-noise order-flow environment for:

- ES and MES first;
- NQ and MNQ later with the same layout;
- discretionary order-flow reading;
- future AxonTrade signal visualization;
- future research feature logging;
- simulation-safe execution practice;
- repeatable rebuilds after Sierra Chart, Wine, or OS reinstall.

Live order routing is out of scope. The default operating assumption is
simulation mode only.

Exact click-by-click Sierra Chart instructions are in
`docs/sierra-chart-exact-build-guide.md`.

## Chartbook Names

Use separate chartbooks per instrument family:

- `AxonTrade_ES_Orderflow.cht`
- `AxonTrade_MES_Orderflow.cht`
- `AxonTrade_NQ_Orderflow.cht`
- `AxonTrade_MNQ_Orderflow.cht`

Build ES first, duplicate the chartbook, then adapt symbol, tick value,
session settings, and scale for MES. Repeat the same pattern for NQ/MNQ only
after the ES/MES workflow is stable.

## Layout

Use five purpose-built charts instead of one overloaded chart. The primary
screen can still read visually like a three-part workflow: market map, liquidity
map, and trigger chart with integrated DOM.

Recommended first-screen arrangement:

- Left side top: TPO Context.
- Left side bottom: Liquidity Heatmap.
- Right side large: Footprint Execution.
- Far right docked or adjacent: DOM / Execution.
- Secondary tab, smaller window, or second monitor: Simple Context / VWAP Levels.

### Chart 1: TPO Context

Purpose: define auction context, value, balance, and imbalance.

Recommended content:

- RTH-focused TPO profile.
- 15-minute TPO letters or blocks when readable.
- Volume by Price profile.
- Current and prior session POC, VAH, and VAL.
- Prior session high and low.
- Optional overnight high and low.

Keep this chart context-first. Do not add signal clutter or execution tools.

### Chart 2: Footprint Execution

Purpose: entry timing, absorption proxy review, and imbalance review.

Recommended content:

- Sierra Chart Numbers Bars.
- Bar type is configurable: range, reversal, or point-and-figure.
- Bid x ask footprint or delta-focused footprint.
- Significant volume and delta highlighting.
- Bar delta and calculated values at bottom.
- Optional volume profile or delta profile if performance stays acceptable.

This is the main future target for AxonTrade signal lines and candidate signal
logging, but it must remain indicator-only during the current phase.

### Chart 3: DOM / Execution

Purpose: order-entry practice, execution visualization, and later simulation
assistant review.

Recommended content:

- Clean Trade DOM or Chart DOM.
- Simulation mode by default.
- No live account assumptions.
- Only the columns needed for reading and practice.

Do not use this workspace to enable live automated trading.

### Chart 4: Liquidity Heatmap

Purpose: observe resting liquidity and liquidity pull/stack context.

Recommended content:

- Market Depth Historical Graph.
- Separate RTH and overnight variants only if performance allows.
- Market depth recording enabled for the symbol before expecting historical
  depth to appear.

Treat heatmap information as context, not a standalone signal.

### Chart 5: Simple Context / VWAP Levels

Purpose: keep clean level context visible without footprint noise.

Recommended content:

- Simple candles or bars.
- VWAP.
- Opening range high and low.
- Overnight high and low.
- Prior day high and low.
- Prior VAH, VAL, and POC.

This chart is the future target for AxonTrade level overlays.

## Session Assumptions

Document and verify all times inside Sierra Chart before trading or testing.

- Time zone: `America/New_York`.
- RTH context: regular US index futures day session.
- ETH context: overnight session used for overnight high and low references.
- Disable new entries after: `16:35 America/New_York`.
- Internal forced flatten target: `16:40 America/New_York`.
- Firm flat time reference: `16:45 America/New_York`.

These times are research assumptions from the project configuration. Verify the
current official firm rules before any funded or live decision.

## Future AxonTrade Attachment Points

- Footprint Execution: signal lines, signal labels, candidate signal logger,
  rejected signal logger.
- Simple Context / VWAP Levels: session levels, prior value references, and
  strategy context overlays.
- TPO Context: market profile references for research annotation.
- DOM / Execution: simulation-only assistant review after a future safety gate.
- Liquidity Heatmap: replay verification and market-depth context logging.

No ACSIL execution logic is part of this workspace blueprint.
