"""Tiny wrapper around the local Ollama server (standard library only).

Every call returns the text AND the token counts Ollama reports, so the
agent can keep a ledger (tokens per call) and enforce a token budget.
"""
import json
import os
import time
import urllib.request

# Qwen2.5 3B served by Ollama. Override with:  export OLLAMA_MODEL=<other tag>
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


class OllamaBackend:
    def __init__(self, model=DEFAULT_MODEL, host=DEFAULT_HOST, temperature=0.3,
                 max_tokens=400, seed=None, timeout=300):
        self.model = model
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.seed = seed
        self.timeout = timeout

    def chat(self, messages, json_mode=False):
        options = {"temperature": self.temperature, "num_predict": self.max_tokens}
        if self.seed is not None:
            options["seed"] = self.seed
        body = {"model": self.model, "messages": messages, "stream": False, "options": options}
        if json_mode:
            body["format"] = "json"  # forces valid JSON output
        req = urllib.request.Request(
            self.host + "/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        latency = time.time() - t0
        text = data["message"]["content"]
        # Ollama may omit prompt_eval_count when it re-used a cached prompt -> estimate.
        p = data.get("prompt_eval_count")
        if p is None:
            p = max(1, sum(len(m["content"]) for m in messages) // 4)
        return {
            "content": text,
            "prompt_tokens": p,
            "completion_tokens": data.get("eval_count", max(1, len(text) // 4)),
            "latency_s": latency,
        }


class Ledger:
    """Records tokens for every model call of one agent run."""

    def __init__(self):
        self.calls = []

    def add(self, resp):
        self.calls.append(
            {"prompt": resp["prompt_tokens"], "completion": resp["completion_tokens"],
             "latency_s": resp.get("latency_s", 0.0)}
        )

    @property
    def prompt_tokens(self):
        return sum(c["prompt"] for c in self.calls)

    @property
    def completion_tokens(self):
        return sum(c["completion"] for c in self.calls)

    @property
    def total(self):
        return self.prompt_tokens + self.completion_tokens
