# Assignment 2 - English vs Bangla token cost (Python + Ollama)

Measures how many more tokens (and notional dollars) a Bangla prompt costs than an English prompt with
the same meaning, using Qwen2.5 3B through Ollama. Standard library only - nothing to `pip install`.

Model tag used: `qwen2.5:3b` (official Ollama tag, the default in `agentlab/lm.py`). Pull it with `ollama pull qwen2.5:3b`.
To use another model, set `OLLAMA_MODEL` before running.

## Reproduce in 5 commands
Ollama must be running (`ollama serve` or the desktop app) and the model pulled.

Run these from inside the project folder (the one that contains `runner.py`). Commands only, no comments, so they can be pasted into zsh/bash:

```bash
python3 -m unittest discover -s tests -t .
python3 build_dataset.py
python3 runner.py
python3 compare.py
python3 cache_check.py
```
1. tests (fake backend, no Ollama needed)
2. writes `dataset.tsv` (50 aligned pairs)
3. 100 calls -> `results/results.jsonl` + `results/results.csv` (~5-8 min)
4. `comparison.csv`, `results/summary.md`, `ratio_chart.svg`
5. (optional) prompt-cache demonstration
If the runner stops halfway, continue with `python3 runner.py --resume`.
Open `report.md` for the table, chart and conclusions.

## Files
| File | Purpose |
|---|---|
| `dataset.tsv` / `build_dataset.py` | 50 English + 50 Bangla prompts (id, category, english, bangla) |
| `token_counter.py` | reusable token counting: Ollama counts, template baseline, fresh state, cache retry, recovery |
| `cost.py` | notional prices ($0.15 / $0.60 per million) |
| `runner.py` | sends all prompts with identical settings, saves every input and output |
| `compare.py` | per-pair / per-category / overall ratios, 95% bootstrap CI, chart |
| `agentlab/lm.py` | Ollama client |
| `results.csv` (in `results/`) | one row per call: id, language, prompt, output, input_tokens, output_tokens, cost_usd, latency_s |
| `comparison.csv` | one row per pair with tokens and ratios |
| `report.md`, `quality_check.md`, `ratio_chart.svg` | report, 10-pair quality check, chart |

## Settings (same for both languages)
temperature 0, seed 42, max_tokens 256, system prompt "You are a helpful assistant. Keep your answers short."
(no language instruction). Prices are notional. Numbers should be very close on rerun (temperature 0 + seed), but
can differ slightly with another Ollama version.

