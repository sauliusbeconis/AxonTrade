# Sierra Chart Exact Build Guide

This guide is the click-by-click build plan for the first AxonTrade chartbook:

`AxonTrade_ES_Orderflow.cht`

Build ES first. After it is stable, duplicate it for MES, then later NQ/MNQ.
Use simulation mode only.

This chartbook is a bot-development harness, not the final product. For the bot
pipeline, the minimum useful setup is the correct ES/MES futures symbol,
simulation mode, VWAP/session levels, and a chart where AxonTrade can later draw
and log signals. TPO, footprint, DOM, and heatmap are optional review tools.

## Default Rules

Use these defaults unless the data service or Sierra Chart symbol settings force
a different value.

| Area | Default |
| --- | --- |
| Time zone | `America/New_York` |
| RTH session | `09:30:00` to `16:14:59` |
| ETH session | `18:00:00` to `09:29:59` |
| New entries disabled | `16:35 America/New_York` |
| Internal flat target | `16:40 America/New_York` |
| Firm flat reference | `16:45 America/New_York` |
| First chartbook | `AxonTrade_ES_Orderflow.cht` |
| Trading mode | Simulation only |
| Visual theme | Dark, compact, blue/red/gray/amber accents |

If a chart has an option named `Use Evening Session`, use:

- RTH-only charts: `Use Evening Session = No`.
- ETH-aware charts: `Use Evening Session = Yes`, with evening times
  `18:00:00` to `09:29:59`.

## Before Building

1. Open Sierra Chart.
2. Click `Trade >> Trade Simulation Mode On`.
3. Confirm the menu item is checked.
4. Confirm `[Sim]` appears in the Sierra Chart title bar.
5. Click `Global Settings >> Data/Trade Service Settings`.
6. Confirm the selected service is the one you intend to use for market data.
7. Click `OK` or `Cancel`.

Do not continue if simulation mode is not visibly enabled.

## Build AxonTrade ACSIL Study

Manual help is required for this step because Sierra Chart must compile and load
the study from inside its own UI.

Use Sierra Chart's remote build under Wine. Do not use the local Visual C++
build path unless Visual C++ is installed and working inside the Wine prefix.

1. In Sierra Chart, click `Analysis >> Build Custom Studies DLL`.
2. In the `Build Advanced Custom Studies DLL` window, click
   `File >> Select Files`.
3. Select `OrderFlowSignalSmokeTest.cpp`.
4. Click `Open`.
5. In the same build window, click `Build >> Remote Build`.
6. Wait for the output to say the remote build succeeded.
7. If the build succeeds, close the build window or leave it open.
8. Click the ES/MES chart where the study should be loaded.
9. Click `Analysis >> Studies`.
10. Click `Add Custom Study`.
11. Expand `AxonTrade Simulation Safe Studies`.
12. Select `Order Flow Signal Smoke Test`.
13. Click `Add`.
14. Select the added study in `Studies to Graph`.
15. Click `Settings`.
16. Set `Horizontal Line Price` near the current futures price.
17. Confirm `Event Type = candidate_signal`.
18. Confirm `Direction = long` or `short`.
19. Confirm `Trade Mode = sim` or `replay`.
20. Click `OK`.
21. Click `OK`.

If you see this error:

`Can't recognize 'cl ...' as an internal or external command`

you clicked the local Visual C++ build path. Go back to the build window and use
`Build >> Remote Build`.

If the study was already loaded and Sierra refuses to overwrite the DLL:

1. Click `Analysis >> Build Custom Studies DLL`.
2. Click `Build >> Release All DLLs and Deny Load`.
3. Click `Build >> Remote Build`.
4. After the build succeeds, click `Build >> Allow Load DLLs`.
5. Return to the chart and reload/recalculate the study.

## Linux / Wine File Compression Fix

On Pop!_OS/Wine, Sierra Chart may log an error like:

`File compression not supported on file system. C:\SierraChart\Data\SPX500.scid. Windows error code 50: Request not supported.`

This means Sierra Chart tried to enable Windows/NTFS-style compression on an
Intraday data file, but the Wine-backed Linux filesystem does not support that
Windows compression API.

Fix it before downloading a lot of data:

1. In Sierra Chart, click `Global Settings >> Advanced Service Settings`.
2. Open the `File Compression` or `Other` section.
3. Set `Support Intraday and Market Depth Files Compression` to `No`.
4. Keep `Disable Intraday and Market Depth File Compression if Enabled on the File`
   set to `No`.
5. Click `OK`.
6. Click `File >> Disconnect`.
7. Click `File >> Connect to Data Feed`.
8. Reopen or reload the chart that produced the message.

Expected result: the message should stop appearing for `.scid` and market-depth
data files. The tradeoff is higher disk usage because Sierra Chart will store
those files uncompressed.

Do not delete `.scid` files just to fix this message. Only delete and redownload
a symbol data file if the chart itself remains broken after compression support
is disabled.

## Create The Chartbook

1. Click `File >> New Chartbook`.
2. Click `File >> Save As`.
3. Name it `AxonTrade_ES_Orderflow.cht`.
4. Save it in Sierra Chart's Data folder.

If `File >> New Chartbook` is not visible in your version, use
`File >> Open Chartbook` for existing chartbooks and save the new workspace with
`File >> Save As` once a clean chartbook is active.

## Create The Base ES Chart

1. Click `File >> Find Symbol`.
2. Find the ES futures symbol for your connected data service.
3. Select the current ES contract.
4. Click `Open Intraday Chart`.
5. Click the chart window to make it active.
6. Click `Chart >> Chart Settings`.
7. In the symbol/settings area, press `Apply Global Symbol Settings` if present.
8. Confirm `Tick Size = 0.25`.
9. Confirm the price display format is correct for ES.
10. Set `Days to Load` to `5` for the first build.
11. Click `OK`.

If the chart is blank, first confirm the symbol and data service. Do not start
adding studies until a plain ES intraday chart is updating or loaded.

## Chart 1: TPO Context

Goal: RTH market map in the top-left workspace area.

### Create Chart

1. Use the base ES chart or duplicate it.
2. Click `Chart >> Duplicate Chart` if you are duplicating.
3. Click the chart to make it active.
4. Click `Chart >> Chart Settings`.
5. Open the `Session Times` section.
6. Set `Start Time = 09:30:00`.
7. Set `End Time = 16:14:59`.
8. Set `Use Evening Session = No`.
9. Set `Days to Load = 10`.
10. Click `OK`.

### Add Studies

1. Click `Analysis >> Studies`.
2. In `Studies Available`, select `TPO Profile Chart`.
3. Click `Add >>`.
4. Select `TPO Profile Chart` in `Studies to Graph`.
5. Click `Settings`.
6. In `Settings and Inputs`, set:
   - letter/block time period: `15 minutes`;
   - value area display: enabled;
   - POC display: enabled;
   - profile period: daily/session.
7. Click `OK`.
8. In `Studies Available`, select `Volume by Price`.
9. Click `Add >>`.
10. Select `Volume by Price` in `Studies to Graph`.
11. Click `Settings`.
12. Configure it as a session-aligned profile with POC and value area visible.
13. Click `OK`.
14. Click `OK` to close Chart Studies.

### Save Study Collection

1. Click `Analysis >> Studies`.
2. In `Save Studies As Study Collection >> Name`, type
   `Axon_TPO_Context`.
3. Click `Save All`.
4. Confirm the name if Sierra Chart asks.
5. Click `OK`.

## Chart 2: Footprint Execution

Goal: largest right-side trigger chart.

### Create Chart

1. Click the plain/base ES chart.
2. Click `Chart >> Duplicate Chart`.
3. Click the duplicated chart.
4. Click `Chart >> Chart Settings`.
5. Open `Session Times`.
6. Set `Start Time = 09:30:00`.
7. Set `End Time = 16:14:59`.
8. Set `Use Evening Session = No`.
9. Set `Days to Load = 3`.
10. Open the bar period section.
11. First build default: set range bars to `4 ticks` for ES/MES.
12. If range bars are too noisy, test `6 ticks`.
13. Click `OK`.

Point-and-Figure can be tested later. The first build should use range bars so
the workspace can be assembled and verified quickly.

### Add Studies

1. Click `Analysis >> Studies`.
2. Select `Numbers Bars`.
3. Click `Add >>`.
4. Select `Numbers Bars` in `Studies to Graph`.
5. Click `Settings`.
6. Configure:
   - display style: bid x ask or delta-focused;
   - significant volume highlighting: enabled;
   - delta highlighting: enabled;
   - text colors: light gray on dark background;
   - positive/dominant bid-side color: cyan/blue;
   - negative/dominant ask-side color: magenta/red.
7. Click `OK`.
8. Select `Numbers Bars Calculated Values`.
9. Click `Add >>`.
10. Select `Numbers Bars Calculated Values` in `Studies to Graph`.
11. Click `Settings`.
12. Keep bar delta, volume, and range-style values visible at the bottom.
13. Click `OK`.
14. Optional: add `Volume by Price` only if the chart remains readable.
15. Click `OK` to close Chart Studies.

### Save Study Collection

1. Click `Analysis >> Studies`.
2. In `Save Studies As Study Collection >> Name`, type
   `Axon_Footprint_Execution`.
3. Click `Save All`.
4. Confirm the name if Sierra Chart asks.
5. Click `OK`.

## Chart 3: DOM / Execution

Goal: docked or adjacent DOM next to the footprint chart.

1. Click `File >> Open Trade DOM`.
2. Select the same ES symbol used by the charts.
3. Click `Open Trading DOM`.
4. Confirm `Trade >> Trade Simulation Mode On` is still checked.
5. Confirm `[Sim]` is still visible.
6. Click the DOM window.
7. Click `Trade >> Open Trade Window For Chart`.
8. If the trade window is floating, click `Trade >> Attach Trade Window To Chart`.
9. To attach it to the right side, click `Chart >> Chart Settings >> Trading`.
10. Enable `Attach Trade Window to Right Side`.
11. Click `OK`.
12. Keep only the columns needed for simulation practice and reading:
    - price;
    - bid size;
    - ask size;
    - recent bid volume;
    - recent ask volume;
    - simulated position if useful.

Do not connect this chartbook to a live account workflow.

## Chart 4: Liquidity Heatmap

Goal: optional lower-left liquidity map.

Skip this section when the priority is bot development. Heatmap is useful for
discretionary review and later diagnostics, but the first signal engine and CSV
logger should not depend on it.

### Enable Market Depth Recording

1. Click `Global Settings >> Symbol Settings`.
2. Find the ES symbol or symbol pattern used by your data service.
3. Locate `Record Market Depth Data`.
4. Set it to `Yes` in the custom settings.
5. Enable `Use Custom Symbol Settings Values` if Sierra Chart shows that box.
6. Click `OK`.
7. Click `File >> Disconnect`.
8. Click `File >> Connect to Data Feed`.

### Create Heatmap Chart

1. Duplicate the base ES chart.
2. Click `Chart >> Chart Settings`.
3. Open `Session Times`.
4. Set `Start Time = 09:30:00`.
5. Set `End Time = 16:14:59`.
6. Set `Use Evening Session = Yes`.
7. Set `Evening Start Time = 18:00:00`.
8. Set `Evening End Time = 09:29:59`.
9. Set `Days to Load = 2`.
10. Click `OK`.

### Add Study

1. Click `Analysis >> Studies`.
2. Select `Market Depth Historical Graph`.
3. Click `Add >>`.
4. Select `Market Depth Historical Graph` in `Studies to Graph`.
5. Click `Settings`.
6. Start with conservative depth levels and moderate color intensity.
7. Use muted magenta/red liquidity bands on a dark background.
8. Click `OK`.
9. Click `OK` to close Chart Studies.

### Save Study Collection

1. Click `Analysis >> Studies`.
2. In `Save Studies As Study Collection >> Name`, type
   `Axon_Liquidity_Heatmap`.
3. Click `Save All`.
4. Confirm the name if Sierra Chart asks.
5. Click `OK`.

## Chart 5: Simple Context / VWAP Levels

Goal: clean secondary context chart.

### Create Chart

1. Duplicate the base ES chart.
2. Click `Chart >> Chart Settings`.
3. Open `Session Times`.
4. Set `Start Time = 09:30:00`.
5. Set `End Time = 16:14:59`.
6. Set `Use Evening Session = Yes`.
7. Set `Evening Start Time = 18:00:00`.
8. Set `Evening End Time = 09:29:59`.
9. Use a simple time bar first, such as `5 minutes`.
10. Set `Days to Load = 5`.
11. Click `OK`.

### Add Studies

1. Click `Analysis >> Studies`.
2. Add `Volume Weighted Average Price`.
3. Configure VWAP to reset by session/day.
4. Add `High/Low for Time Period`.
5. Configure one instance for opening range high/low.
6. Add another `High/Low for Time Period`.
7. Configure it for overnight high/low.
8. Add `Daily OHLC` for prior day high/low if needed.
9. Add prior value references manually at first, or use the TPO chart until an
   AxonTrade overlay exists.
10. Click `OK`.

### Save Study Collection

1. Click `Analysis >> Studies`.
2. In `Save Studies As Study Collection >> Name`, type
   `Axon_Context_Levels`.
3. Click `Save All`.
4. Confirm the name if Sierra Chart asks.
5. Click `OK`.

## Arrange The Workspace

1. Put `TPO Context` top-left.
2. If built, put `Liquidity Heatmap` bottom-left. Otherwise leave that space for
   notes, logs, or the AxonTrade signal chart.
3. Put `Footprint Execution` large on the right.
4. Put the DOM at the far right of the footprint chart.
5. Put `Simple Context / VWAP Levels` in a secondary tab, smaller window, or
   second monitor.
6. Click `File >> Save`.
7. Close Sierra Chart.
8. Reopen Sierra Chart.
9. Click `File >> Open Chartbook`.
10. Select `AxonTrade_ES_Orderflow.cht`.
11. Confirm all windows restore correctly.

## Verify Before Using

- `Trade >> Trade Simulation Mode On` is checked.
- `[Sim]` is visible in the title bar.
- TPO uses RTH only.
- Footprint uses RTH only.
- If heatmap is built, market depth recording is enabled.
- VWAP and levels use the intended session.
- No live order-routing study or ACSIL order function is attached.
- Chartbook saves and reopens cleanly.

## Duplicate For MES

1. Open `AxonTrade_ES_Orderflow.cht`.
2. Click `File >> Save As`.
3. Save as `AxonTrade_MES_Orderflow.cht`.
4. For each chart, click the chart, then `Chart >> Chart Settings`.
5. Change the symbol from ES to MES using your data service's current MES symbol.
6. Press `Apply Global Symbol Settings` if present.
7. Confirm `Tick Size = 0.25`.
8. Keep the same layout.
9. Click `File >> Save`.

Do not build NQ/MNQ until ES/MES are stable and screenshotted.

## Official References

- Sierra Chart chartbooks and adding charts/Trade DOMs:
  https://www.sierrachart.com/index.php?page=doc/Chartbooks.html
- Sierra Chart custom study build window:
  https://www.sierrachart.com/index.php?page=doc/AnalysisMenu.html#BuildAdvancedStudiesDLL
- Sierra Chart build from source guide:
  https://www.sierrachart.com/index.php?page=doc/HowToBuildAnAdvancedCustomStudyFromSourceCode.html
- Sierra Chart file compression settings:
  https://www.sierrachart.com/index.php?page=doc/AdvancedServiceSettings.php#FileCompression
- Sierra Chart trade simulation mode:
  https://www.sierrachart.com/index.php?page=doc/TradeSimulation.php
- Sierra Chart session times:
  https://www.sierrachart.com/index.php?page=doc/SessionTimes.php
- Sierra Chart study collections:
  https://www.sierrachart.com/index.php?page=doc/StudyCollections.html
- Sierra Chart TPO Profile Chart:
  https://www.sierrachart.com/index.php?page=doc/StudiesReference/TimePriceOpportunityCharts.html
- Sierra Chart Numbers Bars:
  https://www.sierrachart.com/index.php?page=doc/NumbersBars.php
- Sierra Chart Market Depth Historical Graph:
  https://www.sierrachart.com/index.php?ID=375&page=doc/StudiesReference.php
