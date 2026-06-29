# Signal Log Rejection Reasons

Manual help needed: **No**.

This is the canonical rejected-signal vocabulary for AxonTrade research logs.
The executable source is:

`config/research/rejection_reason_codes.yaml`

The signal-log schema imports the same catalog through:

`config/research/signal_log_schema.yaml`

## Reason Codes

| Code | Meaning |
| --- | --- |
| `not_applicable` | No rejection was applied. Use this on accepted candidate rows and marker rows. |
| `no_setup` | The strategy pattern was not present on the evaluated bar. |
| `outside_session` | The bar was outside the configured trading or setup window. |
| `insufficient_context` | Required prior bars, opening range, or level context was missing. |
| `risk_limit` | Candidate geometry or account rules violated a configured risk limit. |
| `news_blackout` | The bar was inside a scheduled-news exclusion window. |
| `duplicate_signal` | An equivalent signal was already emitted for the configured scope. |
| `manual_review_required` | The bar matched conflicting states and should not be auto-classified. |
| `no_absorption` | Price swept a reference level but the absorption condition was absent. |
| `daily_limit` | The strategy already emitted the maximum configured signals for the day. |
| `spacing_filter` | The bar occurred too soon after the prior accepted strategy signal. |
| `configuration_error` | The study or strategy inputs are invalid for signal generation. |
| `other` | Fallback only when a more specific code does not exist yet. |

## Rejected Row Fields

A `rejected_signal` row must carry enough context to explain why no candidate
was emitted:

- `schema_version`
- `event_key`
- `event_type`
- `generated_at`
- `symbol`
- `chart_number`
- `bar_index`
- `bar_start_time`
- `trade_mode`
- `strategy_id`
- `signal_id`
- `direction`
- `action`
- `signal_price`
- `rejection_reason`
- `notes`

For rejected rows, `event_type` must be `rejected_signal`, `action` must be
`reject`, and `rejection_reason` must be one of the catalog codes. `notes`
should include the failed threshold, missing context, or pacing condition.

`stop_price`, `target_price`, and `invalidation_price` should be blank when
they are not applicable to the rejection.

## Validation

Manual help needed: **No**.

Run the repo check from the project directory:

```bash
PYTHON=.venv/bin/python bash scripts/check_repo.sh
```

The validator rejects logs with unknown reason codes. It also rejects a signal
schema whose `rejection_reasons` list drifts away from the canonical catalog.
