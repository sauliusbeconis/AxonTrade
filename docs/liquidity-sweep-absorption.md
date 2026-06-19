# Liquidity Sweep Absorption Layer

This is the first order-flow layer for the liquidity sweep reversal setup
family. It extends the price-only sweep proxy with bid/ask volume confirmation.

Manual help needed: **Yes, later, before this can run on real Sierra exports.**
The code is ready, but Sierra must export bid volume and ask volume columns.

## Rule Intent

The setup is not simply "fade every breakout." The first absorption proxy
requires:

- price sweeps beyond the opening range;
- price closes back inside the opening range;
- sweep-side aggression is visible in bid/ask volume;
- the bar closes against that aggression.

Short example:

- high sweeps above opening-range high;
- close returns below opening-range high;
- ask volume dominates bid volume;
- delta is positive;
- close is in the lower `45%` of the bar.

Long example:

- low sweeps below opening-range low;
- close returns above opening-range low;
- bid volume dominates ask volume;
- delta is negative;
- close is in the upper `55%` of the bar.

## Files

- Rule profile: `config/research/liquidity_sweep_absorption_reversal.yaml`
- Sierra export profile: `config/research/sierra_orderflow_bar_export.yaml`
- Runner: `scripts/run_liquidity_sweep_absorption.py`

## Sierra Manual Export Setup

Manual help needed: **Yes**.

In Sierra Chart, use this exact path:

1. Open the chartbook tab that contains the ES execution chart.
2. Press `Analysis >> Studies`.
3. Add or select `Numbers Bars Calculated Values`.
4. In that study, expose/export columns equivalent to:
   - `Bid Volume`
   - `Ask Volume`
   - optionally `Delta`
5. Press `OK`.
6. Use `Edit >> Export Bar and Study Data to Text File`.
7. Save/export to:
   `C:\SierraChart\Data\AxonTrade_ES_OrderflowExport.txt`

From Linux/Wine, that file should be available at:

`/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport.txt`

If Sierra names the columns differently, update aliases in
`config/research/sierra_orderflow_bar_export.yaml`.

## Run

Manual help needed: **No after the export file exists**.

First check whether the export has the required columns:

```bash
.venv/bin/python scripts/check_orderflow_export.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport.txt
```

If the check reports `manual_sierra_help_needed=yes`, fix the Sierra export
columns before running the absorption evaluator.

```bash
.venv/bin/python scripts/run_liquidity_sweep_absorption.py \
  /home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/AxonTrade_ES_OrderflowExport.txt \
  data/processed/AxonTrade_ES_absorption_signals.csv \
  data/processed/AxonTrade_ES_absorption_outcomes.csv \
  --symbol ESU26-CME \
  --chart-number 1 \
  --session-phase rth
```

Then write the report:

```bash
.venv/bin/python scripts/report_price_only_outcomes.py \
  data/processed/AxonTrade_ES_absorption_signals.csv \
  data/processed/AxonTrade_ES_absorption_outcomes.csv \
  reports/liquidity-sweep-absorption-sample.md
```

## Current Status

The evaluator is implemented and tested with synthetic rows. It has not yet
been run on real Sierra order-flow exports because the current local export does
not include bid/ask volume columns.
