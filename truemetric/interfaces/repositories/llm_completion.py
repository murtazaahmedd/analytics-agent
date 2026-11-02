from collections.abc import Callable

Completion = Callable[[list[dict[str, str]]], str]
"""Takes chat messages, returns the model's reply text. LiteLLM in production, a fake in tests."""
