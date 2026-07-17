"""Application use-case services — orchestrate domain, infrastructure, and AI.

Each use-case encapsulates a single user-visible operation.  The UI calls
these methods and displays the results; it never touches the database,
Ollama client, or domain services directly.
"""
