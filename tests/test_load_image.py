"""Tests for the load_image tool: valid PNGs, invalid paths, and the
shape of the image message added to the conversation.
"""

from unittest.mock import patch

from chat import Chat
from tools.load_image import load_image


def test_loading_valid_png_adds_one_image_message():
    """Check that loading a real PNG appends one correctly-shaped image_url message.

    >>> test_loading_valid_png_adds_one_image_message()
    """
    chat = Chat()
    original_length = len(chat.messages)

    result = load_image(chat, "tests/fixtures/pixel.png")

    assert result == "Image loaded: tests/fixtures/pixel.png"
    assert len(chat.messages) == original_length + 1

    new_message = chat.messages[-1]
    assert new_message["role"] == "user"
    assert isinstance(new_message["content"], list)

    image_block = new_message["content"][0]
    assert image_block["type"] == "image_url"
    assert image_block["image_url"]["url"].startswith("data:image/png;base64,")


def test_invalid_paths_do_not_modify_conversation_history():
    """Check that unsafe, missing, or non-PNG paths return an error and leave history untouched.

    >>> test_invalid_paths_do_not_modify_conversation_history()
    """
    chat = Chat()
    original_messages = list(chat.messages)

    assert load_image(chat, "../outside.png").startswith("Error:")
    assert chat.messages == original_messages

    assert load_image(chat, "/etc/image.png").startswith("Error:")
    assert chat.messages == original_messages

    assert load_image(chat, "no_such_image.png").startswith("Error:")
    assert chat.messages == original_messages

    assert load_image(chat, "README.md").startswith("Error:")
    assert chat.messages == original_messages


def test_unreadable_file_does_not_modify_conversation_history():
    """Check that a file that fails to open (mocked OSError) leaves conversation history untouched.

    >>> test_unreadable_file_does_not_modify_conversation_history()
    """
    chat = Chat()
    original_messages = list(chat.messages)

    with patch("tools.load_image.open", side_effect=OSError("permission denied")):
        result = load_image(chat, "tests/fixtures/pixel.png")

    assert result.startswith("Error: could not read file")
    assert chat.messages == original_messages
