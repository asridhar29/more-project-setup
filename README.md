# docchat

A simple terminal chatbot that talks to an AI model through the
[Groq](https://groq.com/) API.

## What it does

You type a message, the chatbot replies, and the conversation keeps
going until you quit. The chatbot remembers everything said earlier
in the same conversation, so you can ask follow-up questions and it
will have context.

## How conversation history works

Every message (yours and the assistant's) is stored, in order, as a
list of small dictionaries like `{'role': 'user', 'content': '...'}`.
Each time you send a new message, the *entire* list is sent to the
model, not just your latest message. That's what gives the chatbot
"memory" of the conversation. The history only lasts for the current
run — it is not saved anywhere after you quit.

## Dependencies

- `groq` — talks to the Groq API
- `python-dotenv` — loads your API key from a `.env` file

(Development only: `pytest` and `coverage`, for running the tests.)

## Setting up your Groq API key

1. Get an API key from [Groq](https://console.groq.com/).
2. Create a file named `.env` in this folder containing:

   ```env
   GROQ_API_KEY=your-real-key-here
   ```

Never commit your `.env` file or share your API key — it's already
listed in `.gitignore` so Git will ignore it.

## Installing

From inside this project folder, with your virtual environment
active:

```bash
python -m pip install .
```

This installs the project and creates a `chat` command you can run
from anywhere (while the virtual environment is active).

## Running it

```bash
chat
```

Type a message and press Enter. The assistant will reply, and you
can keep the conversation going:

```text
chat> My favorite color is blue.
Got it!

chat> What is my favorite color?
Your favorite color is blue.
```

## Exiting

Press `Ctrl+C`, or `Ctrl+D` (end-of-input), to quit. Both exit
cleanly without showing an error.
