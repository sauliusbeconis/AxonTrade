# Acceptance Gates

A strategy may advance only if all applicable gates pass.

## Research Gates

- Beats a price-only baseline after costs.
- Survives chronological walk-forward testing.
- Has enough trade count to be meaningful.
- Gains are not dominated by one day.
- Nearby parameters remain reasonable.
- Results are reported separately for ES/MES and NQ/MNQ.

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
