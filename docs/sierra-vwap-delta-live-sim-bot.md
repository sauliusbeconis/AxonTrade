# Sierra VWAP Delta Live Sim Bot

`AxonTradeVwapDeltaLiveSimBot.cpp` is a simulation-only ACSIL study for forward
testing the current VWAP/delta exhaustion fade candidate on rolling Sierra Chart
data.

Manual help needed: **Yes, to compile and load the Sierra Chart study.**
Manual help needed after it is loaded: **No**, unless Sierra Chart reports a
build error, the chart is missing bid/ask volume data, or the log file is not
created.

The study does not place, modify, cancel, flatten, or route broker orders. It
draws and logs virtual two-contract paper trades only.

## What It Logs

Default output file:

`C:\SierraChart\Data\AxonTrade_VwapDeltaLiveSimBot.csv`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_VwapDeltaLiveSimBot.csv`

Rows use the live-sim bot fields:

- `paper_entry` when the fixed VWAP/delta rule, context guard, and health gate
  allow a virtual entry.
- `paper_leg1_exit` when the first virtual contract reaches the first target.
- `paper_exit` when the virtual trade is fully closed by stop, runner target,
  or session flatten.
- `rejected_signal` when a raw setup appears but is blocked by spacing, context,
  max-open, disabled paper entries, or the health gate. Rejection rows for bars
  with no raw setup are optional and disabled by default.

## Rule Defaults

These defaults match the current next-validation candidate from the fresh 480D
research pass:

- strategy ID:
  `vwap_delta_exhaustion_fade_2pt_10d_cl0.5_guard_risk175_exit6_10_12_initial_health3600_4000`
- setup window: `09:45:00` through `15:45:00`
- VWAP extension: `2.0` points
- minimum bar delta: `10`
- close location threshold: `0.5`
- minimum raw candidate spacing: `900` seconds
- max raw candidates per day: `20`
- context lookback: `20` same-date bars
- lookback directional move must be `<= -2.5` points
- session range must be `>= 30` points
- risk-to-average-bar-range must be `<= 1.75`
- initial stop: `10` points
- first target: `6` points
- runner target: `12` points
- runner stop mode: `initial`
- first leg quantity: `1`
- runner quantity: `1`
- paper daily loss limit: `$3600`
- paper daily profit lock: disabled with `0`
- paper accepted-equity drawdown limit: `$4000`
- ES point value: `$50`
- tick value: `$12.50`
- commission: `$1.75` per side
- slippage model: `1` tick per contract

The study uses the chart timestamps. Keep Sierra Chart time set to New York for
this test.

## LucidFlex 25K Notes

Manual help needed: **No** for reading this section. Manual help is needed later
to enter the selected profile values in Sierra Chart.

LucidFlex 25K rules checked on `2026-06-30`:

- evaluation target: `$1,250`;
- evaluation max loss limit: `$1,000`;
- evaluation consistency: `50%`;
- evaluation max size: `2 minis or 20 micros`;
- evaluation daily loss limit: none;
- funded max loss limit: `$1,000`;
- funded daily loss limit: none;
- funded consistency: none;
- funded scaling plan at `$0 - $999` simulated profit: `1 mini or 10 micros`;
- live starting drawdown: `$1,000`;
- live max contract limit: `2 minis or 20 micros`;
- live daily loss limit and consistency: none.

Sources:

- `https://support.lucidtrading.com/en/articles/12945790-lucidflex-evaluation-account`
- `https://support.lucidtrading.com/en/articles/12945795-lucidflex-funded-account`
- `https://support.lucidtrading.com/en/articles/12945808-lucidflex-scaling-plan`
- `https://support.lucidtrading.com/en/articles/12945805-lucidflex-consistency-percentage`
- `https://support.lucidtrading.com/en/articles/13425130-new-live-structure`

Important sizing consequence:

- `1 ES = 10 MES`;
- the research default `1 ES + 1 ES` has a full-stop loss of about `$1,000`
  before costs;
- that is too close to the LucidFlex 25K `$1,000` max loss limit;
- `5 MES + 5 MES` keeps the same two-leg structure with about half the ES
  research exposure and fits the funded starting scaling tier of `10 micros`.

For clean strategy continuity, run the signal on the ES chart and use MES point
values/quantities for paper P&L modeling. Running the signal directly on an MES
chart can change bid/ask volume and delta behavior versus the ES research
sample.

Suggested forward-sim profiles:

| Profile | First Leg Quantity | Runner Quantity | Point Value USD | Tick Value USD | Paper Daily Profit Lock USD | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Research ES | `1` | `1` | `50` | `12.5` | `0` | Matches historical ES research sizing. |
| LucidFlex 25K Eval MES | `5` | `5` | `5` | `1.25` | `650` | Models `5 MES + 5 MES`; use only if the dashboard consistency cushion allows it. |
| LucidFlex 25K Funded Start MES | `5` | `5` | `5` | `1.25` | `0` | Fits funded `$0 - $999` scaling tier of `10 micros`. |
| LucidFlex 25K Conservative MES | `2` | `2` | `5` | `1.25` | `0` | Lower exposure for first live-sim/live mechanics tests. |

The `650` profit lock is not a universal fixed Lucid rule. Lucid publishes it
as an example cushion for a 25K Flex evaluation at the target. Confirm the
dashboard before relying on it.

## Sync Source Into Sierra

Manual help needed: **No** for this command.

From the repository:

```bash
bash scripts/sync_to_sierra.sh
```

This copies the source to:

`C:\SierraChart\ACS_Source\AxonTradeVwapDeltaLiveSimBot.cpp`

## Build In Sierra Chart

Manual help needed: **Yes**.

Use the exact Sierra Chart path:

1. Click `Analysis >> Build Custom Studies DLL`.
2. In `Build Advanced Custom Studies DLL`, click `File >> Select Files`.
3. Select `AxonTradeVwapDeltaLiveSimBot.cpp`.
4. Click `Open`.
5. Click `Build >> Remote Build`.
6. Wait for the build output to say the remote build succeeded.
7. If Sierra asks to allow loading DLLs, click `Build >> Allow Load DLLs`.

If the build output says:

`Can't recognize 'cl ...' as an internal or external command`

you used the local Visual C++ path. In the same build window, click
`Build >> Remote Build`.

## Load On The ES Execution Chart

Manual help needed: **Yes**.

Use the ES 3-minute footprint/execution chart, not the TPO context chart. Use
the same chart type you used for the fresh 480D export.

1. Click `Global Settings >> Time Zone Settings`.
2. Confirm the time zone is New York.
3. Click `OK`.
4. Click the ES 3-minute footprint/execution chart window.
5. Click `Trade >> Trade Simulation Mode On` and confirm it is checked.
6. Click `Analysis >> Studies`.
7. Click `Add Custom Study`.
8. Expand `AxonTrade VWAP Delta Live Sim Bot`.
9. Select `AxonTrade VWAP Delta Live Sim Bot`.
10. Click `Add`.
11. In `Studies to Graph`, select `AxonTrade VWAP Delta Live Sim Bot`.
12. Click `Settings`.
13. In `Settings and Inputs`, confirm:
    - `CSV Log Path = C:\SierraChart\Data\AxonTrade_VwapDeltaLiveSimBot.csv`
    - `Trade Mode = live_sim`
    - `Enable Paper Entries = Yes`
    - `Log Rejections = No`
    - `Process Full Recalculation = No`
    - `Reset CSV On Full Recalculation = Yes`
    - `Setup Start Time = 09:45:00`
    - `Setup End Time = 15:45:00`
    - `Paper Flatten Time = 16:40:00`
    - `VWAP Extension Points = 2`
    - `Minimum Bar Delta = 10`
    - `Close Location Threshold = 0.5`
    - `Minimum Raw Candidate Spacing Seconds = 900`
    - `Max Raw Candidates Per Day = 20`
    - `Context Lookback Bars = 20`
    - `Maximum Lookback Directional Move Points = -2.5`
    - `Minimum Session Range Points = 30`
    - `Max Risk To Average Bar Range = 1.75`
    - `Initial Stop Points = 10`
    - `First Target Points = 6`
    - `Runner Target Points = 12`
    - `First Leg Quantity = 1`
    - `Runner Quantity = 1`
    - `Paper Daily Loss Limit USD = 3600`
    - `Paper Daily Profit Lock USD = 0`
    - `Paper Accepted Equity Drawdown USD = 4000`
    - `Point Value USD = 50`
    - `Tick Value USD = 12.5`
    - `Commission Per Side USD = 1.75`
    - `Slippage Ticks Per Contract = 1`
    - `Max Open Paper Trades = 20`
14. Click `OK`.
15. Click `OK` again to close Chart Studies.

Expected chart result:

- accepted virtual longs draw a blue up arrow, label, stop segment, first target
  segment, and runner target segment;
- accepted virtual shorts draw a red down arrow, label, stop segment, first
  target segment, and runner target segment;
- full virtual exits draw a yellow diamond and label;
- entry and exit rows append to the CSV log.

## Set A LucidFlex MES Profile

Manual help needed: **Yes**.

Use this when you want ES signals but MES-sized paper P&L:

1. Click the ES 3-minute footprint/execution chart window.
2. Click `Analysis >> Studies`.
3. In `Studies to Graph`, select `AxonTrade VWAP Delta Live Sim Bot`.
4. Click `Settings`.
5. In `Settings and Inputs`, set:
   - `First Leg Quantity = 5`
   - `Runner Quantity = 5`
   - `Point Value USD = 5`
   - `Tick Value USD = 1.25`
   - `Paper Daily Profit Lock USD = 650` for LucidFlex 25K evaluation testing,
     or `0` for funded/live-sim testing without consistency caps
6. For a stricter prop-risk approximation, set:
   - `Paper Daily Loss Limit USD = 900`
   - `Paper Accepted Equity Drawdown USD = 900`
7. Click `OK`.
8. Click `OK` again to close Chart Studies.

These settings do not change the signal rule, stop, or targets. They only
change the virtual exposure and paper risk controls.

## Rolling Live-Sim Use

Manual help needed: **No** after the study is built and loaded.

1. Before the RTH test, click `Trade >> Trade Simulation Mode On` and confirm it
   is checked.
2. Confirm the Sierra title bar shows `[Sim]`.
3. Start the test before `09:45:00` New York time when possible.
4. Leave `Analysis >> Studies >> AxonTrade VWAP Delta Live Sim Bot >> Settings`
   with `Process Full Recalculation = No`.
5. Let live or replay bars close through the setup window.
6. Check the log at:
   `C:\SierraChart\Data\AxonTrade_VwapDeltaLiveSimBot.csv`

If you add the study mid-session and want to backfill all loaded closed bars one
time:

1. Click `Analysis >> Studies`.
2. Select `AxonTrade VWAP Delta Live Sim Bot`.
3. Click `Settings`.
4. Confirm `Log Rejections = No`.
5. Confirm `Reset CSV On Full Recalculation = Yes`.
6. Set `Process Full Recalculation = Yes`.
7. Click `OK`.
8. Click `Chart >> Recalculate`.
9. After the backfill finishes, click `Analysis >> Studies`.
10. Select `AxonTrade VWAP Delta Live Sim Bot`.
11. Click `Settings`.
12. Set `Process Full Recalculation = No`.
13. Click `OK`.

Leaving `Process Full Recalculation = Yes` can repeat historical backfills
during recalculations. Turning `Log Rejections = Yes` during a full backfill can
write a very large diagnostic file.
