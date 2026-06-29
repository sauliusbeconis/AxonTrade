# LucidFlex 25k Rule Audit

Source retrieval date: `2026-06-29`.

Manual help needed: **No**.

This audit compares official Lucid Trading sources against
`config/firms/lucidflex_25k_evaluation.yaml`. It is a research control only;
rules must be rechecked before any funded or live trading decision.

## Comparison

| Rule | Config | Official source check | Status |
| --- | --- | --- | --- |
| Account type | `LucidFlex`, evaluation | LucidFlex evaluation is a simulated account with a profit target before funded upgrade. | Match |
| Account size | `$25,000` | 25k Flex row is listed. | Match |
| Profit target | `$1,250` | 25k Flex profit target is `$1,250`. | Match |
| Max loss limit | `$1,000` | 25k Flex MLL amount is `$1,000`. | Match |
| Drawdown type | `end_of_day_trailing` | LucidFlex uses EOD Drawdown for MLL. | Match |
| Daily loss limit | `null` | Lucid says there is no DLL on LucidFlex evaluation accounts. | Match |
| Consistency | `50%` | LucidFlex evaluation requires consistency percentage of `50%` or less. | Match |
| Max size | `2` minis or `20` micros | 25k Flex max size is `2 mini or 20 micros`. | Match |
| Scaling plan | no evaluation scaling field | Lucid says the LucidFlex scaling plan does not apply during evaluation. | Match |
| Official flat time | `16:45 America/New_York` | LucidPro, LucidFlex, and LucidDirect positions must be closed by `4:45 PM EST`; Lucid auto-closes then. | Match |
| Internal entry cutoff | `16:35 America/New_York` | Not a published Lucid rule. | Local stricter safety buffer |
| Internal forced flatten | `16:40 America/New_York` | Not a published Lucid rule. | Local stricter safety buffer |
| Automated strategies | `true` | Lucid permits automated trading systems and trade copiers if they comply with all rules. | Match |
| HFT | `false` | Lucid prohibits high-frequency trading and may remove profits/close accounts for repeat offenses. | Match |
| Microscalping | `false` | Lucid prohibits microscalping; accounts may be flagged when more than 50% of profits come from trades held 5 seconds or less. | Match |
| Genuine scalping | no explicit config field | Lucid permits genuine scalping if activity reflects realistic execution and stays within microscalping rules. | Documented gap |

## Bot Implications

- Keep `live_automated_entries_enabled: false` until there is a separate live
  approval gate.
- Keep `microscalping_allowed: false`; strategy research should reject edges
  that rely on trades held `5` seconds or less.
- Keep HFT prohibited; avoid high order volume, millisecond execution patterns,
  and strategies that depend on simulated-fill exploitation.
- Keep the internal `16:35` no-new-entry and `16:40` forced-flatten buffers
  because they reduce operational risk before Lucid's `16:45` cutoff.
- Treat news trading as allowed but still stress-test slippage and volatility.

## Sources

- LucidFlex Evaluation Account:
  https://support.lucidtrading.com/en/articles/12945790-lucidflex-evaluation-account
- LucidFlex Drawdown:
  https://support.lucidtrading.com/en/articles/12945815-lucidflex-drawdown
- LucidFlex Consistency Percentage:
  https://support.lucidtrading.com/en/articles/12945805-lucidflex-consistency-percentage
- LucidFlex Scaling Plan:
  https://support.lucidtrading.com/en/articles/12945808-lucidflex-scaling-plan
- Allowed Trading Times:
  https://support.lucidtrading.com/en/articles/11404729-allowed-trading-times
- Permitted Activities:
  https://support.lucidtrading.com/en/articles/11404728-permitted-activities
- Prohibited High Frequency Trading:
  https://support.lucidtrading.com/en/articles/11404736-prohibited-high-frequency-trading
- Prohibited Microscalping:
  https://support.lucidtrading.com/en/articles/11404742-prohibited-microscalping
