"""Ollama client for the token-cost experiment (standard library only).

Returns Ollama's OWN counts:  prompt_eval_count (input) and eval_count (output).
`prompt_eval_count` is None when Ollama reused a cached prompt - the caller must handle it.
"""
import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


class OllamaBackend:
    def __init__(self, model=DEFAULT_MODEL, host=DEFAULT_HOST, timeout=600):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def _post(self, path, body):
        req = urllib.request.Request(self.host + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        for attempt in range(4):   # Ollama sometimes answers 500 right after an unload; retry
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError:
                if attempt == 3:
                    raise
                time.sleep(3)

    def chat(self, system, user, temperature=0, seed=42, max_tokens=256, keep_alive=None):
        body = {"model": self.model, "stream": False,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "options": {"temperature": temperature, "seed": seed, "num_predict": max_tokens}}
        if keep_alive is not None:
            body["keep_alive"] = keep_alive
        t0 = time.time()
        d = self._post("/api/chat", body)
        wall = time.time() - t0
        # latency = generation time only (model loading time is removed)
        if "total_duration" in d and "load_duration" in d:
            latency = (d["total_duration"] - d["load_duration"]) / 1e9
        else:
            latency = wall
        return {"content": d["message"]["content"],
                "prompt_eval_count": d.get("prompt_eval_count"),   # None => cached prompt
                "eval_count": d.get("eval_count", 0),
                "done_reason": d.get("done_reason"),
                "done": d.get("done", True),   # False = Ollama dropped the final chunk (see token_counter)
                "latency_s": latency, "wall_s": wall,
                "load_s": d.get("load_duration", 0) / 1e9}

    def unload(self):
        """Unload the model from memory => next call starts with an empty prompt cache."""
        self._post("/api/generate", {"model": self.model, "keep_alive": 0})
