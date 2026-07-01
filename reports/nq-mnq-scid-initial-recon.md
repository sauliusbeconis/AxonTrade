# NQ/MNQ SCID Initial Recon

Status: research lead only, not live-ready.

This report records the first NQ/MNQ branch pass after adding local SCID bar
export tooling.

## Data

Local files:

- `NQM26-CME.scid`: `34,295,042` records, `2025-12-15 12:44:37` through
  `2026-06-18 13:29:55`;
- `MNQM26-CME.scid`: `123,393,887` records, `2025-12-15 09:53:09` through
  `2026-06-18 13:29:59`.

Exported NQ bars:

- `12725` 3-minute bars;
- source: `NQM26-CME.scid`;
- output:
  `data/processed/AxonTrade_NQ_scid_3min_rth_20251215_20260618.csv`;
- session filter used: `09:30:00` to `16:00:00`.

Important caveat: the SCID timestamp timezone/session alignment has not been
confirmed against Sierra. Treat all results as reconnaissance only.

## Full-Sample Sweep

Top full-sample rows:

| Strategy | First | Stop | Runner | Mode | Trades | Net | Avg |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| `impulse_continue_3bar_1.5pt` | 20 | 10 | 60 | initial | 2550 | `184760` | `72.45` |
| `vwap_extension_fade_3pt` | 20 | 10 | 60 | initial | 2574 | `151972` | `59.04` |
| `impulse_continue_5bar_2pt` | 20 | 10 | 60 | initial | 2512 | `145996` | `58.12` |
| `impulse_fade_5bar_2pt` | 20 | 10 | 60 | initial | 2512 | `138796` | `55.25` |
| `vwap_extension_fade_2pt` | 20 | 10 | 60 | initial | 2580 | `138360` | `53.63` |

The random baseline also reached `109156`, so the full-sample sweep is not
enough to accept a candidate.

## Focused Walk-Forward

One-tick total slippage per contract:

| Strategy | Windows | Trades | Net | Avg/Trade | Negative Windows | Worst Window |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `impulse_continue_3bar_1.5pt` | 22 | 2193 | `135789` | `61.92` | 10 | `-9300` |
| `impulse_continue_5bar_2pt` | 22 | 2184 | `106857` | `48.93` | 8 | `-16000` |
| `impulse_fade_5bar_2pt` | 22 | 2184 | `81842` | `37.47` | 5 | `-17100` |
| `random_25_per_day` | 22 | 2750 | `21040` | `7.65` | 10 | `-16125` |
| `vwap_extension_fade_3pt` | 22 | 2195 | `86175` | `39.26` | 8 | `-17700` |

Four-tick total slippage per contract:

| Strategy | Windows | Trades | Net | Avg/Trade | Negative Windows | Worst Window |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `impulse_continue_3bar_1.5pt` | 22 | 2193 | `69999` | `31.92` | 10 | `-12300` |
| `impulse_continue_5bar_2pt` | 22 | 2184 | `41337` | `18.93` | 10 | `-19000` |
| `impulse_fade_5bar_2pt` | 22 | 2184 | `16322` | `7.47` | 10 | `-20100` |
| `random_25_per_day` | 22 | 2750 | `-61460` | `-22.35` | 14 | `-19875` |
| `vwap_extension_fade_3pt` | 22 | 2195 | `20325` | `9.26` | 8 | `-20700` |

## Interpretation

The first actual lead is `impulse_continue_3bar_1.5pt`, not a VWAP/delta fade.
That is directionally different from the current ES/MES bot and supports
keeping NQ/MNQ separate.

The lead is not accepted:

- too many negative windows;
- worst windows are too large for prop-eval sizing;
- random baseline behavior shows the dataset/session needs more scrutiny;
- only the June 2026 contract was available locally.
