# Decision Log

## 2026-06-16: Initialize Phase-0 Foundation

Decision: start AxonTrade as a research-first, simulation-safe futures trading laboratory.

Context:

- Target instruments are ES/MES and NQ/MNQ.
- Sierra Chart ACSIL is used for platform-side visual/logging studies.
- Python is used for offline research and reporting.
- Live order routing is prohibited in the foundation phase.

Consequences:

- Strategy ideas are documented as hypotheses only.
- Account and instrument rules live in YAML.
- The first ACSIL study is indicator-only.
- Manual Sierra Chart verification remains required.

## 2026-06-29: Keep Delta Impulse Fixed Row Research-Only

Decision: keep collecting the Sierra delta-impulse `5 / 10 / 8 / initial`
variant, but do not promote it to live order routing.

Context:

- The larger 78-trade sample is positive in-sample at `3104` net USD.
- Rolling walk-forward selection is still negative.
- The fixed-row robustness check shows dependence on the last few dates, a
  narrow parameter shelf, holiday/early-close handling, and weak shorts.

Consequences:

- The current Sierra overlay can continue logging candidates.
- Holiday/early-close flags are required before acceptance testing.
- The next validation step is fixed-row holdout/walk-forward reporting, not a
  live execution change.

## 2026-06-29: Reject Delta Impulse Fixed Row After Expanded Export

Decision: reject the Sierra delta-impulse `5 / 10 / 8 / initial` fixed row as
a current strategy candidate.

Context:

- The expanded Sierra export validates `163` overlay candidates across `41`
  trade dates from `2026-03-23` through `2026-06-26`.
- Overlay validation passes exactly: `163` expected, `163` actual, `163`
  matched.
- The fixed row produces `-15716` net USD.
- The full exit sweep has no positive row; the best row is still negative.
- The normalized context walk-forward loses `-4640` on selected holdout trades.
- News exclusion removes one losing trade but leaves the result strongly
  negative.

Consequences:

- Do not keep optimizing this exact fixed row as a live or funded candidate.
- Further Delta Impulse work requires a changed hypothesis, not only exit
  parameter tuning.
- Any new variant must pass fresh overlay validation, cost/slippage checks,
  context diagnostics, and chronological walk-forward validation.
