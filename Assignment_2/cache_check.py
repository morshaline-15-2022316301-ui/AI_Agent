"""Shows the prompt-cache effect: same prompt twice WITHOUT unloading vs WITH unloading.
    python3 cache_check.py      -> results/cache_check.json
"""
import json
import os

import runner
from agentlab.lm import OllamaBackend

PROMPT = "Explain how rain is formed."
be = OllamaBackend()
S = dict(temperature=0, seed=42, max_tokens=5)
out = {"prompt": PROMPT, "no_unload": [], "with_unload": []}
be.unload()
for _ in range(3):
    out["no_unload"].append(be.chat(runner.SYSTEM_PROMPT, PROMPT, **S)["prompt_eval_count"])
for _ in range(3):
    be.unload()
    out["with_unload"].append(be.chat(runner.SYSTEM_PROMPT, PROMPT, keep_alive=0, **S)["prompt_eval_count"])
print(out)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "cache_check.json"), "w"), indent=1)
