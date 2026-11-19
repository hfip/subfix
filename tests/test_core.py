from subfix.bidi import add_rtl_marks, needs_rtl_mark, strip_marks
from subfix.core import FixOptions, fix_text, parse_srt, serialize_srt


def make_cue(index, start, end, text):
    return "%d\n%s --> %s\n%s" % (index, start, end, text)


def test_parse_srt_reads_cues():
    content = make_cue(1, "00:00:01,000", "00:00:03,000", "مرحبا") + "\n\n"
    cues = parse_srt(content)
    assert len(cues) == 1
    assert cues[0].start == 1000
    assert cues[0].text == "مرحبا"


def test_parse_srt_tolerates_missing_index():
    content = "00:00:01,000 --> 00:00:03,000\nمرحبا\n"
    cues = parse_srt(content)
    assert len(cues) == 1
    assert cues[0].end == 3000


def test_parse_srt_keeps_multiline_text_and_styles():
    content = make_cue(1, "00:00:01,000", "00:00:03,000", "<i>مرحبا</i>\nبك")
    cues = parse_srt(content)
    assert cues[0].text == "<i>مرحبا</i>\nبك"


def test_parse_srt_returns_nothing_for_plain_text():
    assert parse_srt("just some text\nwith no timings") == []


def test_serialize_renumbers_from_one():
    cues = parse_srt(make_cue(7, "00:00:01,000", "00:00:03,000", "مرحبا"))
    assert serialize_srt(cues).startswith("1\n00:00:01,000 --> 00:00:03,000")


def test_fix_text_renumbers_and_normalises():
    content = make_cue(42, "00:00:01.000", "00:00:03.000", "مرحبا  ") + "\n\n\n"
    result = fix_text(content)
    assert result.cues_before == 1
    assert result.text == "1\n00:00:01,000 --> 00:00:03,000\nمرحبا\n"


def test_fix_text_drops_empty_cues():
    content = (
        make_cue(1, "00:00:01,000", "00:00:03,000", "مرحبا")
        + "\n\n"
        + make_cue(2, "00:00:04,000", "00:00:06,000", "   ")
    )
    result = fix_text(content)
    assert result.empty_removed == 1
    assert result.cues_after == 1


def test_fix_text_fixes_broken_timing():
    content = make_cue(1, "00:00:05,000", "00:00:04,000", "مرحبا")
    result = fix_text(content)
    assert result.timing_fixed == 1
    assert "00:00:05,000 --> 00:00:06,500" in result.text


def test_fix_text_shifts_all_cues():
    content = make_cue(1, "00:00:05,000", "00:00:07,000", "مرحبا")
    result = fix_text(content, FixOptions(shift_ms=-2000))
    assert "00:00:03,000 --> 00:00:05,000" in result.text


def test_fix_text_never_produces_negative_timings():
    content = make_cue(1, "00:00:01,000", "00:00:03,000", "مرحبا")
    result = fix_text(content, FixOptions(shift_ms=-5000))
    assert result.text.startswith("1\n00:00:00,000")


def test_fix_text_sorts_out_of_order_cues():
    content = (
        make_cue(1, "00:00:10,000", "00:00:12,000", "الثانية")
        + "\n\n"
        + make_cue(2, "00:00:01,000", "00:00:03,000", "الأولى")
    )
    result = fix_text(content)
    assert result.sorted is True
    assert result.text.index("الأولى") < result.text.index("الثانية")


def test_ad_lines_are_removed_at_the_edges():
    content = (
        make_cue(1, "00:00:01,000", "00:00:03,000", "شاهدونا على تليجرام")
        + "\n\n"
        + make_cue(2, "00:00:04,000", "00:00:06,000", "لا تنسى الاشتراك في القناة")
        + "\n\n"
        + make_cue(3, "00:00:07,000", "00:00:09,000", "حوار حقيقي")
    )
    result = fix_text(content)
    assert result.ads_removed == 2
    assert "حوار حقيقي" in result.text
    assert result.cues_after == 1


def test_weak_credit_is_kept_in_the_middle():
    content = ""
    for index in range(1, 9):
        text = "ترجمة: أحمد" if index == 4 else "حوار رقم %d" % index
        content += make_cue(
            index, "00:00:%02d,000" % (index * 5), "00:00:%02d,000" % (index * 5 + 2), text
        )
        content += "\n\n"
    result = fix_text(content)
    assert "ترجمة: أحمد" in result.text


def test_ads_can_be_kept():
    content = make_cue(1, "00:00:01,000", "00:00:03,000", "www.example.com")
    result = fix_text(content, FixOptions(remove_ads=False))
    assert "www.example.com" in result.text


def test_bidi_marks_are_stripped():
    content = make_cue(1, "00:00:01,000", "00:00:03,000", "\u200fمرحبا\u200e")
    result = fix_text(content)
    assert "\u200e" not in result.text
    assert "\u200f" not in result.text


def test_rtl_mark_added_for_latin_initial_line():
    content = make_cue(1, "00:00:01,000", "00:00:03,000", "iPhone الجديد")
    result = fix_text(content)
    assert result.rtl_marked == 1
    assert "\u200fiPhone" in result.text


def test_rtl_mark_not_added_for_arabic_line():
    content = make_cue(1, "00:00:01,000", "00:00:03,000", "السلام عليكم")
    result = fix_text(content)
    assert result.rtl_marked == 0


def test_needs_rtl_mark_helpers():
    assert needs_rtl_mark("2019 كان عاما") is False
    assert needs_rtl_mark("iPhone جديد") is True
    assert needs_rtl_mark("no arabic here") is False


def test_add_rtl_marks_keeps_indentation():
    marked, count = add_rtl_marks("  iPhone الجديد")
    assert count == 1
    assert marked.startswith("  \u200f")


def test_strip_marks_removes_controls():
    assert strip_marks("a\u200fb\u202ec") == "abc"


def test_fix_text_returns_empty_result_for_non_srt():
    result = fix_text("hello")
    assert result.cues_before == 0
    assert result.text == ""
