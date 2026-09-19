from __future__ import annotations

from audioextract.progress import parse_timestamp, progress_from_record


def test_parse_timestamp() -> None:
    assert parse_timestamp("00:01:02.500000") == 62.5
    assert parse_timestamp("not-a-time") is None


def test_progress_percent_is_bounded() -> None:
    update = progress_from_record(
        {"out_time": "00:00:05.000000", "speed": "2x", "progress": "continue"},
        10.0,
    )
    assert update.percent == 50.0
    assert update.speed == "2x"
