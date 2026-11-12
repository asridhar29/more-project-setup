"""Tests for the grep tool: matching, empty results, bad regex, unsafe patterns."""

from tools.grep import grep


def test_finds_matching_lines_with_filename_and_line_number():
    results = grep("def calculate", "tools/calculate.py")
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0].startswith("tools/calculate.py:")
    # format is "path:line_number:line_text"
    pieces = results[0].split(":", 2)
    assert pieces[0] == "tools/calculate.py"
    assert pieces[1].isdigit()


def test_no_matches_returns_empty_list():
    result = grep("zzz_text_that_will_never_appear_zzz", "tools/calculate.py")
    assert result == []


def test_invalid_regex_gives_clear_error():
    result = grep("(unclosed", "tools/*.py")
    assert result == "Error: invalid regular expression"


def test_pattern_matching_zero_files_returns_empty_list():
    # A valid, safe glob pattern that simply matches nothing (the
    # folder does not exist at all) is not an error -- it just means
    # there was nothing to search.
    result = grep("anything", "no_such_folder/*.py")
    assert result == []


def test_pattern_matching_zero_files_returns_empty_list_even_when_mocked():
    # Same guarantee as above, but independent of anything on disk:
    # if glob.glob() itself returns an empty list for any reason, grep
    # must return [] too, never an error string.
    from unittest.mock import patch

    with patch("glob.glob", return_value=[]):
        result = grep("anything", "some/pattern/*.py")
    assert result == []


def test_glob_pattern_that_escapes_project_is_rejected():
    result = grep("anything", "../*.py")
    assert result == "Error: that path or pattern is not allowed"


def test_skips_directories_matched_by_the_pattern():
    # "test_projects/*" matches the submodule folders themselves
    # (directories), not just files. grep must skip those directories
    # instead of trying to open them as if they were text files.
    result = grep("zzz_text_that_will_never_appear_zzz", "test_projects/*")
    assert result == []


def test_valid_pattern_matching_only_directories_returns_empty_list():
    # Regression test for the exact call that previous reports were
    # ambiguous about: a valid glob pattern ("test_projects/*") that
    # matches only directories, not files, must return an empty list,
    # not an error string.
    assert grep("anything", "test_projects/*") == []


def test_does_not_crash_on_undecodable_file():
    # The pattern below matches both a normal text file and an
    # undecodable binary file in the fixtures folder. grep should skip
    # the binary one without crashing and still find the text match.
    results = grep("Hello", "tests/fixtures/*")
    assert isinstance(results, list)

    found_the_text_file = False
    for line in results:
        if "utf16_sample.txt" in line:
            found_the_text_file = True
    assert found_the_text_file is True


def test_does_not_crash_on_file_with_no_bom_and_invalid_utf8():
    # This file's bytes are invalid UTF-8 and do NOT start with any
    # byte-order mark at all. Trying to blindly decode it as UTF-16
    # (without first checking for a BOM) would raise a confusing
    # "stream does not start with BOM" error -- grep must never do
    # that, and should just skip the file cleanly instead.
    result = grep("anything", "tests/fixtures/no_bom_binary.bin")
    assert result == []


def test_reads_utf8_file_with_bom():
    results = grep("byte-order mark", "tests/fixtures/utf8_bom_sample.txt")
    assert len(results) == 1
    assert results[0] == "tests/fixtures/utf8_bom_sample.txt:1:This file has a UTF-8 byte-order mark."


def test_reads_utf16_big_endian_file_with_bom():
    results = grep("big-endian", "tests/fixtures/utf16_be_sample.txt")
    assert len(results) == 1
    assert results[0] == "tests/fixtures/utf16_be_sample.txt:1:Hello from UTF-16 big-endian!"


def test_reads_legacy_cp1252_file_with_no_bom():
    # This file is not valid UTF-8 and has no BOM at all, but it IS a
    # real, legitimate text file (saved in an older Windows encoding).
    # grep must still read it, not silently skip it just because it
    # isn't UTF-8.
    results = grep("legacy Windows encoding", "tests/fixtures/cp1252_sample.txt")
    assert len(results) == 1
    assert results[0].startswith("tests/fixtures/cp1252_sample.txt:1:")


def test_skips_genuinely_binary_files_even_without_a_null_byte_shortcut():
    # pixel.png has no BOM and is not valid UTF-8, but it DOES contain
    # a null byte, which is what correctly marks it as binary (as
    # opposed to a legacy-encoded text file like cp1252_sample.txt,
    # which has no null byte and so is read as real text instead).
    result = grep("anything", "tests/fixtures/pixel.png")
    assert result == []


def test_matches_across_multiple_files():
    results = grep("is_path_safe", "tools/*.py")
    files_matched = set()
    for line in results:
        files_matched.add(line.split(":")[0])
    assert len(files_matched) >= 3
