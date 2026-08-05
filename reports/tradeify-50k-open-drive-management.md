# Tradeify 50K Opening-Drive Management

Status: second-stage research on the only fresh family that remained broadly positive across the initial chronological split. No NinjaTrader code is included.

## Scope

- source: `67300` MNQ three-minute bars, `2024-07-15` through `2026-07-02`;
- periods: `253` training, `127` validation, `127` later-validation dates;
- the later period is no longer called untouched holdout because family selection used its first-pass result;
- fixed entry neighborhood: aligned 15-minute opening drive, minimum 20-point drive, opening close-location 0.70, then a real pullback and resumption;
- management search: partial target, protected runner, conservative stop-first bar handling, one trade per day;
- evaluated rows: `2304`.

## Top Robust Rows

| Rank | Split | T1 / Stop / Runner / BE | Trades | /Wk | Net | PF | Win | T1 Hit | Runner Hit | DD | Period PFs | Windows | Worst Window |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |

## Frozen Result

No scale-out profile cleared the stability gates. The opening-drive family remains rejected for a production bot.
