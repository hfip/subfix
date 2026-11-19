import pytest

from subfix.timestamps import (
    format_time,
    normalize_span,
    parse_shift,
    parse_time,
)


def test_parse_time_basic():
    assert parse_time("00:01:02,500") == (62500, 0)


def test_parse_time_accepts_dot_separator():
    assert parse_time("00:01:02.500")[0] == 62500


def test_parse_time_reports_out_of_range_fields():
    milliseconds, issues = parse_time("00:00:75,000")
    assert milliseconds == 75000
    assert issues == 1


def test_parse_time_handles_four_digit_fraction():
    milliseconds, issues = parse_time("00:00:01,1234")
    assert milliseconds == 1123
    assert issues == 1


def test_parse_time_rejects_garbage():
    assert parse_time("not a time") is None


def test_format_time_pads():
    assert format_time(0) == "00:00:00,000"
    assert format_time(3723004) == "01:02:03,004"


def test_format_time_never_negative():
    assert format_time(-500) == "00:00:00,000"


def test_normalize_span_extends_backwards_cue():
    start, end, fixes = normalize_span(5000, 4000)
    assert (start, end) == (5000, 6500)
    assert fixes == 1


def test_normalize_span_keeps_long_cue_untouched():
    assert normalize_span(1000, 9000) == (1000, 9000, 0)


def test_normalize_span_enforces_min_duration():
    start, end, fixes = normalize_span(1000, 1200, min_duration=700)
    assert (start, end) == (1000, 1700)
    assert fixes == 1


@pytest.mark.parametrize(
    "spec, expected",
    [
        ("+1.5s", 1500),
        ("-800ms", -800),
        ("2", 2000),
        ("00:00:02,500", 2500),
    ],
)
def test_parse_shift(spec, expected):
    assert parse_shift(spec) == expected


def test_parse_shift_rejects_empty():
    with pytest.raises(ValueError):
        parse_shift("")
