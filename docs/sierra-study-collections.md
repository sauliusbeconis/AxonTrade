# Sierra Study Collections

Sierra Chart study collections should be created manually after each chart is
configured and verified. The YAML files under `config/sierra/study_collections`
are human-readable manifests only.

## Intended Study Collections

- `Axon_TPO_Context`
- `Axon_Footprint_Execution`
- `Axon_Liquidity_Heatmap`
- `Axon_Context_Levels`
- `Axon_DOM_Execution`

## Manual Creation Pattern

1. Configure the chart manually in Sierra Chart.
2. Confirm the chart is readable and uses the intended session.
3. Remove studies that do not serve the chart purpose.
4. Save the study collection with the Axon name.
5. Reapply the study collection to a duplicate chart.
6. Confirm the duplicate chart matches the intended behavior.
7. Record deviations in `docs/decision-log.md`.

## Shared Visual Style

Use a consistent dark theme across all collections:

- matte black or charcoal chart background;
- light gray text and axes;
- cyan/blue positive-side accents;
- magenta/red negative-side accents;
- gray volume profile base;
- amber/yellow reference levels and session dividers;
- minimal labels and no decorative elements.

## Collection Notes

### Axon_TPO_Context

Use for the TPO / market profile context chart. Keep profile settings readable
and focused on auction context.

### Axon_Footprint_Execution

Use for the Numbers Bars execution chart. Keep highlighting strict enough to
surface meaningful activity without turning every price level into a signal.

### Axon_Liquidity_Heatmap

Use for the Market Depth Historical Graph chart. Keep this separate from the
execution footprint chart so market-depth rendering does not slow the primary
execution view.

### Axon_Context_Levels

Use for simple candles or bars plus VWAP and reference levels. This chart should
remain clean enough to quickly answer where price is relative to value, prior
range, overnight range, and opening range.

### Axon_DOM_Execution

Use for DOM layout notes and manual DOM configuration. Sierra Chart DOM settings
may not map to study collections in the same way as chart studies, so treat the
manifest as a rebuild checklist when needed.
