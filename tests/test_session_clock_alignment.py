from __future__ import annotations

from axontrade.research import (
    SESSION_CLOCK_ALIGNMENT_HEADER,
    run_session_clock_alignment_diagnostics,
)


def test_session_clock_alignment_reports_open_and_local_time() -> None:
    rows = run_session_clock_alignment_diagnostics(
        [
            {
                "Date": "2026-06-19",
                "Time": "09:30:00.000000",
                "Volume": "100",
                "# of Trades": "50",
            },
            {
                "Date": "2026-06-19",
                "Time": "09:35:00.000000",
                "Volume": "25",
                "# of Trades": "20",
            },
            {
                "Date": "2026-06-19",
                "Time": "16:14:00.000000",
                "Volume": "10",
                "# of Trades": "8",
            },
        ],
    )

    assert list(rows[0].keys()) == SESSION_CLOCK_ALIGNMENT_HEADER
    assert rows[0]["trade_date"] == "2026-06-19"
    assert rows[0]["expected_session_start_time"] == "09:30:00 EDT"
    assert rows[0]["expected_local_session_start_time"] == "16:30:00 EEST"
    assert rows[0]["ny_dst_active"] == "true"
    assert rows[0]["first_bar_delay_seconds"] == "0"
    assert rows[0]["check_time_rows"] == 0
    assert rows[0]["session_start_5m_volume_rank"] == 1


def test_session_clock_alignment_counts_check_time_rows() -> None:
    rows = run_session_clock_alignment_diagnostics(
        [
            {
                "Date Time": "2026-06-19 09:30:00",
                "Volume": "100",
                "Trades": "50",
            },
            {
                "Date Time": "2026-06-19 16:30:00",
                "Volume": "10",
                "Trades": "8",
            },
        ],
    )

    assert rows[0]["check_time"] == "16:30:00"
    assert rows[0]["check_time_rows"] == 1
    assert rows[0]["notes"] == "rows exist at check time; inspect session/end-time settings"
