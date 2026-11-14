"""Reusable token counting system on top of Ollama's own counters.

Handles the two traps from the assignment:
 1. TEMPLATE OVERHEAD - the chat template + system prompt add tokens to every call.
    We use the SAME fixed system prompt for all calls, measure the overhead ONCE with a
    tiny prompt (".") and report both gross (what Ollama bills) and net (prompt only) tokens.
 2. PROMPT CACHING - Ollama re-uses the evaluated prompt prefix, so prompt_eval_count can be
    smaller (or missing) on a repeat. We unload the model before every call (fresh state) and
    also check: if the count is missing, we unload and retry.
"""

TINY_PROMPT = "."


class TokenCounter:
    def __init__(self, backend, system_prompt, max_retries=3, **settings):
        self.backend = backend
        self.system = system_prompt
        self.max_retries = max_retries
        self.settings = {"temperature": 0, "seed": 42, "max_tokens": 256, **settings}
        self.baseline_input_tokens = None

    @property
    def template_overhead(self):
        """Tokens added by chat template + system prompt (tiny prompt counted as 1 token)."""
        return None if self.baseline_input_tokens is None else self.baseline_input_tokens - 1

    def measure_baseline(self):
        r = self._call(TINY_PROMPT, {**self.settings, "max_tokens": 1})
        self.baseline_input_tokens = r["input_tokens"]
        return self.baseline_input_tokens

    def _call(self, prompt, settings):
        retries = 0
        while True:
            self.backend.unload()  # fresh state: no cached prompt
            resp = self.backend.chat(self.system, prompt, keep_alive=0, **settings)
            if resp.get("prompt_eval_count") is not None:
                break
            retries += 1  # prompt came from cache -> count is unusable
            if retries > self.max_retries:
                if resp.get("done") is False:
                    return self._recover(prompt, settings, resp, retries)
                raise RuntimeError("Ollama never returned prompt_eval_count (prompt cache?)")
        n_in = resp["prompt_eval_count"]
        overhead = self.template_overhead or 0
        return {
            "output": resp["content"],
            "input_tokens": n_in,
            "net_input_tokens": n_in - overhead,
            "output_tokens": resp["eval_count"],
            "truncated": resp.get("done_reason") == "length",
            "latency_s": resp["latency_s"],
            "retries": retries,
        }

    def _recover(self, prompt, settings, broken, retries):
        """Ollama quirk: when generation ends in the middle of a multi-byte character (happens
        with Bangla) it drops the final chunk, so there are no counts at all. We recover EXACT
        counts with probe calls: input = a 1-token call; output = the smallest max_tokens for
        which the reply comes back broken (binary search)."""
        def probe(k):
            self.backend.unload()
            return self.backend.chat(self.system, prompt, keep_alive=0, **{**settings, "max_tokens": k})
        n_in = probe(1)["prompt_eval_count"]
        lo, hi = 1, settings["max_tokens"]          # hi is known to be "broken" (>= real length)
        while lo < hi:
            mid = (lo + hi) // 2
            if probe(mid).get("prompt_eval_count") is None:
                hi = mid
            else:
                lo = mid + 1
        overhead = self.template_overhead or 0
        return {"output": broken["content"], "input_tokens": n_in, "net_input_tokens": n_in - overhead,
                "output_tokens": lo, "truncated": False, "latency_s": broken["latency_s"],
                "retries": retries, "recovered": True}

    def count(self, prompt):
        return self._call(prompt, self.settings)
