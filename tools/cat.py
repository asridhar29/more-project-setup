r"""The `cat` tool: reads and returns the text contents of a file.

"cat" is short for "concatenate", another classic Unix command name,
traditionally used to print a file's contents to the screen.

A quick note on "encodings": a text file is really just a sequence of
bytes on disk. An "encoding" is the rulebook used to turn those bytes
back into readable characters. Most files today use an encoding called
UTF-8. Some programs on Windows instead save files using an encoding
called UTF-16. If we guess the wrong encoding, Python raises a
`UnicodeDecodeError` instead of giving us readable text, so we try
UTF-8 first and fall back to UTF-16 if that fails.
"""

import os

from tools.security import get_project_directory, is_path_safe

# We try these encodings in order until one of them successfully reads
# the file. UTF-8 is by far the most common, so we try it first.
ENCODINGS_TO_TRY = ["utf-8", "utf-16"]


def cat(path):
    r"""Read and return the text contents of the file at `path`.

    `path` is relative to the project directory.

    >>> "tools package" in cat("tools/__init__.py")
    True
    >>> cat("../outside.txt")
    'Error: that path is not allowed'
    >>> cat("this_file_does_not_exist.txt")
    'Error: no such file: this_file_does_not_exist.txt'

    `tests/fixtures/undecodable.bin` is a small file of raw bytes that
    is not valid text in UTF-8 or UTF-16 -- neither encoding can read
    it, so `cat` falls back to a clear error instead of crashing:

    >>> cat("tests/fixtures/undecodable.bin")
    'Error: could not read file (unsupported text encoding): tests/fixtures/undecodable.bin'
    """
    # Check the path is inside the project BEFORE we try to open
    # anything. This is the same rule every other tool uses.
    if not is_path_safe(path):
        return "Error: that path is not allowed"

    full_path = os.path.join(get_project_directory(), path)

    if not os.path.isfile(full_path):
        return "Error: no such file: " + path

    for encoding in ENCODINGS_TO_TRY:
        try:
            with open(full_path, "r", encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            # This encoding didn't work. Move on and try the next one.
            continue

    # If we get here, none of our known encodings could read the file.
    return "Error: could not read file (unsupported text encoding): " + path
