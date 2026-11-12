r"""The `load_image` tool: adds a local PNG image into the conversation.

Some AI models can "see" images, not just read text -- these are
called "vision-capable" models. To send an image to one of these
models through the chat-completions API, the image needs to be turned
into text first, since the conversation history is just a list of
text-based messages.

The standard trick for this is "Base64 encoding". Base64 is a way of
representing raw bytes (like the bytes of a PNG file) using only
letters, digits, and a couple of punctuation characters -- the kind of
plain text that can safely be put inside a JSON message. Python's
built-in `base64` module does this conversion for us; no extra
libraries are needed.

Once the image bytes are Base64-encoded, we wrap the result in a "data
URL", which is a special kind of URL that contains the data directly
inside it instead of pointing to a file somewhere else. It looks like
this:

    data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...

That whole string gets placed into an "image_url" content block and
added to the conversation history, in the format the chat-completions
API expects for image input. Note: not every Groq model understands
images. Sending this block to a model that is not vision-capable will
simply not work for image analysis -- see the README for which models
to use.
"""

import base64
import os

from tools.security import get_project_directory, is_path_safe


def load_image(chat, path):
    r"""Add the PNG image at `path` to `chat`'s conversation as an image message.

    `chat` is a `Chat` object (see `chat.py`). `path` must be a `.png`
    file, given as a path relative to the project directory.

    On success, a new message with role `"user"` is appended to
    `chat.messages`, containing an `image_url` content block with the
    image encoded as a Base64 data URL. On failure (bad path, missing
    file, wrong file type), `chat.messages` is left completely
    unchanged, and a clear error message is returned instead.

    >>> import chat as chat_module
    >>> my_chat = chat_module.Chat()
    >>> original_length = len(my_chat.messages)
    >>> load_image(my_chat, "../outside.png")
    'Error: that path is not allowed'
    >>> len(my_chat.messages) == original_length
    True
    >>> load_image(my_chat, "no_such_image.png")
    'Error: no such file: no_such_image.png'
    >>> load_image(my_chat, "README.md")
    'Error: only .png files are supported'

    Successfully loading a real PNG adds one image message:

    >>> load_image(my_chat, "tests/fixtures/pixel.png")
    'Image loaded: tests/fixtures/pixel.png'
    >>> len(my_chat.messages) == original_length + 1
    True
    >>> my_chat.messages[-1]['content'][0]['type']
    'image_url'
    >>> my_chat.messages[-1]['content'][0]['image_url']['url'].startswith('data:image/png;base64,')
    True

    If the file can't actually be read (for example, no permission to
    open it), history is left unchanged and a clear error comes back
    instead of a crash. We fake that failure here with `unittest.mock`
    so this doctest doesn't depend on real file permissions. We patch
    `'builtins.open'` (not `'tools.load_image.open'`) because `open` is
    a Python builtin that every module shares one single copy of, so
    patching it there works no matter what name this file happens to
    have been imported under:

    >>> from unittest.mock import patch
    >>> another_chat = chat_module.Chat()
    >>> with patch('builtins.open', side_effect=OSError('permission denied')):
    ...     load_image(another_chat, "tests/fixtures/pixel.png")
    'Error: could not read file (permission denied)'
    >>> len(another_chat.messages)
    1
    """
    # Same shared security check every other file-reading tool uses.
    if not is_path_safe(path):
        return "Error: that path is not allowed"

    # Only PNG files are supported, as required. We check the file
    # name's ending (case-insensitively) rather than trying to guess
    # the file type from its contents, which keeps this simple.
    if not path.lower().endswith(".png"):
        return "Error: only .png files are supported"

    full_path = os.path.join(get_project_directory(), path)

    if not os.path.isfile(full_path):
        return "Error: no such file: " + path

    # Read the image as raw bytes ("rb" means "read binary"), not as
    # text -- image data is not text, and trying to read it as text
    # would corrupt it.
    try:
        with open(full_path, "rb") as image_file:
            image_bytes = image_file.read()
    except OSError as error:
        return "Error: could not read file (" + str(error) + ")"

    # base64.b64encode() turns raw bytes into Base64-encoded bytes.
    # We then call .decode("utf-8") to turn those encoded bytes into a
    # normal Python string, since Base64 output is always plain text
    # characters (letters, digits, "+", "/", "=") even though the
    # function technically returns a "bytes" object first.
    base64_text = base64.b64encode(image_bytes).decode("utf-8")
    data_url = "data:image/png;base64," + base64_text

    # This is the standard OpenAI-compatible way of describing an
    # image inside a chat message: a message whose "content" is a list
    # of content blocks, where one block has type "image_url".
    image_message = {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": data_url},
            }
        ],
    }

    chat.messages.append(image_message)

    return "Image loaded: " + path
