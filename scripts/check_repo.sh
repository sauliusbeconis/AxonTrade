#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "== AxonTrade repository checks =="

if command -v rg >/dev/null 2>&1; then
  if rg --glob '*.cpp' --glob '*.h' 'sc\.(BuyEntry|SellEntry|BuyOrder|SellOrder|BuyExit|SellExit|FlattenAndCancelAllOrders)' src/acsil; then
    echo "ERROR: prohibited ACSIL order-routing call found in src/acsil." >&2
    exit 1
  fi
  echo "Safety scan passed for src/acsil."
else
  if grep -R -E --include='*.cpp' --include='*.h' 'sc\.(BuyEntry|SellEntry|BuyOrder|SellOrder|BuyExit|SellExit|FlattenAndCancelAllOrders)' src/acsil; then
    echo "ERROR: prohibited ACSIL order-routing call found in src/acsil." >&2
    exit 1
  fi
  echo "Safety scan passed for src/acsil."
fi

python_bin="${PYTHON:-}"
if [[ -z "$python_bin" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    python_bin="python3"
  elif command -v python >/dev/null 2>&1; then
    python_bin="python"
  fi
fi

if [[ -n "$python_bin" ]]; then
  if "$python_bin" -c "import pytest" >/dev/null 2>&1; then
    "$python_bin" -m pytest
  else
    echo "Skipping pytest: pytest is not installed for $python_bin."
    echo "Install dev dependencies with: $python_bin -m pip install -e '.[dev]'"
  fi
else
  echo "Skipping Python checks: no python3 or python executable found."
fi

if command -v ruff >/dev/null 2>&1; then
  ruff check src tests
else
  echo "Skipping ruff: command not found."
fi

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck scripts/*.sh
else
  echo "Skipping shellcheck: command not found."
fi

echo "Repository checks completed."
