"""Terminal chatbot using Groq's API. Keeps conversation history."""
import os
from unittest.mock import patch
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# client used to talk to the Groq API
client = Groq(api_key=os.environ.get('GROQ_API_KEY'))


def llm(messages, temperature=1):
    """Send the conversation so far to the model, return the reply text."""
    completion = client.chat.completions.create(
        messages=messages,
        model='openai/gpt-oss-20b',
        temperature=temperature,
    )
    return completion.choices[0].message.content


# Everything below this point is only used by the tests in the
# docstrings further down. It builds a fake reply with the same shape
# as a real Groq response (response.choices[0].message.content) so the
# tests don't need a real API key or internet connection.
class FakePiece:
    pass


def fake_response(text):
    message = FakePiece()
    message.content = text
    choice = FakePiece()
    choice.message = message
    response = FakePiece()
    response.choices = [choice]
    return response


class Chat:
    """Holds the message history for one conversation."""

    def __init__(self, system='You are a helpful assistant.'):
        # every conversation starts with a system message
        self.messages = [{'role': 'system', 'content': system}]

    def send_message(self, message, temperature=0.8):
        """Add a user message, get a reply, remember both, return the reply.

        >>> chat = Chat()
        >>> with patch('chat.client.chat.completions.create') as fake_create:
        ...     fake_create.return_value = fake_response('Hi there!')
        ...     chat.send_message('Hello', temperature=0)
        'Hi there!'
        >>> chat.messages[-2]
        {'role': 'user', 'content': 'Hello'}
        >>> chat.messages[-1]
        {'role': 'assistant', 'content': 'Hi there!'}

        A second message should go out with the full history attached,
        not just the newest message. seen_messages grabs a copy of the
        list right when the fake API gets called, since self.messages
        keeps changing after that.

        >>> seen_messages = []
        >>> seen_temperatures = []
        >>> def fake_call(messages, model, temperature):
        ...     seen_messages.append(list(messages))
        ...     seen_temperatures.append(temperature)
        ...     return fake_response('Second reply')
        >>> with patch('chat.client.chat.completions.create', side_effect=fake_call):
        ...     chat.send_message('How are you?', temperature=0)
        'Second reply'
        >>> roles = []
        >>> for entry in seen_messages[0]:
        ...     roles.append(entry['role'])
        >>> roles
        ['system', 'user', 'assistant', 'user']
        >>> seen_messages[0][1]
        {'role': 'user', 'content': 'Hello'}
        >>> seen_messages[0][2]
        {'role': 'assistant', 'content': 'Hi there!'}
        >>> seen_messages[0][3]
        {'role': 'user', 'content': 'How are you?'}
        >>> seen_temperatures[0]
        0
        """
        self.messages.append({'role': 'user', 'content': message})
        reply = llm(self.messages, temperature=temperature)
        self.messages.append({'role': 'assistant', 'content': reply})
        return reply


def repl(temperature=0.8):
    """Read a line, send it to the chatbot, print the reply, repeat.

    Exits quietly (no traceback) on Ctrl+C or end of input (Ctrl+D).

    >>> replies = [fake_response('Hi!'), fake_response('I am good.')]
    >>> with (patch('chat.client.chat.completions.create', side_effect=replies),
    ...       patch('builtins.input', side_effect=['Hello', 'How are you?', EOFError()])):
    ...     repl(temperature=0)
    Hi!
    I am good.
    <BLANKLINE>

    >>> with (patch('chat.client.chat.completions.create', side_effect=replies),
    ...       patch('builtins.input', side_effect=['Hello', KeyboardInterrupt()])):
    ...     repl(temperature=0)
    Hi!
    <BLANKLINE>
    """
    chat = Chat()
    try:
        while True:
            user_input = input('chat> ')
            print(chat.send_message(user_input, temperature=temperature))
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == '__main__':
    repl()
