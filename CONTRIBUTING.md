# Contributing

AxonTrade is currently in a foundation and simulation-safe research phase.

## Rules

- Do not add live order-routing code.
- Do not add hidden live-trading flags.
- Do not commit credentials, account numbers, or personal secrets.
- Do not implement martingale, grid recovery, averaging down, HFT, or microscalping behavior.
- Document strategy ideas as hypotheses before implementation.
- Keep firm rules and instrument settings in YAML.
- Add or update tests when changing Python config or risk behavior.

## Pull Requests

Pull requests should include:

- summary of changes;
- assumptions;
- safety impact;
- tests or checks run;
- manual verification still required.
