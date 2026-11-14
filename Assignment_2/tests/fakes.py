"""Fake Ollama backend: token counts come from a simple rule, no network."""


class FakeBackend:
    """chat() returns ollama-like fields. Token rule: 1 token per 4 characters + overhead.

    `drop_prompt_count_times`: simulate Ollama's prompt cache - the first N calls
    come back WITHOUT prompt_eval_count (as if the prompt was cached).
    """

    def __init__(self, overhead=20, drop_prompt_count_times=0, out_tokens=7, done_reason="stop"):
        self.overhead = overhead
        self.calls = []
        self.drop = drop_prompt_count_times
        self.out_tokens = out_tokens
        self.done_reason = done_reason
        self.unloads = 0

    def chat(self, system, user, **opts):
        self.calls.append({"system": system, "user": user, "opts": dict(opts)})
        count = self.overhead + max(1, len(user) // 4)
        if self.drop > 0:
            self.drop -= 1
            count = None
        return {"content": "answer: " + user[:10], "prompt_eval_count": count,
                "eval_count": self.out_tokens, "done_reason": self.done_reason,
                "latency_s": 0.5}

    def unload(self):
        self.unloads += 1
