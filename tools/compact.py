r"""The `compact` tool: shrinks a long conversation down to one summary.

As a conversation goes on, the message history list inside a `Chat`
object keeps growing. Every single message in that list gets sent to
the AI model again every time you send a new message, which gets slow
and expensive as the conversation grows. "Compacting" means asking the
model to summarize everything said so far into a short paragraph, and
then replacing the whole long history with just that one summary
message. The conversation can continue afterward, now starting from a
short summary instead of the full transcript.

This file depends on `chat.py` (it needs the `llm` function to ask the
model for a summary), but `chat.py` also needs this file (to make the
`/compact` slash command work). Importing `chat` directly at the top of
this file, and `compact` directly at the top of `chat.py`, would create
a "circular import" -- two files trying to load each other before
either one has finished loading, which Python does not allow.

The fix is simple: `compact()` imports `llm` from `chat` INSIDE the
function body instead of at the top of the file. By the time
`compact()` actually runs, `chat.py` has already finished loading, so
the import works fine.
"""


def compact(chat):
    r"""Replace `chat.messages` with a single short summary message.

    `chat` is a `Chat` object (see `chat.py`). This function asks the
    AI model to summarize the conversation so far in five lines or
    fewer, and then -- only if that succeeds -- replaces the entire
    `chat.messages` list with one new message containing that summary.

    If the request to the model fails for any reason (no internet, bad
    API key, etc), the original conversation history is left completely
    unchanged. We generate the summary FIRST and only replace
    `chat.messages` AFTER we know the summary was created successfully,
    so a failure can never leave the conversation half-deleted.

    >>> from unittest.mock import patch
    >>> import chat as chat_module
    >>> my_chat = chat_module.Chat()
    >>> my_chat.messages.append({'role': 'user', 'content': 'My favorite color is blue.'})
    >>> my_chat.messages.append({'role': 'assistant', 'content': 'Got it, blue!'})
    >>> fake_summary = 'The user said their favorite color is blue.'
    >>> with patch('chat.llm', return_value=fake_summary):
    ...     compact(my_chat)
    'The user said their favorite color is blue.'
    >>> len(my_chat.messages)
    1
    >>> my_chat.messages[0]['content']
    'The user said their favorite color is blue.'

    If the model call raises an error, the history is left alone:

    >>> my_chat_2 = chat_module.Chat()
    >>> my_chat_2.messages.append({'role': 'user', 'content': 'Hello'})
    >>> original_length = len(my_chat_2.messages)
    >>> with patch('chat.llm', side_effect=Exception('network error')):
    ...     compact(my_chat_2)
    'Error: could not compact the conversation (network error)'
    >>> len(my_chat_2.messages) == original_length
    True
    """
    # Imported here, instead of at the top of the file, to avoid a
    # circular import with chat.py (explained in the module docstring
    # above).
    from chat import llm

    instruction = (
        "Summarize the conversation above in five lines or fewer. "
        "Keep the important facts, decisions, and context. Do not add "
        "any new information that was not already discussed."
    )

    # We build a brand new list of messages to send for the summary
    # request, instead of modifying chat.messages directly. That way,
    # if anything goes wrong, chat.messages is never touched.
    messages_to_summarize = list(chat.messages)
    messages_to_summarize.append({"role": "user", "content": instruction})

    try:
        summary = llm(messages_to_summarize, temperature=0)
    except Exception as error:
        return "Error: could not compact the conversation (" + str(error) + ")"

    # Only now, after the summary request succeeded, do we replace the
    # conversation history. This single line is the entire "compaction"
    # -- the old messages are thrown away and replaced with just this
    # one new message.
    chat.messages = [{"role": "assistant", "content": summary}]

    return summary
