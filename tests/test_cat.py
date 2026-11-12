"""Tests for the cat tool: reading files, encodings, missing files, unsafe paths."""

from tools.cat import cat


def test_reads_utf8_file():
    """Check that a plain UTF-8 text file is read and its contents returned.

    >>> test_reads_utf8_file()
    """
    contents = cat("tools/__init__.py")
    assert "tools package" in contents


def test_reads_utf16_file():
    """Check that a UTF-16 encoded file is decoded correctly, not misread as UTF-8.

    >>> test_reads_utf16_file()
    """
    contents = cat("tests/fixtures/utf16_sample.txt")
    assert contents == "Hello from a UTF-16 file!"


def test_unsupported_encoding_gives_clear_error():
    """Check that a file with no readable text encoding returns a clear error, not a crash.

    >>> test_unsupported_encoding_gives_clear_error()
    """
    result = cat("tests/fixtures/undecodable.bin")
    assert result.startswith("Error:")
    assert "encoding" in result


def test_missing_file_gives_clear_error():
    """Check that reading a nonexistent file returns a clear error message.

    >>> test_missing_file_gives_clear_error()
    """
    result = cat("no_such_file.txt")
    assert result == "Error: no such file: no_such_file.txt"


def test_unsafe_paths_are_rejected():
    """Check that paths outside the project (via .. or an absolute path) are rejected.

    >>> test_unsafe_paths_are_rejected()
    """
    assert cat("../secret.txt") == "Error: that path is not allowed"
    assert cat("/etc/passwd") == "Error: that path is not allowed"
