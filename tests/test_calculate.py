"""Tests for the calculate tool, focused on invalid/unsafe expressions."""

from tools.calculate import calculate


def test_valid_expressions():
    """Check that basic arithmetic (+, *, /, **) and parentheses return the correct numeric result.

    This test takes no arguments and only uses plain `assert` statements,
    so calling it directly runs every check below and prints nothing at
    all if they all pass -- exactly what a doctest with no expected
    output after it checks for:

    >>> test_valid_expressions()
    """
    assert calculate("5 + 3") == 8
    assert calculate("10 * 4") == 40
    assert calculate("(20 + 5) / 5") == 5.0
    assert calculate("2 ** 3") == 8


def test_rejects_letters_and_code_injection_attempts():
    """Check that expressions containing letters or function calls are rejected, never executed.

    >>> test_rejects_letters_and_code_injection_attempts()
    """
    result = calculate("__import__('os').system('echo hi')")
    assert result.startswith("Error:")

    result = calculate("open('secret.txt')")
    assert result.startswith("Error:")


def test_rejects_empty_or_malformed_expression():
    """Check that empty, incomplete, or syntactically invalid expressions return an error.

    >>> test_rejects_empty_or_malformed_expression()
    """
    assert calculate("").startswith("Error:")
    assert calculate("2 +").startswith("Error:")
    assert calculate("5 3").startswith("Error:")
    assert calculate("(2 + 3").startswith("Error:")


def test_division_by_zero_gives_friendly_error():
    """Check that dividing by zero returns a clear error message instead of crashing.

    >>> test_division_by_zero_gives_friendly_error()
    """
    assert calculate("1 / 0") == "Error: division by zero"
