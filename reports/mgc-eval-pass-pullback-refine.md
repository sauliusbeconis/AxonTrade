# MGC Eval-Pass Pullback Refinement

Status: rejected as a standalone eval-pass candidate.

This follow-up reviewed the promising MGC pullback rows from
`reports/mgc-eval-pass-initial-scan.md`.

## Starting Point

The initial scan found two useful but incomplete shapes:

- frequent breakout rows can pass often, but fail too often;
- VWAP pullback rows can keep calendar-start fail low, but do not pass often
  enough and still have high signal-start failure.

## Targeted Filters Checked

The refinement focused on the best MGC VWAP pullback families:

- `stretch15 / pb2`, early `08:20-10:30` entries;
- `stretch25 / pb2`, entries through `13:30`;
- `stretch25 / pb5`, entries through `13:30`;
- Friday and non-Friday variants.

Simple context filters were checked:

- opening-range width;
- day range at entry;
- signal bar range;
- directional distance from VWAP;
- directional distance from the active-session open.

## Best Useful Rows

Best low-fail / higher-pass pullback refinement:

| Metric | Value |
| --- | ---: |
| Strategy | `mgc_vwap_pullback:stretch25:pb5:delta0:cl0.55:end1330:skipfri0:filteror7_28+barle5.9` |
| Quantity | `10` MGC |
| Target / stop | `$650 / $800` |
| Trades | `69` |
| Latest-year net | `$2880` |
| Full-sample net | `$11080` |
| Calendar-start pass / fail | `26.1% / 6.6%` |
| Signal-start pass / fail | `69.6% / 23.2%` |
| Signal-start two-day pass | `43.5%` |
| Median signal gap | `5` calendar days |
| Worst quarter | `-$800` |
| Trade-sequence max DD | `-$3350` |

Best higher signal-start pass row:

| Metric | Value |
| --- | ---: |
| Strategy | `mgc_vwap_pullback:stretch25:pb2:delta0:cl0.55:end1330:skipfri0:filterbarle5.9` |
| Quantity | `12` MGC |
| Target / stop | `$660 / $648` |
| Trades | `66` |
| Latest-year net | `$2172` |
| Full-sample net | `$5100` |
| Calendar-start pass / fail | `24.8% / 7.6%` |
| Signal-start pass / fail | `71.2% / 24.2%` |
| Signal-start two-day pass | `31.8%` |
| Median signal gap | `5` calendar days |
| Worst quarter | `-$1824` |
| Trade-sequence max DD | `-$5832` |

Best lower-risk early pullback row:

| Metric | Value |
| --- | ---: |
| Strategy | `mgc_vwap_pullback:stretch15:pb2:delta0:cl0.55:end1030:skipfri0:filterdayle40` |
| Quantity | `5` MGC |
| Target / stop | `$625 / $500` |
| Trades | `90` |
| Latest-year net | `$1875` |
| Full-sample net | `$5380` |
| Calendar-start pass / fail | `18.4% / 6.2%` |
| Signal-start pass / fail | `60.0% / 16.7%` |
| Signal-start two-day pass | `17.8%` |
| Median signal gap | `7` calendar days |
| Worst quarter | `-$935` |
| Trade-sequence max DD | `-$3000` |

## Rejection Notes

No refined MGC pullback row met the current eval-pass bar:

- no row met `calendar-start pass >= 30%` and `fail <= 15%`;
- no row had `signal-start fail <= 20%` with positive full-sample and
  latest-year net;
- no positive row kept trade-sequence drawdown inside `-$1500`.

MGC remains usable data, but this first continuation/pullback idea is not a
current implementation candidate.
