# Workspace Screenshots Checklist

Capture these screenshots after manually building the chartbook. Store them
outside Git if they contain account, broker, or personal details.

## Required Screenshots

- Full workspace layout.
- Full workspace layout with TPO top-left, heatmap bottom-left, footprint large
  right, and DOM docked beside footprint where practical.
- TPO Context chart.
- Footprint Execution chart.
- DOM / Execution view.
- Liquidity Heatmap chart.
- Simple Context / VWAP Levels chart.
- Study settings for TPO Context.
- Study settings for Footprint Execution.
- Study settings for Liquidity Heatmap.
- Study settings for Context / VWAP Levels.
- Chart session settings.
- Symbol settings.
- Market depth recording setting.
- Simulation mode confirmation.

## Visual Acceptance Checks

- Dark theme is consistent across charts.
- Footprint and DOM form the obvious trigger area.
- TPO and heatmap read as context, not as execution panels.
- Cyan/blue and magenta/red accents are visible but not overwhelming.
- Amber/yellow reference levels are easy to spot.
- Text and scales remain readable after resizing.

## Review Notes

After screenshots are captured:

- redact account numbers and personal data;
- compare each chart to the matching manifest under `config/sierra`;
- record local deviations in `docs/decision-log.md`;
- update the manifests only when the deviation should become the project default.
