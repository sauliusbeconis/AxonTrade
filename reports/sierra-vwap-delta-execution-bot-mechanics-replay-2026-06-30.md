# Sierra VWAP Delta Execution Bot Mechanics Replay

Status: **PASS for simulation mechanics, not live-ready**

## Scope

This report records the first Sierra Chart replay mechanics checks for
`AxonTradeVwapDeltaExecutionBot.cpp`.

Replay was run on `2026-06-30` using Sierra simulation mode and historical
`ESU26-CME` replay bars. The bot used the current, unrelaxed guard settings:

- `vwap_delta_exhaustion_fade_2pt_10d_cl0.5`
- `lookback_directional_move_points <= -2.5`
- `session_range_points >= 30`
- `risk_to_average_bar_range <= 1.75`
- `6 / 10 / 12 / initial` exits
- `First Leg Quantity = 1`
- `Runner Quantity = 1`
- `Send Orders To Trade Service = No`
- `Confirmation Text = SIM_ONLY`

Sources:

- Runtime CSV:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_VwapDeltaExecutionBot.csv`
- Trade activity logs:
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/TradeActivityLogs/TradeActivityLog_2026-06-25_UTC.Sim1.simulated.data`
  and
  `/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/TradeActivityLogs/TradeActivityLog_2026-06-18_UTC.Sim1.simulated.data`

## Replay Cases

| Case | Replay Bar | Direction | Result | Internal Order IDs |
| --- | --- | --- | --- | --- |
| First target / scale-out mechanics | `2026-06-25 12:45:00` | Long | `execution_entry_submitted`, `order_result = 2` | parent `43`, target1 `41`, target2 `44`, stop `42` |
| Stop / daily-lock mechanics | `2026-06-18 10:42:00` | Short | `execution_entry_submitted`, `order_result = 2` | parent `49`, target1 `47`, target2 `50`, stop `48` |

The first pass was also visually checked in Sierra Chart. The observed parent
order, two targets, and common stop appeared correctly.

## Follow-Up State

For the `2026-06-25 12:45:00` long replay:

- position moved from `2` to `1` after the first target state;
- working orders remained present while the runner was open;
- the replay later reached flat state with no working orders;
- `daily_profit_loss = 900`.

For the `2026-06-18 10:42:00` short replay:

- the bot submitted a short parent with both targets and the common stop;
- at `2026-06-18 10:45:00`, the bot logged `execution_flatten_submitted`;
- flatten notes were `daily loss lock active; loss_view=-825; limit=200`;
- at `2026-06-18 10:57:00`, a later valid setup was blocked with
  `daily_loss_lock_blocked`.

## Coverage

Confirmed:

- explicit arming gate;
- simulation-only order submission;
- long entry;
- short entry;
- parent market order with two attached targets and one common stop;
- first-target scale-out state;
- flatten/cancel submission path;
- daily loss lock;
- post-loss same-day entry block;
- CSV mechanics logging.

Not yet confirmed:

- scheduled session-flatten time behavior on an open position;
- optional breakeven stop movement;
- live trade-service routing, which remains intentionally disabled.

## Decision

The simulation mechanics harness has enough coverage for the current phase.
Further progress should shift back to profitability validation.

The current live-promotion blocker is not order mechanics. The blocker is that
the fresh 480D research still requires true future validation after
`2026-06-30` with the selected entry, guard, exit, and health-gate rules held
fixed. Live routing remains disabled.

Next validation vehicle:

- use `AxonTradeVwapDeltaLiveSimBot.cpp` for future paper/live-sim evidence;
- keep the order-submitting execution harness disarmed unless running an
  explicit mechanics replay;
- keep the live-sim defaults aligned to the selected validation candidate:
  `6 / 10 / 12 / initial`, `risk_to_average_bar_range <= 1.75`,
  `Paper Daily Loss Limit USD = 3600`, and
  `Paper Accepted Equity Drawdown USD = 4000`.
