"""Tests for the model tool-calling loop in chat.py.

These cover the trickier scenarios: the model asking for more than one
tool at once, asking for a tool that doesn't exist, sending arguments
that aren't valid JSON, and the API itself failing.
"""

from unittest.mock import patch

import pytest

from chat import Chat, FakeMessage, FakeToolCall, run_tool


def test_multiple_tool_calls_in_one_turn_are_all_executed():
    """Check that when the model requests two tools at once, both run and both results are saved.

    >>> test_multiple_tool_calls_in_one_turn_are_all_executed()
    """
    call_a = FakeToolCall("call_a", "calculate", '{"expression": "2 + 2"}')
    call_b = FakeToolCall("call_b", "calculate", '{"expression": "3 + 3"}')

    first_reply = FakeMessage(tool_calls=[call_a, call_b])
    second_reply = FakeMessage(content="The answers are 4 and 6.")

    chat = Chat()
    with patch("chat._request_completion_with_tools", side_effect=[first_reply, second_reply]):
        answer = chat.send_message("What is 2+2 and 3+3?", temperature=0)

    assert answer == "The answers are 4 and 6."

    tool_messages = []
    for entry in chat.messages:
        if entry["role"] == "tool":
            tool_messages.append(entry)

    assert len(tool_messages) == 2
    assert tool_messages[0]["tool_call_id"] == "call_a"
    assert tool_messages[0]["content"] == "4"
    assert tool_messages[1]["tool_call_id"] == "call_b"
    assert tool_messages[1]["content"] == "6"


def test_unknown_tool_name_does_not_crash():
    """Check that run_tool() with an unregistered tool name returns an error, not a crash.

    >>> test_unknown_tool_name_does_not_crash()
    """
    result = run_tool("this_tool_does_not_exist", "{}")
    assert result == "Error: unknown tool: this_tool_does_not_exist"


def test_unknown_tool_requested_by_model_is_handled_gracefully():
    """Check that the model requesting a nonexistent tool is handled within the normal conversation flow.

    >>> test_unknown_tool_requested_by_model_is_handled_gracefully()
    """
    call = FakeToolCall("call_1", "delete_everything", "{}")
    first_reply = FakeMessage(tool_calls=[call])
    second_reply = FakeMessage(content="I cannot do that.")

    chat = Chat()
    with patch("chat._request_completion_with_tools", side_effect=[first_reply, second_reply]):
        answer = chat.send_message("Delete everything", temperature=0)

    assert answer == "I cannot do that."
    tool_result = chat.messages[3]
    assert tool_result["role"] == "tool"
    assert "unknown tool" in tool_result["content"]


def test_invalid_json_arguments_are_handled_gracefully():
    """Check that malformed JSON tool arguments return a clear error instead of raising.

    >>> test_invalid_json_arguments_are_handled_gracefully()
    """
    result = run_tool("calculate", "{not valid json!!")
    assert result == "Error: could not understand the tool arguments (invalid JSON)"


def test_api_failure_during_conversation_is_not_swallowed_silently():
    """Check that an exception from the API call propagates out of send_message() instead of being hidden.

    >>> test_api_failure_during_conversation_is_not_swallowed_silently()
    """
    # send_message itself does not catch exceptions -- that is done by
    # the callers (repl() and run_one_shot()), so the conversation
    # history is not left in a confusing half-updated state.
    chat = Chat()
    with patch("chat._request_completion_with_tools", side_effect=Exception("network down")):
        with pytest.raises(Exception):
            chat.send_message("Hello", temperature=0)


def test_repl_shows_friendly_message_on_api_failure(capsys, monkeypatch):
    r"""Check that the REPL prints a friendly error message instead of crashing on an API failure.

    This test itself needs pytest's `capsys` and `monkeypatch` fixtures,
    which a plain doctest has no way to supply. So instead of calling
    this test function directly, this example demonstrates the exact
    same underlying production behavior -- `repl()` surviving an API
    failure and printing a friendly message -- using only
    `unittest.mock.patch` and `io.StringIO` to capture output, neither
    of which needs a pytest fixture:

    >>> import io, contextlib
    >>> from unittest.mock import patch
    >>> import chat as chat_module
    >>> inputs = iter(["Hello", EOFError()])
    >>> def _scripted_input(prompt):
    ...     value = next(inputs)
    ...     if isinstance(value, Exception):
    ...         raise value
    ...     return value
    >>> captured_output = io.StringIO()
    >>> with (patch("builtins.input", _scripted_input),
    ...       patch("chat._request_completion_with_tools", side_effect=Exception("network down")),
    ...       contextlib.redirect_stdout(captured_output)):
    ...     chat_module.repl(temperature=0)
    >>> "Error talking to the AI model" in captured_output.getvalue()
    True
    """
    import chat as chat_module

    inputs = iter(["Hello", EOFError()])

    def fake_input(prompt):
        """Return the next scripted input, or raise it if it's an exception (simulates EOF)."""
        value = next(inputs)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr("builtins.input", fake_input)

    with patch("chat._request_completion_with_tools", side_effect=Exception("network down")):
        chat_module.repl(temperature=0)

    captured = capsys.readouterr()
    assert "Error talking to the AI model" in captured.out
