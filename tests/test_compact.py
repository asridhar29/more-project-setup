"""Tests for conversation compaction (tools/compact.py), using a fake,
known summary instead of a real API call.
"""

from unittest.mock import patch

from chat import Chat
from tools.compact import compact


def test_compact_replaces_history_with_one_known_summary():
    """Check that compact() replaces the whole conversation with exactly one summary message."""
    chat = Chat()
    chat.messages.append({"role": "user", "content": "My favorite color is blue."})
    chat.messages.append({"role": "assistant", "content": "Got it, blue!"})

    fake_summary = "The user's favorite color is blue."
    with patch("chat.llm", return_value=fake_summary):
        returned_value = compact(chat)

    assert returned_value == fake_summary
    assert len(chat.messages) == 1
    assert chat.messages[0]["content"] == fake_summary


def test_failed_compaction_leaves_original_history_unchanged():
    """Check that a failed summarization request leaves the original conversation untouched."""
    chat = Chat()
    chat.messages.append({"role": "user", "content": "Hello"})
    chat.messages.append({"role": "assistant", "content": "Hi!"})
    original_messages = list(chat.messages)

    with patch("chat.llm", side_effect=Exception("network error")):
        result = compact(chat)

    assert result.startswith("Error:")
    assert chat.messages == original_messages
