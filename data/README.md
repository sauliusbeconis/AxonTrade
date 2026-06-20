# Research Data

Store local research datasets outside Git unless a small fixture is intentionally added for tests.

Suggested local layout:

- `data/raw`: raw exports from Sierra Chart or other sources.
- `data/processed`: normalized research datasets.

Large data files should not be committed.

`data/processed/AxonTrade_ES_overlay_signal_log_replay_sample.csv` is the local
Sierra replay sample used to generate `reports/sierra-signal-log-replay-sample.md`.
