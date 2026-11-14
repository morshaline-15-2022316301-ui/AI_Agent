"""A fake model backend so tests never need Ollama."""


class FakeBackend:
    """Returns scripted replies one by one. Records every call it receives."""

    def __init__(self, replies, prompt_tokens=10, completion_tokens=5):
        self.replies = list(replies)
        self.calls = []
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    def chat(self, messages, json_mode=False):
        self.calls.append({"messages": list(messages), "json_mode": json_mode})
        if not self.replies:
            raise RuntimeError("FakeBackend ran out of scripted replies")
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return {
            "content": item,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_s": 0.0,
        }
