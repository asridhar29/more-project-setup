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

import codecs
import glob
import os
import re

from tools.security import get_project_directory, is_path_safe, safe_glob_pattern_is_allowed

# A byte-order mark (BOM) is a few special bytes some text files start
# with, which say how the rest of the file is encoded. Checking for
# one FIRST, before ever trying to decode as UTF-16, is important: the
# UTF-16 codec raises a confusing error ("stream does not start with
# BOM") if it is asked to decode a file's lines one at a time (as
# `.readlines()` does) and that file does not actually start with a
# UTF-16 BOM. Reading the raw bytes ourselves and checking for a BOM
# first means we only ever attempt UTF-16 decoding when we already
# know it is safe to do so.
UTF16_BOMS = (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)


def _read_lines_of_file(path):
    r"""Return the lines of a text file, detecting its real encoding first.

    Reads the file's raw bytes, then decides how to decode them based
    on what those bytes actually look like:

    - A UTF-16 byte-order mark (BOM) means it is safe to decode as
      UTF-16 -- Python uses the BOM to pick the correct byte order
      (little-endian or big-endian) and strips it out automatically.
    - A UTF-8 BOM means it is safe to decode as UTF-8, using the
      "utf-8-sig" encoding, which also strips the BOM out.
    - A "\x00" (null) byte anywhere in the file is a strong sign this
      is a binary file (like an image), not text -- real text files
      essentially never contain one. We give up immediately in that
      case, rather than risk turning binary bytes into fake-looking
      matches.
    - Otherwise, there's no BOM and no null byte, so we try plain
      UTF-8 first (the most common case by far), and if that fails,
      "cp1252" (a common older Windows text encoding) as a fallback --
      so a legitimate text file saved in an older encoding is not
      skipped just because it isn't UTF-8.

    Returns None, instead of raising an error, if the file's bytes
    can't reasonably be decoded as text by any of the above, or if the
    file can't be opened for some other reason (missing, no
    permission, etc) -- so the caller can skip it instead of crashing.

    >>> lines = _read_lines_of_file("tools/__init__.py")
    >>> "tools package" in "".join(lines)
    True

    `utf16_sample.txt` was written using Python's native byte order,
    which on most computers today is little-endian; `utf16_be_sample.txt`
    was built by hand with an explicit big-endian BOM instead, to prove
    both byte orders are handled, not just one:

    >>> _read_lines_of_file("tests/fixtures/utf16_sample.txt")
    ['Hello from a UTF-16 file!']
    >>> _read_lines_of_file("tests/fixtures/utf16_be_sample.txt")
    ['Hello from UTF-16 big-endian!']
    >>> _read_lines_of_file("tests/fixtures/utf8_bom_sample.txt")
    ['This file has a UTF-8 byte-order mark.']

    A legitimate text file saved in an older Windows encoding (here,
    "cp1252") is still read correctly, even though it is not valid
    UTF-8 and has no BOM at all. The file contains a curly right-quote
    character (code point 8217) that only exists in cp1252, not
    plain ASCII -- checking its code point number instead of writing
    the character directly here avoids any confusion about how a
    terminal might display it:

    >>> cp1252_lines = _read_lines_of_file("tests/fixtures/cp1252_sample.txt")
    >>> cp1252_lines[0].startswith("This file uses a legacy Windows encoding: it")
    True
    >>> ord(cp1252_lines[0][44])
    8217
    >>> cp1252_lines[0].endswith("s cp1252.")
    True

    A genuinely binary file (one containing a null byte, like a PNG
    image) is skipped cleanly -- `_read_lines_of_file` never even
    attempts to decode it as UTF-16, since there is no BOM to justify
    that, and never risks decoding it as cp1252 "text" either, since
    the null byte already marks it as binary:

    >>> _read_lines_of_file("tests/fixtures/no_bom_binary.bin") is None
    True
    >>> _read_lines_of_file("tests/fixtures/undecodable.bin") is None
    True

    A different kind of failure (not a bad encoding, but something
    like no permission to read the file at all) also returns `None`
    instead of crashing. We fake that here with `unittest.mock`, since
    we can't rely on actually having a permission-denied file to test
    with. We patch `'builtins.open'` (not, say, `'tools.grep.open'`)
    because `open` is a Python builtin that every module shares one
    single copy of -- patching it there affects this function no
    matter what name this file happens to have been imported under:

    >>> from unittest.mock import patch
    >>> with patch('builtins.open', side_effect=OSError('permission denied')):
    ...     _read_lines_of_file("tools/__init__.py") is None
    True
    """
    try:
        with open(path, "rb") as file:
            raw_bytes = file.read()
    except OSError:
        return None

    if raw_bytes.startswith(UTF16_BOMS):
        candidate_encodings = ["utf-16"]
    elif raw_bytes.startswith(codecs.BOM_UTF8):
        candidate_encodings = ["utf-8-sig"]
    elif b"\x00" in raw_bytes:
        return None
    else:
        candidate_encodings = ["utf-8", "cp1252"]

    for encoding in candidate_encodings:
        try:
            text = raw_bytes.decode(encoding)
            return text.splitlines(keepends=True)
        except UnicodeDecodeError:
            continue

    return None


def grep(regex, path):
    r"""Search for `regex` inside every file matched by the glob pattern `path`.

    Returns a list of strings, each formatted as
    ``"filename:line_number:line_text"``, one per matching line. If
    nothing matches, returns an empty list -- so, just like the real
    Unix `grep` command, no matches means no output at all.

    >>> matches = grep("def calculate", "tools/calculate.py")
    >>> matches[0].startswith("tools/calculate.py:")
    True
    >>> grep("xyz_no_such_text_anywhere_in_this_file_abc", "tools/calculate.py")
    []

    A glob pattern can match more than one file; results from every
    matching file are combined into one list, each still tagged with
    its own filename:

    >>> matches = grep("is_path_safe", "tools/*.py")
    >>> files_matched = set()
    >>> for line in matches:
    ...     files_matched.add(line.split(":")[0])
    >>> len(files_matched) >= 3
    True
    >>> grep("(", "tools/*.py")
    'Error: invalid regular expression'
    >>> grep("def ", "../*.py")
    'Error: that path or pattern is not allowed'

    A valid, safe glob pattern that matches no files at all is not an
    error either -- it just means there was nothing to search:

    >>> grep("def ", "no_such_file_or_folder/*.py")
    []

    A glob pattern can match files `grep` has to skip instead of
    crashing: `tests/fixtures/pixel.png`, `tests/fixtures/undecodable.bin`,
    and `tests/fixtures/no_bom_binary.bin` are none of them valid text
    (and none of them start with a byte-order mark either), so they
    are silently skipped, leaving only the real matches from the
    genuine text files in that folder:

    >>> grep("Hello", "tests/fixtures/*")
    ['tests/fixtures/utf16_be_sample.txt:1:Hello from UTF-16 big-endian!', 'tests/fixtures/utf16_sample.txt:1:Hello from a UTF-16 file!']

    A pattern can also match folders (not just files) -- `grep` skips
    those too, since searching inside a folder doesn't make sense.
    `test_projects/*` demonstrates this with the three real submodule
    folders, but that only proves the point if those submodules have
    actually been checked out; `tests/*` proves the same thing using
    `tests/fixtures`, an ordinary folder that is always present
    regardless of submodule state:

    >>> grep("anything", "test_projects/*")
    []
    >>> grep("zzz_never_matches_anything_zzz", "tests/*")
    []

    As a last resort, even a file an allowed glob pattern matched gets
    one more individual safety check (`is_path_safe`) before it's
    opened, in case a symbolic link made it secretly point outside the
    project. That is hard to arrange for real in a doctest, so we fake
    that check failing here with `unittest.mock`. `is_path_safe` was
    imported into *this* module's own namespace (unlike `open`, it is
    not a shared builtin), so we patch it there, on a reference to
    this exact, currently-running module -- `sys.modules[__name__]` --
    rather than on the fixed string `'tools.grep'`, which can point to
    a *different* copy of this same file when it's run in certain ways
    (for example, `python -m doctest` on this file directly imports it
    under the plain name `"grep"`, not `"tools.grep"`):

    >>> import sys
    >>> from unittest.mock import patch
    >>> this_module = sys.modules[__name__]
    >>> with patch.object(this_module, 'is_path_safe', return_value=False):
    ...     grep("def calculate", "tools/calculate.py")
    []
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

    # A valid, safe glob pattern that simply doesn't match anything is
    # not an error -- it just means there is nothing to search. This
    # matches the real Unix `grep` command's behavior (no matches
    # means no output), and keeps this case consistent with every
    # other "nothing to report" case below (no searchable files,
    # files with no matching text, and so on), which also returns [].
    if not matching_files:
        return []

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

    return results
