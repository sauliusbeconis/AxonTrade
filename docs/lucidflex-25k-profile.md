# LucidFlex 25K Profile

The initial target account profile is a Lucid Trading LucidFlex 25K evaluation account.

The repository stores this as YAML in `config/firms/lucidflex_25k_evaluation.yaml` so research and risk checks can read account constraints without hardcoding them into strategy logic.

## Phase-0 Values

- Account size: 25000 USD.
- Profit target: 1250 USD.
- Max loss limit: 1000 USD.
- Drawdown type: end-of-day trailing.
- Consistency max: 50 percent.
- Max position: 2 minis or 20 micros.
- Mandatory flat time: 16:45 America/New_York.
- Internal forced flat time: 16:40 America/New_York.
- Disable new entries after: 16:35 America/New_York.
- Simulation only: true.
- Live automated entries: false.
- One-click approved entries: false.

## Verification Requirement

These values must be verified against official Lucid Trading account documents before any funded or live trading decision. Research code may use them as development configuration, not as legal or account-management advice.

Public references checked during planning:

- https://lucidtrading.com/
- https://support.lucidtrading.com/en/articles/12945805-lucidflex-consistency-percentage
