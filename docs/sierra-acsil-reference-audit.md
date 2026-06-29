# Sierra ACSIL Reference Audit

Source retrieval date: `2026-06-29`.

Manual help needed: **No**.

This file records the official Sierra Chart documentation links that govern the
current AxonTrade ACSIL studies in `src/acsil`.

## Core ACSIL References

| Topic | Official source | AxonTrade use |
| --- | --- | --- |
| ACSIL overview and custom-study lifecycle | https://www.sierrachart.com/index.php?page=doc/AdvancedCustomStudyInterfaceAndLanguage.php | Defines the `#include "sierrachart.h"`, `SCDLLName(...)`, `SCSFExport`, `sc.SetDefaults`, build, and load workflow used by all local studies. |
| Build from source | https://www.sierrachart.com/index.php?page=doc/HowToBuildAnAdvancedCustomStudyFromSourceCode.html | Confirms `Analysis >> Build Custom Studies DLL`, `File >> Select Files`, and `Build >> Remote Build` are valid build paths. |
| Developing custom studies and systems | https://www.sierrachart.com/index.php?page=doc/DevelopingCustomStudiesAndSystems.php | Confirms ACSIL supports drawing styles, custom bars, and chart drawing tools from C++. |
| ACSIL programming concepts | https://www.sierrachart.com/index.php?page=doc/ACSILProgrammingConcepts.html | Provides implementation concepts, including accessing volume-at-price data per bar and avoiding processing during historical downloading/full recalculation where needed. |
| Interface variables and arrays | https://www.sierrachart.com/index.php?page=doc/ACSIL_Members_Variables_And_Arrays.html | Defines base arrays such as `SC_BIDVOL`, `SC_ASKVOL`, `sc.BaseDateTimeIn[]`, `sc.MaintainVolumeAtPriceData`, and `sc.VolumeAtPriceForBars`. |
| Interface functions | https://www.sierrachart.com/index.php?page=doc/ACSIL_Members_Functions.html | Defines helper functions including VAP-related functions such as `sc.GetPointOfControlPriceVolumeForBar()` and `sc.GetVolumeAtPriceForBarsForChart()`. |
| Drawing tools | https://www.sierrachart.com/index.php?page=doc/ACSILDrawingTools.html | Defines `sc.UseTool`, `s_UseTool::LineNumber`, and `UTAM_ADD_OR_ADJUST`, which we use for recalculation-safe drawings. |

## Volume At Price References

| Topic | Official source | AxonTrade implication |
| --- | --- | --- |
| Accessing Volume at Price Data Per Bar | https://www.sierrachart.com/index.php?page=doc/ACSILProgrammingConcepts.html#AccessingVolumeAtPriceDataPerBar | Sierra directs custom studies to use ACSIL and `sc.VolumeAtPriceForBars` for per-bar volume-at-price data. |
| `sc.MaintainVolumeAtPriceData` | https://www.sierrachart.com/index.php?page=doc/ACSIL_Members_Variables_And_Arrays.html#scMaintainVolumeAtPriceData | VAP logger studies must set `sc.MaintainVolumeAtPriceData = 1` inside `sc.SetDefaults`. |
| `sc.VolumeAtPriceForBars` | https://www.sierrachart.com/index.php?page=doc/ACSIL_Members_Variables_And_Arrays.html#scVolumeAtPriceForBars | This is a `c_VAPContainer` pointer containing per-price tick volume data for loaded bars. |
| `GetSizeAtBarIndex` / `GetVAPElementAtIndex` | https://www.sierrachart.com/index.php?page=doc/ACSIL_Members_Variables_And_Arrays.html#scVolumeAtPriceForBars | Use indexed access over each bar's VAP container rather than deprecated next-higher/next-lower traversal. |
| `PriceInTicks` convention | https://www.sierrachart.com/index.php?page=doc/ACSIL_Members_Variables_And_Arrays.html#scVolumeAtPriceForBars | Convert price to ticks with `price / sc.TickSize` when using price-specific VAP lookups. |
| `sc.GetPointOfControlPriceVolumeForBar()` | https://www.sierrachart.com/index.php?page=doc/ACSIL_Members_Functions.html#scGetPointOfControlPriceVolumeForBar | Available if we later need bar-level POC from maintained VAP data. |
| `sc.GetVolumeAtPriceForBarsForChart()` | https://www.sierrachart.com/index.php?page=doc/ACSIL_Members_Functions.html#scGetVolumeAtPriceForBarsForChart | Available if a study needs VAP data from another chart by chart number. |

## Implementation Rules

- Keep all Phase 0 ACSIL studies indicator-only: draw objects and write CSV
  research logs only.
- For VAP exports, set `sc.MaintainVolumeAtPriceData = 1` in the `sc.SetDefaults`
  block before reading `sc.VolumeAtPriceForBars`.
- Iterate VAP data with `GetSizeAtBarIndex()` and `GetVAPElementAtIndex()`.
- Use chart tick size when converting between display prices and `PriceInTicks`.
- Use deterministic drawing identifiers for AxonTrade-owned drawings, and call
  `sc.UseTool()` with `UTAM_ADD_OR_ADJUST` when drawings should update instead
  of duplicating across recalculations.
- Build under Sierra with `Analysis >> Build Custom Studies DLL` and
  `Build >> Remote Build` unless there is a specific local Visual C++ reason.
