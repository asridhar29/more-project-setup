"""The tools package: small, focused functions the chatbot can call.

Each file in this folder implements one tool that either the AI model
or the person typing in the terminal can run: looking at files
(`ls`, `cat`), searching inside them (`grep`), doing math
(`calculate`), shrinking the conversation (`compact`), or adding a
picture to the conversation (`load_image`). Keeping every tool in its
own small file makes each one easy to read on its own.
"""
