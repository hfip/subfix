from subfix.encoding import (
    arabic_ratio,
    decode_bytes,
    looks_mojibake,
    repair_mojibake,
)

ARABIC_TEXT = "السلام عليكم\nكيف حالك؟"


def test_utf8_passthrough():
    text, encoding, notes = decode_bytes(ARABIC_TEXT.encode("utf-8"))
    assert text == ARABIC_TEXT
    assert encoding == "utf-8"
    assert notes == []


def test_utf8_bom_is_stripped():
    text, encoding, _ = decode_bytes(b"\xef\xbb\xbf" + ARABIC_TEXT.encode("utf-8"))
    assert text == ARABIC_TEXT
    assert encoding == "utf-8"


def test_cp1256_is_decoded():
    text, encoding, notes = decode_bytes(ARABIC_TEXT.encode("cp1256"))
    assert text == ARABIC_TEXT
    assert encoding == "cp1256"
    assert notes


def test_utf16_is_decoded():
    text, encoding, _ = decode_bytes(ARABIC_TEXT.encode("utf-16"))
    assert text == ARABIC_TEXT
    assert encoding == "utf-16"


def test_mojibake_is_repaired():
    broken = ARABIC_TEXT.encode("utf-8").decode("latin-1")
    assert looks_mojibake(broken)
    assert repair_mojibake(broken) == ARABIC_TEXT
    text, encoding, notes = decode_bytes(broken.encode("utf-8"))
    assert text == ARABIC_TEXT
    assert "repaired" in encoding
    assert any("mojibake" in note for note in notes)


def test_mojibake_repaired_through_cp1256():
    broken = ARABIC_TEXT.encode("utf-8").decode("cp1256")
    assert repair_mojibake(broken) == ARABIC_TEXT


def test_crlf_is_normalised():
    text, _, _ = decode_bytes("a\r\nb\rc".encode("utf-8"))
    assert text == "a\nb\nc"


def test_arabic_ratio_ignores_punctuation():
    assert arabic_ratio("مرحبا!!") == 1.0
    assert arabic_ratio("hello") == 0.0
    assert arabic_ratio("") == 0.0


def test_plain_latin_text_is_not_treated_as_mojibake():
    assert not looks_mojibake("Just a normal English subtitle line.")
