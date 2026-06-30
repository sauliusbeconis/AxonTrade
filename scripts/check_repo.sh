#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "== AxonTrade repository checks =="

order_call_regex='sc\.(BuyEntry|SellEntry|BuyOrder|SellOrder|BuyExit|SellExit|FlattenAndCancelAllOrders)'
approved_order_file="src/acsil/AxonTradeVwapDeltaExecutionBot.cpp"

if command -v rg >/dev/null 2>&1; then
  if rg --glob '*.cpp' --glob '*.h' --glob "!$(basename "$approved_order_file")" "$order_call_regex" src/acsil; then
    echo "ERROR: prohibited ACSIL order-routing call found outside $approved_order_file." >&2
    exit 1
  fi
  if [[ -f "$approved_order_file" ]] && rg "$order_call_regex" "$approved_order_file" >/dev/null; then
    echo "Safety scan passed: order-routing calls are isolated to $approved_order_file."
  else
    echo "Safety scan passed: no ACSIL order-routing calls found."
  fi
else
  mapfile -d '' acsil_files < <(find src/acsil -type f \( -name '*.cpp' -o -name '*.h' \) ! -path "$approved_order_file" -print0)
  if ((${#acsil_files[@]} > 0)); then
    if grep -H -E "$order_call_regex" "${acsil_files[@]}"; then
      echo "ERROR: prohibited ACSIL order-routing call found outside $approved_order_file." >&2
      exit 1
    fi
  fi
  if [[ -f "$approved_order_file" ]] && grep -E "$order_call_regex" "$approved_order_file" >/dev/null; then
    echo "Safety scan passed: order-routing calls are isolated to $approved_order_file."
  else
    echo "Safety scan passed: no ACSIL order-routing calls found."
  fi
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
elif [[ -n "$python_bin" ]] && "$python_bin" -c "import ruff" >/dev/null 2>&1; then
  "$python_bin" -m ruff check src tests
else
  echo "Skipping ruff: command not found."
fi

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck scripts/*.sh
else
  echo "Skipping shellcheck: command not found."
fi

echo "Repository checks completed."
