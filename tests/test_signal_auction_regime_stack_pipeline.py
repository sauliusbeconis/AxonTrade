from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_pipeline_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / (
        "run_signal_auction_regime_stack_pipeline.py"
    )
    spec = importlib.util.spec_from_file_location("run_signal_auction_regime_stack_pipeline", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_pipeline_output_paths_are_sample_specific() -> None:
    module = _load_pipeline_module()

    paths = module._output_paths(Path("reports"), "test-sample")

    assert paths["filter_overlap"] == Path(
        "reports/sierra-signal-log-auction-regime-filter-walk-forward-test-sample.csv",
    )
    assert paths["filter_holdout1"] == Path(
        "reports/sierra-signal-log-auction-regime-filter-walk-forward-holdout1-test-sample.csv",
    )
    assert paths["target_acceptance_holdout1"] == Path(
        "reports/sierra-signal-log-auction-regime-target-r-acceptance-holdout1-test-sample.md",
    )
    assert paths["breakeven_acceptance_overlap"] == Path(
        "reports/sierra-signal-log-auction-regime-breakeven-acceptance-test-sample.md",
    )


def test_pipeline_parses_comma_lists() -> None:
    module = _load_pipeline_module()

    assert module._parse_float_list("0.5, 1,2.5") == [0.5, 1.0, 2.5]
    assert module._parse_string_list("all, long,,short") == ["all", "long", "short"]


def test_pipeline_rejects_blank_output_tag() -> None:
    module = _load_pipeline_module()

    with pytest.raises(ValueError, match="output tag"):
        module._output_paths(Path("reports"), " ")
