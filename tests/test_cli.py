import json

from subfix.cli import main

ARABIC = "السلام عليكم"


def write_srt(path, text=ARABIC, encoding="cp1256"):
    content = "1\n00:00:01,000 --> 00:00:03,000\n%s\n" % text
    path.write_bytes(content.encode(encoding))
    return path


def test_cli_fixes_file_and_writes_backup(tmp_path):
    srt = write_srt(tmp_path / "movie.srt")
    assert main([str(srt)]) == 0

    assert ARABIC in srt.read_text(encoding="utf-8")
    assert (tmp_path / "movie.srt.bak").exists()


def test_cli_dry_run_does_not_write(tmp_path, capsys):
    srt = write_srt(tmp_path / "movie.srt")
    original = srt.read_bytes()
    assert main(["-n", str(srt)]) == 0

    assert srt.read_bytes() == original
    assert not (tmp_path / "movie.srt.bak").exists()
    assert "would fix" in capsys.readouterr().out


def test_cli_check_exits_one_when_fix_needed(tmp_path):
    srt = write_srt(tmp_path / "movie.srt")
    assert main(["--check", str(srt)]) == 1


def test_cli_check_exits_zero_when_clean(tmp_path):
    srt = write_srt(tmp_path / "clean.srt", encoding="utf-8")
    assert main([str(srt)]) == 0
    assert main(["--check", str(srt)]) == 0


def test_cli_json_output(tmp_path, capsys):
    srt = write_srt(tmp_path / "movie.srt")
    assert main(["--json", str(srt)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["total"] == 1
    assert payload["summary"]["changed"] == 1
    assert payload["files"][0]["path"].endswith("movie.srt")


def test_cli_directory_scan(tmp_path):
    write_srt(tmp_path / "a.srt")
    write_srt(tmp_path / "b.srt")
    (tmp_path / "notes.txt").write_text("skip me", encoding="utf-8")
    assert main([str(tmp_path)]) == 0
    assert "السلام عليكم" in (tmp_path / "a.srt").read_text(encoding="utf-8")


def test_cli_recursive_scan(tmp_path):
    nested = tmp_path / "sub"
    nested.mkdir()
    write_srt(nested / "deep.srt")
    assert main([str(tmp_path)]) == 2
    assert main(["-r", str(tmp_path)]) == 0


def test_cli_missing_path_exits_two(tmp_path):
    assert main([str(tmp_path / "nope.srt")]) == 2


def test_cli_rejects_non_srt_content(tmp_path):
    bad = tmp_path / "bad.srt"
    bad.write_text("no timings here", encoding="utf-8")
    assert main([str(bad)]) == 2


def test_cli_no_backup(tmp_path):
    srt = write_srt(tmp_path / "movie.srt")
    assert main(["--no-backup", str(srt)]) == 0
    assert not (tmp_path / "movie.srt.bak").exists()


def test_cli_shift_option(tmp_path):
    srt = write_srt(tmp_path / "movie.srt", encoding="utf-8")
    assert main(["--shift", "+2s", str(srt)]) == 0
    assert "00:00:03,000 --> 00:00:05,000" in srt.read_text(encoding="utf-8")


def test_cli_bad_shift_exits_two(tmp_path):
    srt = write_srt(tmp_path / "movie.srt")
    assert main(["--shift", "abc", str(srt)]) == 2


def test_cli_refuses_file_with_unparsed_block(tmp_path):
    path = tmp_path / "broken.srt"
    original = "1\n00:00:01,000 --> 00:00:03,000\nمرحبا\n\n2\n00:00:04,000 -> 00:00:06,000\nثاني\n"
    path.write_text(original, encoding="utf-8")
    assert main([str(path)]) == 2
    assert path.read_text(encoding="utf-8") == original


def test_cli_keeps_five_digit_fractions(tmp_path):
    path = tmp_path / "odd.srt"
    path.write_text("1\n00:00:01,12345 --> 00:00:03,000\nمرحبا\n", encoding="utf-8")
    assert main([str(path)]) == 0
    assert "00:00:01,123 -->" in path.read_text(encoding="utf-8")
