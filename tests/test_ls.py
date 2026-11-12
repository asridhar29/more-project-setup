"""Tests for the ls tool: listing, sorting, and invalid/unsafe paths."""

from tools.ls import ls


def test_lists_and_sorts_tools_folder():
    result = ls("tools")
    assert result == sorted(result)
    assert "calculate.py" in result
    assert "security.py" in result


def test_default_path_lists_project_root():
    result = ls()
    assert "chat.py" in result
    assert "tools" in result


def test_nonexistent_directory_gives_clear_error():
    result = ls("this_directory_does_not_exist")
    assert result.startswith("Error:")


def test_unsafe_paths_are_rejected():
    assert ls("../").startswith("Error:")
    assert ls("/etc").startswith("Error:")
