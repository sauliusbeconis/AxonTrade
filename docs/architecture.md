# Architecture

AxonTrade separates research, visualization, logging, risk controls, and future execution boundaries.

## Components

- `src/acsil`: Sierra Chart ACSIL studies for chart visualization and simulation-safe event logging.
- `src/axontrade/config`: YAML loading and validation.
- `src/axontrade/risk`: basic research-phase risk-limit checks.
- `src/axontrade/research`: future offline research workflows.
- `src/axontrade/reports`: future report generation.
- `src/axontrade/data`: future data access helpers.
- `config`: firm, instrument, cost, and risk profiles.
- `docs`: research design, safety, phase gates, and operational notes.
- `scripts`: local workflow helpers.
- `tests`: Python tests.

## Data Flow

1. Sierra Chart study draws and logs simulation-safe events.
2. CSV exports are reviewed and archived outside live-order paths.
3. Python tools load configs and analyze exported event data.
4. Reports compare hypotheses against baselines and acceptance gates.

## Execution Boundary

Execution is intentionally absent in phase 0. Any future execution subsystem must be introduced only after explicit authorization, documented safety review, and passing acceptance gates.
