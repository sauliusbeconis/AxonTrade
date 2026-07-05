# MNQ Eval-Pass Wave Rider Cadence Refinement

Status: faster-cadence offline research only; not implementation-ready.

## Source

- rows: `67300`
- dates: `2024-07-15` through `2026-07-02`
- unique dates: `507`
- base signals: `505`
- instrument: `MNQ`, point value `$2`, tick value `$0.50`
- cost model: `$0.50/side` commission plus `1` total slippage tick per contract

## Base Idea

`lb10 / buf0 / delta300 / cl0.55 / 10:00-12:30` lookback breakout.

This is the faster B-setup family. It intentionally gives up two-day pass potential in exchange for many more signals than the sparse A+ lead.

## Best Low-Fail Row

| Metric | Value |
| --- | ---: |
| Strategy | `cadence_refine:no_thu_fri:short:1000_1230:none` |
| Quantity | `4` |
| Target / stop | `$350 / $650` |
| Trades | `129` |
| Signal frequency | `0.25443787` per trading day |
| Median signal gap | `3.5` trading days |
| Max signal gap | `14` trading days |
| Full-sample net | `$17496` |
| Latest-year net | `$4200` |
| Worst quarter | `$350` |
| Trade-sequence max DD | `$-2118` |
| Calendar-start pass / fail / timeout | `30.4% / 4.1% / 65.5%` |
| Signal-start pass / fail | `66.7% / 13.2%` |
| Median calendar days to pass | `21.5` |
| Median traded days to pass | `4` |

## Strict Rows

Rows shown here have calendar-start pass `>=30%`, fail `<=12%`, and at least `80` trades.

| Rank | Qty | Target | Stop | Trades | Latest Net | Cal Pass | Cal Fail | Timeout | Signal Pass | Signal Fail | Median Trade Days | DD | Strategy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 4 | 350 | 650 | 129 | 4200 | 30.4% | 4.1% | 65.5% | 66.7% | 13.2% | 4 | -2118 | `cadence_refine:no_thu_fri:short:1000_1230:none` |
| 2 | 3 | 351 | 499.5 | 155 | 5311.5 | 33.3% | 7.1% | 59.6% | 58.7% | 13.5% | 6 | -2566.5 | `cadence_refine:tue_wed:both:1000_1045:vwap_le100` |
| 3 | 3 | 351 | 499.5 | 129 | 4341 | 33.5% | 7.5% | 59.0% | 65.9% | 12.4% | 4 | -2740.5 | `cadence_refine:no_thu_fri:short:1000_1230:none` |
| 4 | 3 | 351 | 499.5 | 127 | 4341 | 31.8% | 7.5% | 60.7% | 65.4% | 12.6% | 4 | -2740.5 | `cadence_refine:no_thu_fri:short:1000_1130:none` |
| 5 | 4 | 350 | 650 | 146 | 4122 | 30.2% | 7.7% | 62.1% | 52.1% | 15.1% | 4 | -3604 | `cadence_refine:tue_wed:both:1000_1230:move125_bar60` |
| 6 | 4 | 350 | 650 | 151 | 1650 | 30.6% | 8.1% | 61.3% | 49.0% | 13.9% | 4 | -2200 | `cadence_refine:mon_wed_fri:short:1000_1045:none` |
| 7 | 3 | 351 | 499.5 | 147 | 4960.5 | 31.2% | 8.3% | 60.6% | 64.6% | 14.3% | 5 | -2592 | `cadence_refine:tue_wed:both:1000_1045:move_le125` |
| 8 | 3 | 351 | 499.5 | 180 | 4663.5 | 34.1% | 8.5% | 57.4% | 56.1% | 14.4% | 6 | -2473.5 | `cadence_refine:tue_wed:both:1000_1230:vwap_le100` |
| 9 | 3 | 351 | 499.5 | 179 | 4663.5 | 32.7% | 8.5% | 58.8% | 55.3% | 14.5% | 6 | -2473.5 | `cadence_refine:tue_wed:both:1000_1130:vwap_le100` |
| 10 | 3 | 351 | 499.5 | 173 | 4663.5 | 31.0% | 8.5% | 60.6% | 52.6% | 15.6% | 5 | -2325 | `cadence_refine:tue_wed:both:1000_1100:vwap_le100` |
| 11 | 3 | 351 | 499.5 | 151 | 1695 | 31.8% | 8.7% | 59.6% | 53.6% | 11.3% | 4 | -1836 | `cadence_refine:mon_wed_fri:short:1000_1045:none` |
| 12 | 3 | 400.5 | 499.5 | 129 | 5479.5 | 31.2% | 9.3% | 59.6% | 73.6% | 12.4% | 4 | -2922 | `cadence_refine:no_thu_fri:short:1000_1230:none` |

## Balanced Rows

Rows shown here have calendar-start pass `>=35%`, fail `<=16%`, and at least `80` trades.

| Rank | Qty | Target | Stop | Trades | Latest Net | Cal Pass | Cal Fail | Timeout | Signal Pass | Signal Fail | Median Trade Days | DD | Strategy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 3 | 351 | 499.5 | 172 | 4312.5 | 36.9% | 9.7% | 53.5% | 61.0% | 15.1% | 6 | -2592 | `cadence_refine:tue_wed:both:1000_1230:move_le125` |
| 2 | 3 | 351 | 499.5 | 171 | 4312.5 | 35.5% | 9.7% | 54.8% | 60.2% | 15.2% | 6 | -2592 | `cadence_refine:tue_wed:both:1000_1130:move_le125` |
| 3 | 4 | 350 | 650 | 147 | 5572 | 36.3% | 10.1% | 53.6% | 57.8% | 17.0% | 5 | -3404 | `cadence_refine:tue_wed:both:1000_1045:move_le125` |
| 4 | 4 | 350 | 650 | 155 | 5922 | 36.3% | 11.2% | 52.5% | 58.1% | 21.3% | 5 | -4354 | `cadence_refine:tue_wed:both:1000_1045:vwap_le100` |
| 5 | 3 | 351 | 499.5 | 178 | 6270 | 40.0% | 11.6% | 48.3% | 59.0% | 17.4% | 6 | -2781 | `cadence_refine:tue_wed:both:1000_1045:none` |
| 6 | 4 | 350 | 650 | 172 | 4622 | 39.3% | 12.2% | 48.5% | 52.9% | 17.4% | 5 | -3500 | `cadence_refine:tue_wed:both:1000_1230:move_le125` |
| 7 | 4 | 350 | 650 | 171 | 4622 | 37.7% | 12.2% | 50.1% | 52.6% | 17.5% | 5 | -3500 | `cadence_refine:tue_wed:both:1000_1130:move_le125` |
| 8 | 4 | 400 | 650 | 129 | 3286 | 36.9% | 12.2% | 50.9% | 64.3% | 22.5% | 4 | -2800 | `cadence_refine:no_thu_fri:short:1000_1230:none` |
| 9 | 4 | 400 | 650 | 127 | 3286 | 36.5% | 12.2% | 51.3% | 63.8% | 22.8% | 4 | -2800 | `cadence_refine:no_thu_fri:short:1000_1130:none` |
| 10 | 3 | 351 | 499.5 | 204 | 5973 | 40.2% | 12.8% | 46.9% | 54.9% | 18.6% | 6 | -3039 | `cadence_refine:tue_wed:both:1000_1230:none` |
| 11 | 3 | 351 | 499.5 | 203 | 5973 | 40.0% | 12.8% | 47.1% | 54.7% | 18.7% | 6 | -3039 | `cadence_refine:tue_wed:both:1000_1130:none` |
| 12 | 3 | 351 | 499.5 | 178 | 1897.5 | 37.9% | 12.8% | 49.3% | 55.1% | 14.0% | 4 | -2199 | `cadence_refine:mon_wed_fri:short:1000_1230:none` |

## Interpretation

This is a materially faster B setup than the sparse A+ lead, but it is not a deployment candidate yet. The best low-fail row trades about every three trading days and cuts calendar-start fail rate near the `10-12%` target, but it still needs walk-forward, slippage stress, and replay mechanics before any implementation discussion.

Two-day pass rate is expected to be `0%` for the low-fail rows because the per-trade target is about `$350`; this path is designed for a multi-trade eval pass.
