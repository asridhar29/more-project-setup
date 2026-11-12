r"""The `grep` tool: searches for a pattern inside one or more files.

"grep" is another classic Unix command name. It searches through text
files line by line, looking for lines that match a pattern, and prints
out each matching line along with which file and line number it came
from.

Two concepts worth explaining if you have not seen them before:

- A "glob pattern" (from the `glob` module) is a filename pattern with
  wildcards, like ``tools/*.py``, which matches every ``.py`` file
  directly inside the `tools` folder. We use glob here to let the
  caller search many files at once instead of just one.
- A "regular expression" (often shortened to "regex") is a tiny
  pattern language for describing text to search for -- more powerful
  than a plain substring search. For example, the regex ``"def "``
  matches the literal text "def " anywhere in a line, while a fancier
  regex like ``"^def "`` means "only match if 'def ' is at the very
  start of the line". Python's `re` module understands this pattern
  language.
"""

import glob
import os
import re

from tools.security import get_project_directory, is_path_safe, safe_glob_pattern_is_allowed
from tools.cat import ENCODINGS_TO_TRY


def _read_lines_of_file(path):
    """Return the lines of a text file, trying each known encoding.

    Returns None if the file could not be read with any encoding, so
    the caller can skip it instead of crashing.
    """
    for encoding in ENCODINGS_TO_TRY:
        try:
            with open(path, "r", encoding=encoding) as file:
                return file.readlines()
        except UnicodeDecodeError:
            continue
        except OSError:
            return None
    return None


def grep(regex, path):
    r"""Search for `regex` inside every file matched by the glob pattern `path`.

    Returns a list of strings, each formatted as
    ``"filename:line_number:line_text"``, one per matching line. If
    nothing matches, returns the message ``"No matches found"`` instead
    of an empty list, so the result is always easy to read.

    >>> matches = grep("def calculate", "tools/calculate.py")
    >>> matches[0].startswith("tools/calculate.py:")
    True
    >>> grep("xyz_no_such_text_anywhere_in_this_file_abc", "tools/calculate.py")
    'No matches found'
    >>> grep("(", "tools/*.py")
    'Error: invalid regular expression'
    >>> grep("def ", "../*.py")
    'Error: that path or pattern is not allowed'
    >>> grep("def ", "no_such_file_or_folder/*.py")
    'Error: no files matched: no_such_file_or_folder/*.py'
    """
    # Validate the glob pattern's text before using it at all. This
    # blocks obviously unsafe patterns like "../*.py" immediately.
    if not safe_glob_pattern_is_allowed(path):
        return "Error: that path or pattern is not allowed"

    # Make sure the regex itself is valid BEFORE we start opening
    # files. re.compile() raises re.error if the pattern's syntax is
    # broken (for example, an unmatched parenthesis).
    try:
        compiled_regex = re.compile(regex)
    except re.error:
        return "Error: invalid regular expression"

    # Build the glob pattern relative to the project directory (the
    # folder `chat` was launched from), not whatever folder happens to
    # be current at some other point. Looking it up fresh here keeps
    # this correct even if something else changed directories.
    project_directory = get_project_directory()
    full_pattern = os.path.join(project_directory, path)
    matching_files = glob.glob(full_pattern)

    if len(matching_files) == 0:
        return "Error: no files matched: " + path

    results = []
    for absolute_file_path in matching_files:
        # Turn the absolute path glob gave us back into a path relative
        # to the project directory, both so is_path_safe can check it
        # (it rejects absolute paths on purpose) and so our output
        # does not reveal the full machine path to the user.
        file_path = os.path.relpath(absolute_file_path, project_directory)
        file_path = file_path.replace("\\", "/")

        # Even though the pattern's text looked safe, double check
        # every individual file the pattern actually matched. This
        # protects against glob patterns that could indirectly reach
        # outside the project (for example through symbolic links).
        if not is_path_safe(file_path):
            continue

        if not os.path.isfile(absolute_file_path):
            # Skip folders -- grep only makes sense on files.
            continue

        lines = _read_lines_of_file(absolute_file_path)
        if lines is None:
            # Could not read this file (bad encoding, or it is a
            # folder, etc). Skip it instead of crashing, and move on
            # to the next file.
            continue

        line_number = 0
        for line in lines:
            line_number += 1
            if compiled_regex.search(line) is not None:
                clean_line = line.rstrip("\n")
                formatted = file_path + ":" + str(line_number) + ":" + clean_line
                results.append(formatted)

    if len(results) == 0:
        return "No matches found"

    return results
