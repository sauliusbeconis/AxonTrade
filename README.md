# AxonTrade

AxonTrade is a professional-grade futures trading research and execution laboratory focused first on intraday ES/MES and NQ/MNQ research.

It is not a get-rich-quick trading bot, signal service, black-box system, martingale engine, grid recovery tool, HFT system, or microscalping project.

## Current Phase

Phase 0 is foundation and simulation-safe research tooling.

Live order routing is disabled by policy and is not implemented in this repository.

## Platform Stack

- Sierra Chart for charting, replay, and platform-side studies.
- ACSIL C++ for Sierra Chart indicators, visual tools, and simulation-safe event logging.
- Python for offline research, configuration validation, analytics, and reports.
- YAML for prop-firm profiles, instrument settings, costs, and internal risk limits.
- Pop!_OS Linux with Sierra Chart running through Wine as the target development workstation.

## Why Sierra Chart And ACSIL

Sierra Chart gives direct access to futures market data, replay, chart studies, and platform-native ACSIL extensions. ACSIL is used for platform-side study logic because it can draw on charts, read bar and study state, and integrate with Sierra Chart replay while keeping this phase indicator-only.

## Why Python

Python is used away from the trading platform for reproducible research: loading configs, validating assumptions, analyzing exported CSV events, producing reports, and eventually running chronological walk-forward tests.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
bash scripts/check_repo.sh
```

On Windows, use PowerShell with the same Python commands. The shell scripts are intended for Pop!_OS or another Linux environment with Bash.

## Current Research Workflow

After exporting Sierra Chart bars, run the price-only signal and outcome
workflow documented in
[docs/price-only-outcome-workflow.md](docs/price-only-outcome-workflow.md).
Then use
[docs/price-only-parameter-sweep.md](docs/price-only-parameter-sweep.md)
to compare simple stop/target variants.
Use
[docs/price-only-train-holdout-sweep.md](docs/price-only-train-holdout-sweep.md)
to check whether selected parameters survive later dates.
Use
[docs/price-only-walk-forward-sweep.md](docs/price-only-walk-forward-sweep.md)
to repeat that selection across rolling chronological windows.
Then run
[docs/acceptance-gates.md](docs/acceptance-gates.md)
to check whether the current research sample passes the configured evidence
gates.

The first concrete setup-family branch is the price-only liquidity sweep
reversal proxy documented in
[docs/price-only-liquidity-sweep.md](docs/price-only-liquidity-sweep.md).
The first bid/ask-volume absorption layer is documented in
[docs/liquidity-sweep-absorption.md](docs/liquidity-sweep-absorption.md).
Use `scripts/check_orderflow_export.py` before running that layer to verify the
Sierra export contains the required bid/ask volume fields.
Reward/risk filtering experiments for that layer are documented in
[docs/liquidity-sweep-reward-risk-sweep.md](docs/liquidity-sweep-reward-risk-sweep.md).
Rolling walk-forward validation for that filter is documented in
[docs/liquidity-sweep-reward-risk-walk-forward.md](docs/liquidity-sweep-reward-risk-walk-forward.md).
The next level-specific footprint export contract is documented in
[docs/sierra-volume-at-price-export.md](docs/sierra-volume-at-price-export.md).
The Sierra-side logger workflow for that file is documented in
[docs/sierra-volume-at-price-logger.md](docs/sierra-volume-at-price-logger.md).
The first diagnostic pass over swept price levels is run with
`scripts/run_vap_absorption_diagnostics.py` and documented in
[docs/liquidity-sweep-vap-absorption-diagnostics.md](docs/liquidity-sweep-vap-absorption-diagnostics.md).

## Pop!_OS And Wine Notes

The target workstation runs Sierra Chart under Wine. See [docs/popos-wine-setup.md](docs/popos-wine-setup.md) for setup notes and [docs/sierra-chart-development.md](docs/sierra-chart-development.md) for ACSIL workflow notes.

## Sync ACSIL Files Into Sierra Chart

Set `WINEPREFIX` if your Sierra Chart prefix is not the default:

```bash
export WINEPREFIX="$HOME/wineprefixes/sierrachart"
bash scripts/sync_to_sierra.sh
```

The sync script copies `src/acsil/*.cpp` into Sierra Chart's `ACS_Source` directory. It does not compile, launch Sierra Chart, or place orders.

## Safety Status

This repository currently contains no live order-routing implementation. All strategy material is hypothesis documentation until it passes the documented research, replay, forward-simulation, and safety-review gates.
