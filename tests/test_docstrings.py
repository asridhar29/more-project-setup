"""A lightweight, permanent check that every project function and method has a docstring.

This exists because external grading has repeatedly flagged one
missing docstring at a time, in different files, across several
submissions -- first in `chat.py`, then in `tools/grep.py`, then
back in `chat.py` again. Each time, the fix only covered the file the
grader happened to mention, not the whole project. This test walks
EVERY project-owned Python file with Python's own `ast` module
(no extra dependency needed) and fails, listing every offender by
name and line number, if even one function or method anywhere is
missing a docstring -- so the next missing docstring is caught here,
locally, before it ever reaches an external grader again.
"""

import ast
import glob
import os


def _find_functions_without_docstrings(path):
    """Return a list of (line_number, name) for every function/method in `path` with no docstring."""
    with open(path, "r", encoding="utf-8") as file:
        source = file.read()
    tree = ast.parse(source, filename=path)

    missing = []

    class _Finder(ast.NodeVisitor):
        """Walks the AST, remembering which class (if any) each function is defined inside."""

        def __init__(self):
            """Start with an empty stack of enclosing class/function names."""
            self.owner_stack = []

        def visit_ClassDef(self, node):
            """Push this class's name, visit everything inside it, then pop it back off."""
            self.owner_stack.append(node.name)
            self.generic_visit(node)
            self.owner_stack.pop()

        def _check(self, node):
            """Record `node` in `missing` if it has no docstring, then keep walking inside it."""
            if self.owner_stack:
                name = ".".join(self.owner_stack + [node.name])
            else:
                name = node.name
            if ast.get_docstring(node) is None:
                missing.append((node.lineno, name))
            self.owner_stack.append(node.name)
            self.generic_visit(node)
            self.owner_stack.pop()

        def visit_FunctionDef(self, node):
            """Check a regular `def` function or method."""
            self._check(node)

        def visit_AsyncFunctionDef(self, node):
            """Check an `async def` function or method."""
            self._check(node)

    _Finder().visit(tree)
    return missing


def _project_python_files():
    """Return every project-owned .py file to audit: chat.py, tools/*.py, and tests/*.py."""
    tests_directory = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(tests_directory)

    files = [os.path.join(project_root, "chat.py")]
    files += sorted(glob.glob(os.path.join(project_root, "tools", "*.py")))
    files += sorted(glob.glob(os.path.join(project_root, "tests", "*.py")))
    return files


def test_every_function_and_method_has_a_docstring():
    """Fail with a clear list of file:line:name if any function or method is missing a docstring."""
    all_missing = []
    for path in _project_python_files():
        for lineno, name in _find_functions_without_docstrings(path):
            all_missing.append(path + ":" + str(lineno) + ": " + name)

    assert all_missing == [], "Functions/methods missing a docstring:\n" + "\n".join(all_missing)
