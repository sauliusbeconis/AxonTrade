# Sierra Chartbook Build Checklist

Use this checklist to manually build the clean AxonTrade workspace inside
Sierra Chart.

For exact menu paths and first-build settings, use
`docs/sierra-chart-exact-build-guide.md`.

## Build Steps

1. Open Sierra Chart.
2. Confirm the data/trade service is correct.
3. Confirm the ES and MES symbol mapping for the selected data service.
4. Confirm Sierra Chart time zone and chart session settings.
5. Confirm simulation mode is enabled.
6. Create a new chartbook named `AxonTrade_ES_Orderflow.cht`.
7. Create the ES base chart.
8. Configure Chart 1 as TPO Context.
9. Save Chart 1 as study collection `Axon_TPO_Context`.
10. Duplicate or create Chart 2 as Footprint Execution.
11. Configure Numbers Bars, bar type, delta display, and calculated values.
12. Save Chart 2 as study collection `Axon_Footprint_Execution`.
13. Create Chart 3 as Trade DOM or Chart DOM.
14. Confirm DOM is simulation-only.
15. Save DOM configuration as `Axon_DOM_Execution` where Sierra Chart supports it.
16. Create Chart 4 as Liquidity Heatmap.
17. Enable market depth recording for the symbol if required.
18. Save Chart 4 as study collection `Axon_Liquidity_Heatmap`.
19. Create Chart 5 as Simple Context / VWAP Levels.
20. Configure VWAP, opening range, overnight high and low, prior day high and low,
    and prior VAH, VAL, and POC.
21. Save Chart 5 as study collection `Axon_Context_Levels`.
22. Arrange windows so the workspace visually reads as market map, liquidity
    map, and trigger chart with DOM.
23. Place TPO Context on the left top area.
24. Place Liquidity Heatmap on the left bottom area.
25. Place Footprint Execution as the largest right-side chart.
26. Dock or place DOM beside the Footprint Execution chart.
27. Keep Simple Context / VWAP Levels in a secondary tab, smaller window, or
    second monitor if screen space is tight.
28. Save the chartbook.
29. Close and reopen Sierra Chart to confirm the chartbook restores cleanly.
30. Duplicate the ES chartbook as `AxonTrade_MES_Orderflow.cht`.
31. Update symbols, tick values, scales, and any MES-specific settings.
32. After ES/MES are stable, duplicate the structure for
    `AxonTrade_NQ_Orderflow.cht` and `AxonTrade_MNQ_Orderflow.cht`.
33. Take screenshots listed in `docs/workspace-screenshots-checklist.md`.
34. Record any deviations or local Sierra Chart quirks in `docs/decision-log.md`.

## Manual Verification

- No live order routing is enabled.
- Simulation mode is visible and confirmed.
- TPO profiles show the expected session.
- POC, VAH, and VAL are visible and not duplicated incorrectly.
- Footprint bars update without excessive lag.
- DOM is readable and does not hide risk-critical columns.
- Heatmap renders only after market depth recording is configured.
- VWAP and session levels match the intended session template.
- Chartbook reopens without missing studies.
- Dark visual theme is consistent across all charts.
- Important blue/red/magenta/amber accents are readable without dominating the
  screen.
