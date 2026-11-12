"""Tests for the shared path-safety helper in tools/security.py.

These go beyond the doctests in security.py itself to cover more edge
cases: paths that try to escape the project through glob patterns, and
a Windows-specific gotcha where a path like "/etc/passwd" is not
flagged as "absolute" by Python's own os.path.isabs().
"""

from tools.security import is_path_safe, safe_glob_pattern_is_allowed


def test_relative_path_inside_project_is_safe():
    """Check that ordinary relative paths inside the project are accepted."""
    assert is_path_safe("chat.py") is True
    assert is_path_safe("tools/calculate.py") is True
    assert is_path_safe(".") is True


def test_absolute_path_is_rejected():
    """Check that absolute paths (with or without a drive letter) are rejected."""
    assert is_path_safe("/etc/passwd") is False
    assert is_path_safe("C:/Windows/System32") is False


def test_drive_relative_windows_path_is_rejected():
    """Check that Windows drive-relative paths (no drive letter, but still absolute-like) are rejected."""
    # On Windows, a path starting with "/" or "\" but with no drive
    # letter is NOT considered absolute by os.path.isabs(), even
    # though it behaves like "jump to the root of the current drive"
    # when combined with another path. Our helper must catch this
    # anyway.
    assert is_path_safe("/etc/passwd") is False
    assert is_path_safe("\\windows\\system32") is False


def test_dot_dot_anywhere_in_path_is_rejected():
    """Check that ".." anywhere in a path is rejected, not just at the start."""
    assert is_path_safe("../secret.txt") is False
    assert is_path_safe("tools/../../secret.txt") is False
    assert is_path_safe("tools/../chat.py") is False


def test_glob_pattern_that_escapes_project_is_rejected():
    """Check that glob patterns using ".." or an absolute path are rejected, unlike safe ones."""
    assert safe_glob_pattern_is_allowed("tools/*.py") is True
    assert safe_glob_pattern_is_allowed("../*.py") is False
    assert safe_glob_pattern_is_allowed("/*.py") is False
    assert safe_glob_pattern_is_allowed("tools/../../*.py") is False


def test_glob_pattern_with_drive_letter_is_rejected():
    """Check that a glob pattern with a Windows drive letter is rejected as absolute."""
    assert safe_glob_pattern_is_allowed("C:/Windows/*.py") is False
