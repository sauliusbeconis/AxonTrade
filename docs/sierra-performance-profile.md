# Sierra Performance Profile

This profile keeps the AxonTrade Sierra Chart workspace responsive while still
supporting order-flow reading.

## Principles

- Separate heavy charts from execution charts.
- Do not render full-depth market data on every chart.
- Keep the footprint chart readable before adding more studies.
- Limit loaded days on heavy charts.
- Increase chart complexity only after confirming replay and live data remain
  responsive.

## Recommended Starting Point

- TPO Context: enough days for current and recent prior-session references.
- Footprint Execution: minimal loaded days needed for the active session and
  replay task.
- DOM / Execution: simulation mode, clean columns, no extra studies.
- Liquidity Heatmap: shorter history first, expand only when performance allows.
- Simple Context / VWAP Levels: moderate history, simple studies only.

## User-Tunable Settings

- Chart update interval.
- Number of loaded days.
- Market-depth history length.
- Heatmap levels displayed.
- Numbers Bars calculated values.
- Volume profile and delta profile visibility.

If Sierra Chart becomes sluggish, reduce heatmap history first, then reduce
loaded days on the footprint chart, then disable nonessential studies.

## Market Depth Notes

Market Depth Historical Graph requires market depth recording for the symbol.
If the heatmap is blank, verify:

- data service supports market depth;
- market depth recording is enabled;
- symbol mapping is correct;
- enough depth data has been recorded after enabling the setting.

## Rebuild Rule

After every major Sierra Chart, Wine, GPU, data-service, or OS change, reopen
the chartbook and confirm:

- footprint updates normally;
- heatmap renders without freezing;
- DOM remains responsive;
- replay mode remains usable;
- no duplicate logging or drawing behavior appears from AxonTrade studies.

