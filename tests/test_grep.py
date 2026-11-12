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


def test_missing_files_gives_clear_error():
    result = grep("anything", "no_such_folder/*.py")
    assert result.startswith("Error: no files matched")


def test_glob_pattern_that_escapes_project_is_rejected():
    result = grep("anything", "../*.py")
    assert result == "Error: that path or pattern is not allowed"


def test_skips_directories_matched_by_the_pattern():
    # "test_projects/*" matches the submodule folders themselves
    # (directories), not just files. grep must skip those directories
    # instead of trying to open them as if they were text files.
    result = grep("zzz_text_that_will_never_appear_zzz", "test_projects/*")
    assert result == []


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
