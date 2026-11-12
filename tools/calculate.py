r"""The `calculate` tool: safely evaluates a basic math expression.

We want the chatbot to be able to do arithmetic for the user, like
"what is 12 * 7?". The tricky part is that Python's built-in `eval()`
function can run ANY Python code, not just math -- if we fed user text
straight into `eval()`, someone could type something like
``__import__('os').system('delete everything')`` and it would actually
run. That would be a huge security hole.

To stay safe, we do two things before we ever call `eval()`:

1. We check the expression character-by-character and reject it if it
   contains anything other than digits, spaces, decimal points,
   parentheses, and the arithmetic operators ``+ - * / ** ( )``. This
   means things like letters, underscores, or brackets can never appear,
   which blocks tricks like ``__import__`` from ever reaching `eval()`.
2. We call `eval()` with its "built-ins" turned off, using an empty
   dictionary for `__builtins__`. This disables ALL of Python's normal
   built-in functions (`open`, `__import__`, `print`, etc.) during the
   `eval()` call, so even if something slipped past step 1, it would
   have no dangerous functions available to call.

Together, these two layers mean `eval()` can only ever compute plain
arithmetic -- nothing else.
"""

# The only characters we will accept in a math expression. Anything
# else causes us to reject the expression before it gets near eval().
ALLOWED_CHARACTERS = "0123456789+-*/(). "


def _expression_contains_only_safe_characters(expression):
    """Return True if every character in `expression` is allowed.

    This is a small helper used only inside this file, which is why its
    name starts with an underscore (a Python convention meaning "this is
    an internal detail, not meant to be used by other files").

    >>> _expression_contains_only_safe_characters("5 + 3")
    True
    >>> _expression_contains_only_safe_characters("2 ** 3")
    True
    >>> _expression_contains_only_safe_characters("import os")
    False
    """
    for character in expression:
        if character not in ALLOWED_CHARACTERS:
            return False
    return True


def calculate(expression):
    r"""Safely evaluate a basic arithmetic expression and return the result.

    Supports addition, subtraction, multiplication, division,
    exponentiation (``**``), and parentheses for grouping.

    >>> calculate("5 + 3")
    8
    >>> calculate("10 * 4")
    40
    >>> calculate("(20 + 5) / 5")
    5.0
    >>> calculate("2 ** 3")
    8
    >>> calculate("import os")
    'Error: expression contains characters that are not allowed'
    >>> calculate("1 / 0")
    'Error: division by zero'
    >>> calculate("2 +")
    'Error: could not evaluate that expression'
    """
    # Step 1: reject anything with characters we did not explicitly
    # approve. This is our first and most important line of defense.
    if not _expression_contains_only_safe_characters(expression):
        return "Error: expression contains characters that are not allowed"

    # Step 2: even though the characters are safe, make sure Python's
    # eval() has no access to built-in functions like open() or
    # __import__(). Passing an empty dict as "__builtins__" strips all
    # of that away, so eval() can only do arithmetic with the numbers
    # and operators already in the expression.
    restricted_globals = {"__builtins__": {}}

    try:
        result = eval(expression, restricted_globals)
    except ZeroDivisionError:
        return "Error: division by zero"
    except Exception:
        # Any other problem (bad syntax, empty expression, etc.) gets
        # turned into one clear, friendly error message instead of a
        # scary Python traceback.
        return "Error: could not evaluate that expression"

    return result
