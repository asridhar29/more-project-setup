"""Tests for lazy client initialization, slash commands without an API
key, one-shot mode, and debug mode.
"""

from unittest.mock import patch

import chat as chat_module
from chat import Chat, FakeMessage, FakeToolCall, run_one_shot, run_slash_command


def test_groq_client_is_not_created_until_needed(monkeypatch):
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
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(chat_module, "_client", None)

    chat = Chat()
    # None of these should raise, even with no API key at all.
    run_slash_command(chat, "/ls tools")
    run_slash_command(chat, "/cat README.md")
    run_slash_command(chat, "/calculate 5 + 5")
    run_slash_command(chat, "/grep def tools/calculate.py")


def test_one_shot_mode_prints_final_reply(capsys):
    with patch("chat._request_completion_with_tools") as fake_request:
        fake_request.return_value = FakeMessage(content="Paris is the capital of France.")
        run_one_shot("What is the capital of France?")

    captured = capsys.readouterr()
    assert captured.out.strip() == "Paris is the capital of France."


def test_debug_mode_prints_tool_name_and_arguments(capsys):
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
    call = FakeToolCall("call_1", "calculate", '{"expression": "1 + 1"}')
    first_reply = FakeMessage(tool_calls=[call])
    second_reply = FakeMessage(content="It's 2.")

    chat = Chat()
    with patch("chat._request_completion_with_tools", side_effect=[first_reply, second_reply]):
        chat.send_message("What is 1 + 1?", temperature=0)

    captured = capsys.readouterr()
    assert "[DEBUG]" not in captured.out
