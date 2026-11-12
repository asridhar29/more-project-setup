r"""The `ls` tool: lists files and folders inside a project directory.

"ls" is a classic Unix command name (short for "list"). Here we build
our own small version of it using Python's `glob` module.

A quick note on `glob`: it is a standard library module for finding
files that match a pattern containing wildcards. The pattern ``*``
means "match anything", so the pattern ``tools/*`` means "every file
or folder directly inside the tools folder". This is different from
`os.listdir`, but glob is what the assignment asks us to use, and it
has the nice property of also supporting patterns like ``*.py``.
"""

import glob
import os

from tools.security import get_project_directory, is_path_safe


def ls(path="."):
    r"""List the files and folders directly inside `path`, sorted alphabetically.

    `path` is relative to the project directory. It defaults to ``"."``,
    which means "the project directory itself".

    >>> result = ls("tools")
    >>> "calculate.py" in result
    True
    >>> "ls.py" in result
    True
    >>> ls("../outside")
    'Error: that path is not allowed'
    >>> ls("this_folder_does_not_exist")
    'Error: no such directory: this_folder_does_not_exist'
    """
    # Always check the path with our shared security helper before we
    # touch the filesystem at all. This stops someone from asking the
    # chatbot to list files outside the project, like "/" or "../../".
    if not is_path_safe(path):
        return "Error: that path is not allowed"

    # Build the real, absolute folder we are about to look inside, by
    # combining the project directory with the requested relative path.
    full_directory = os.path.join(get_project_directory(), path)

    if not os.path.isdir(full_directory):
        return "Error: no such directory: " + path

    # glob.glob() returns a list of paths that match the given pattern.
    # Here the pattern is "<folder>/*", which matches every item (file
    # or folder) directly inside that folder, one level deep.
    search_pattern = os.path.join(full_directory, "*")
    matches = glob.glob(search_pattern)

    # Each match is currently a full path like "C:/.../tools/ls.py". We
    # only want the last piece (the file or folder's own name), so we
    # use os.path.basename() to strip away everything before it.
    names = []
    for match in matches:
        names.append(os.path.basename(match))

    names.sort()
    return names
