# Sierra Signal Log Report

This workflow validates and summarizes signal-log rows written by the Sierra
Chart indicator-only overlay.

Manual help needed: **No** after `AxonTrade_SignalLog.csv` exists.

## Inputs

Live Sierra path:

`C:\SierraChart\Data\AxonTrade_SignalLog.csv`

Linux/Wine path:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_SignalLog.csv`

Local replay sample used for the current report:

`data/processed/AxonTrade_ES_overlay_signal_log_replay_sample.csv`

## Run

From the repository:

```bash
.venv/bin/python scripts/report_signal_log.py \
  data/processed/AxonTrade_ES_overlay_signal_log_replay_sample.csv \
  reports/sierra-signal-log-replay-sample.md
```

For the active Sierra log:

```bash
.venv/bin/python scripts/report_signal_log.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_SignalLog.csv \
  reports/sierra-signal-log-live.md
```

The script validates:

- the exact CSV header from `config/research/signal_log_schema.yaml`;
- required fields by event type;
- allowed enum values;
- numeric field parsing.

## Current Replay Sample

Local source:

`data/processed/AxonTrade_ES_overlay_signal_log_replay_sample.csv`

Output:

`reports/sierra-signal-log-replay-sample.md`

Current sample result:

- rows: `808`
- candidate signals: `2`
- rejected signals: `806`
- symbols: `ESU26-CME`
- candidate directions: `2` long, `0` short

Candidate rows:

| Time | Direction | Entry | Stop | Target |
| --- | --- | ---: | ---: | ---: |
| `2026-06-17 10:42:28` | `long` | `7581.25` | `7579.25` | `7590.5` |
| `2026-06-19 12:59:58` | `long` | `7556.75` | `7553.75` | `7559.75` |

Interpretation: the Sierra overlay is logging valid signal-schema rows. This is
not strategy validation; candidate rows still need outcome evaluation.
