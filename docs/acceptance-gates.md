# Acceptance Gates

A strategy may advance only if all applicable gates pass.

## Research Gates

- Beats a price-only baseline after costs.
- Survives chronological walk-forward testing.
- Has enough trade count to be meaningful.
- Gains are not dominated by one day.
- Nearby parameters remain reasonable.
- Results are reported separately for ES/MES and NQ/MNQ.

The current price-only ES baseline has a concrete executable gate profile in
`config/research/price_only_acceptance_gates.yaml`.

Current thresholds:

- at least `100` evaluated outcome trades;
- at least `20` distinct trade dates;
- at least `30` selected walk-forward holdout trades;
- selected walk-forward holdout net must be positive after configured costs;
- the single train-selected holdout row must contain at least `10` trades;
- the worst losing day must be no more than `40%` of total losing-day loss.

Run the check from the repository:

```bash
.venv/bin/python scripts/check_price_only_acceptance.py
```

The command writes `reports/price-only-acceptance-sample.md`. By default it
returns exit code `0` even when the research sample fails, because a rejection is
a valid research result. Add `--fail-on-reject` when a CI-style nonzero failure
is desired.

## Risk Gates

- Average holding time is comfortably above microscalping thresholds.
- Max drawdown is well below the LucidFlex max loss.
- Risk limits are stricter than firm limits during development.
- No rule violates prop-firm restrictions.

## Platform Gates

- Sierra Chart replay behavior is stable.
- Recalculation does not duplicate drawings.
- Recalculation does not duplicate event rows.
- Forward simulation matches expectations.

## Live-Routing Gate

Live routing remains disabled until a future explicit safety phase authorizes it.
