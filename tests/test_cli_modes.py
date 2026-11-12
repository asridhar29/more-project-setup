"""Tests for lazy client initialization, slash commands without an API
key, one-shot mode, and debug mode.

Every test function in this file takes a pytest fixture (`monkeypatch`
or `capsys`) as an argument, which a plain doctest has no way to
supply. So each docstring below demonstrates the same underlying
production behavior with a standalone example instead of calling the
test function directly -- using only `unittest.mock.patch` and
`io.StringIO`/`contextlib.redirect_stdout` to stand in for
`monkeypatch` and `capsys`.
"""

from unittest.mock import patch

import chat as chat_module
from chat import Chat, FakeMessage, FakeToolCall, run_one_shot, run_slash_command


def test_groq_client_is_not_created_until_needed(monkeypatch):
    r"""Check that running slash commands never builds a Groq client, but get_client() does.

    >>> import io, contextlib
    >>> chat_module._client = None
    >>> my_chat = Chat()
    >>> with (patch("chat.Groq") as fake_groq_class,
    ...       contextlib.redirect_stdout(io.StringIO())):
    ...     run_slash_command(my_chat, "/ls tools")
    ...     run_slash_command(my_chat, "/calculate 2 + 2")
    ...     client_built_before = fake_groq_class.called
    ...     chat_module.get_client()
    ...     client_built_after = fake_groq_class.called
    >>> client_built_before
    False
    >>> client_built_after
    True
    """
    # Reset the lazy client so this test doesn't depend on what ran before it.
    monkeypatch.setattr(chat_module, "_client", None)

    with patch("chat.Groq") as fake_groq_class:
        chat = Chat()
        run_slash_command(chat, "/ls tools")
        run_slash_command(chat, "/calculate 2 + 2")

        # Running local slash commands must never construct a Groq client.
        fake_groq_class.assert_not_called()

        chat_module.get_client()
        # Only once we actually ask for the client does it get built.
        fake_groq_class.assert_called_once()


def test_slash_commands_work_with_no_api_key_configured(monkeypatch):
    r"""Check that /ls, /cat, /calculate, and /grep all work with no GROQ_API_KEY set at all.

    >>> import io, contextlib, os
    >>> old_key = os.environ.pop("GROQ_API_KEY", None)
    >>> chat_module._client = None
    >>> my_chat = Chat()
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     run_slash_command(my_chat, "/ls tools")
    ...     run_slash_command(my_chat, "/cat README.md")
    ...     run_slash_command(my_chat, "/calculate 5 + 5")
    ...     run_slash_command(my_chat, "/grep def tools/calculate.py")
    >>> if old_key is not None:
    ...     os.environ["GROQ_API_KEY"] = old_key
    """
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(chat_module, "_client", None)

    chat = Chat()
    # None of these should raise, even with no API key at all.
    run_slash_command(chat, "/ls tools")
    run_slash_command(chat, "/cat README.md")
    run_slash_command(chat, "/calculate 5 + 5")
    run_slash_command(chat, "/grep def tools/calculate.py")


def test_one_shot_mode_prints_final_reply(capsys):
    r"""Check that run_one_shot() prints exactly the model's final reply text.

    >>> import io, contextlib
    >>> captured_output = io.StringIO()
    >>> with (patch("chat._request_completion_with_tools") as fake_request,
    ...       contextlib.redirect_stdout(captured_output)):
    ...     fake_request.return_value = FakeMessage(content="Paris is the capital of France.")
    ...     run_one_shot("What is the capital of France?")
    >>> captured_output.getvalue().strip() == "Paris is the capital of France."
    True
    """
    with patch("chat._request_completion_with_tools") as fake_request:
        fake_request.return_value = FakeMessage(content="Paris is the capital of France.")
        run_one_shot("What is the capital of France?")

    captured = capsys.readouterr()
    assert captured.out.strip() == "Paris is the capital of France."


def test_debug_mode_prints_tool_name_and_arguments(capsys):
    r"""Check that debug=True prints the tool's name and arguments when the model calls a tool.

    >>> import io, contextlib
    >>> call = FakeToolCall("call_1", "calculate", '{"expression": "6 * 7"}')
    >>> first_reply = FakeMessage(tool_calls=[call])
    >>> second_reply = FakeMessage(content="It's 42.")
    >>> my_chat = Chat()
    >>> captured_output = io.StringIO()
    >>> with (patch("chat._request_completion_with_tools", side_effect=[first_reply, second_reply]),
    ...       contextlib.redirect_stdout(captured_output)):
    ...     my_chat.send_message("What is 6 times 7?", temperature=0, debug=True)
    >>> "[DEBUG] Tool requested: calculate" in captured_output.getvalue()
    True
    >>> "[DEBUG] Tool finished: calculate" in captured_output.getvalue()
    True
    """
    call = FakeToolCall("call_1", "calculate", '{"expression": "6 * 7"}')
    first_reply = FakeMessage(tool_calls=[call])
    second_reply = FakeMessage(content="It's 42.")

    chat = Chat()
    with patch("chat._request_completion_with_tools", side_effect=[first_reply, second_reply]):
        chat.send_message("What is 6 times 7?", temperature=0, debug=True)

    captured = capsys.readouterr()
    assert "[DEBUG] Tool requested: calculate" in captured.out
    assert '[DEBUG] Arguments: {"expression": "6 * 7"}' in captured.out
    assert "[DEBUG] Tool finished: calculate" in captured.out


def test_debug_mode_off_by_default_prints_no_debug_lines(capsys):
    r"""Check that no [DEBUG] lines are printed when debug is left at its default of False.

    >>> import io, contextlib
    >>> call = FakeToolCall("call_1", "calculate", '{"expression": "1 + 1"}')
    >>> first_reply = FakeMessage(tool_calls=[call])
    >>> second_reply = FakeMessage(content="It's 2.")
    >>> my_chat = Chat()
    >>> captured_output = io.StringIO()
    >>> with (patch("chat._request_completion_with_tools", side_effect=[first_reply, second_reply]),
    ...       contextlib.redirect_stdout(captured_output)):
    ...     my_chat.send_message("What is 1 + 1?", temperature=0)
    >>> "[DEBUG]" in captured_output.getvalue()
    False
    """
    call = FakeToolCall("call_1", "calculate", '{"expression": "1 + 1"}')
    first_reply = FakeMessage(tool_calls=[call])
    second_reply = FakeMessage(content="It's 2.")

    chat = Chat()
    with patch("chat._request_completion_with_tools", side_effect=[first_reply, second_reply]):
        chat.send_message("What is 1 + 1?", temperature=0)

    captured = capsys.readouterr()
    assert "[DEBUG]" not in captured.out
