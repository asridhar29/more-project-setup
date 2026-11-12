r"""Shared file-path security helper used by every tool.

Several of our tools (`ls`, `cat`, `grep`, `load_image`) read files from
disk because the user or the AI model asked them to. That is risky: if we
are not careful, someone could ask the chatbot to read a file like
``../../../etc/passwd`` or an absolute path like ``C:/Users/secret.txt``
and the chatbot would happily hand over private information from outside
the project folder.

To stop that, every tool in this project calls `is_path_safe` *before* it
opens any file. This file is the ONLY place that decides what counts as
"safe". Keeping the logic in one place (instead of copy-pasting similar
checks into every tool) means we only have to get it right once, and
every tool automatically benefits from fixes made here.

Key concept for beginners: "resolving" a path means turning something
like ``tools/../chat.py`` into the actual absolute path it points to
(``chat.py``), so we can check where it *really* points, not just what
the text of the path looks like.

Another key concept: the "project directory" that every tool is locked
into is whatever folder you were standing in (your current working
directory) when you typed `chat`. That is what lets you install
docchat once and then use it to inspect any project: run `chat` from
inside this repository and it can see this repository's files; `cd`
into some other project and run `chat` there, and it can see that
project's files instead -- never anything outside wherever you
launched it from.
"""

import os


def get_project_directory():
    r"""Return the folder that every tool is locked into: the current working directory.

    `os.getcwd()` ("get current working directory") returns whatever
    folder the terminal was in when `chat` was launched. We look this
    up fresh every time, instead of caching it once, so it always
    reflects where the chatbot was actually started from.
    """
    return os.getcwd()


def is_path_safe(path):
    r"""Return True if `path` is safely inside the project directory.

    A path is considered safe only if ALL of these are true:

    1. It is not an absolute path (like ``/etc/passwd`` or ``C:\secrets``).
       Absolute paths point to a specific place on the whole computer,
       not a place inside our project, so we reject them outright.
    2. It does not contain ``..`` anywhere. ``..`` means "go up one
       folder", and a path like ``tools/../../secret.txt`` can sneak
       outside the project folder even though it does not look absolute.
    3. After resolving the path to its real, absolute location on disk,
       that location is still inside the project directory.

    We check both the raw text of the path (steps 1 and 2) AND the
    resolved, real location (step 3). Checking only the text is not
    enough, because of things like symbolic links (shortcuts on disk
    that point somewhere else) -- a path's text can look innocent while
    secretly pointing outside the project. Resolving it tells us where
    it truly leads.

    >>> is_path_safe("chat.py")
    True
    >>> is_path_safe("tools/calculate.py")
    True
    >>> is_path_safe("../secret.txt")
    False
    >>> is_path_safe("/etc/passwd")
    False
    >>> is_path_safe("tools/../../outside.txt")
    False

    A path with a drive letter (Windows-specific, like
    ``C:/Windows/system32``) *is* caught by `os.path.isabs()`, unlike
    the drive-relative paths above:

    >>> is_path_safe("C:/Windows/system32")
    False

    The very last safety net is `os.path.commonpath()`, used to check
    whether the resolved path is inside the project directory. On
    Windows, that function raises `ValueError` if asked to compare two
    paths on different drives -- which can't happen through this
    function's normal checks above, so we fake that error here with
    `unittest.mock` to prove the fallback still says "not safe" instead
    of crashing:

    >>> from unittest.mock import patch
    >>> with patch('os.path.commonpath', side_effect=ValueError('no common path')):
    ...     is_path_safe("chat.py")
    False
    """
    # An absolute path already points to one exact place on the machine,
    # ignoring the project folder entirely, so it is never safe.
    if os.path.isabs(path):
        return False

    # On Windows, os.path.isabs() has a surprising gap: a path that
    # starts with "/" or "\" but has no drive letter (like "/etc/passwd")
    # is NOT considered absolute, even though os.path.join() treats it
    # as "replace everything and jump to the root of the current
    # drive". That would let a path like "/etc/passwd" slip past the
    # isabs() check above and then escape the project directory. So we
    # also explicitly reject any path that starts with a slash or
    # backslash, on every platform.
    if path.startswith("/") or path.startswith("\\"):
        return False

    # os.path.normpath() cleans up a path (for example turning "a/./b"
    # into "a/b") but importantly for us, it also collapses ".." where
    # it can. We check the ORIGINAL text for ".." first, before any
    # cleanup happens, because a sneaky path could be written in a way
    # that still means "go outside" even after normalizing.
    normalized_slashes = path.replace("\\", "/")
    path_pieces = normalized_slashes.split("/")
    if ".." in path_pieces:
        return False

    # Now figure out where this path actually points on disk, as a full
    # absolute path, starting from the project directory. This follows
    # any shortcuts/symlinks and resolves "." and ".." pieces for real.
    project_directory = get_project_directory()
    candidate = os.path.join(project_directory, path)
    resolved_path = os.path.realpath(candidate)
    resolved_project_directory = os.path.realpath(project_directory)

    # The resolved path is safe only if it is the project directory
    # itself, or somewhere inside it. os.path.commonpath tells us the
    # shared starting folder of two paths; if that shared folder is the
    # project directory, then resolved_path is inside (or equal to) it.
    try:
        common = os.path.commonpath([resolved_path, resolved_project_directory])
    except ValueError:
        # This happens on Windows if the two paths are on different
        # drives (like C:\ and D:\) -- they can't share a folder at all,
        # so the path is definitely not inside the project.
        return False

    return common == resolved_project_directory


def safe_glob_pattern_is_allowed(pattern):
    r"""Return True if a glob pattern cannot be used to escape the project.

    Glob patterns (used by `ls` and `grep`) are strings with wildcards
    like ``*`` or ``?`` that match many files at once, for example
    ``tools/*.py`` matches every ``.py`` file inside ``tools``. Before we
    let a tool search using a pattern, we check the pattern's text the
    same way we check a normal path: no absolute paths, and no ``..``
    pieces. The actual files that the pattern matches are checked again,
    individually, with `is_path_safe` after the glob search runs -- this
    function just rejects obviously unsafe patterns up front.

    >>> safe_glob_pattern_is_allowed("tools/*.py")
    True
    >>> safe_glob_pattern_is_allowed("../*.py")
    False
    >>> safe_glob_pattern_is_allowed("/*.py")
    False
    >>> safe_glob_pattern_is_allowed("C:/Windows/*.py")
    False
    """
    if os.path.isabs(pattern):
        return False

    # See the matching comment in is_path_safe() above: on Windows, a
    # pattern starting with "/" or "\" has no drive letter and so is
    # NOT caught by os.path.isabs(), even though it behaves like an
    # absolute path once combined with a base directory.
    if pattern.startswith("/") or pattern.startswith("\\"):
        return False

    normalized_slashes = pattern.replace("\\", "/")
    pattern_pieces = normalized_slashes.split("/")
    if ".." in pattern_pieces:
        return False

    return True
