# Assignment 1 - SQL calculation agent (Python + Ollama)

An agent (own loop, no framework) answers calculation questions by calling tools
against a SQLite database with dummy data. Model: **Qwen2.5 3B** served by Ollama.

Default model tag: `qwen2.5:3b` (the official Ollama tag, no export needed).
The numbers in `results/` and `report.md` were produced with the equivalent GGUF build
`hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M`; to use exactly that one, run
`export OLLAMA_MODEL=hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M` first.

## Run everything in 5 commands

Needs: Python 3.9+ (standard library only, nothing to `pip install`) and Ollama.

```bash
# 0. (once) start Ollama and get the model - keep Ollama running in the background
ollama pull qwen2.5:3b

cd Assignment_1
python3 -m unittest discover -s tests -t .      # 1. tests (no Ollama needed)
python3 build_db.py                             # 2. build data/shop.db (seed 42)
python3 make_questions.py                       # 3. questions.json, answers computed by our own SQL
python3 run_eval.py --variant baseline --trials 3   # 4. before-change numbers  -> results/baseline/
python3 run_eval.py --variant improved --trials 3   # 5. after-change numbers   -> results/improved/
```

Each evaluation takes roughly 10-20 minutes (18 questions x 3 trials).
Quick check on 2 questions: `python3 run_eval.py --only q01,q05 --trials 1 --out /tmp/quick`.

Ask one question yourself:

```bash
python3 -c "import agent, json; from agentlab.lm import OllamaBackend; \
print(json.dumps(agent.run_agent('How many customers are there?', OllamaBackend(), 'data/shop.db'), indent=1))"
```

## Files

| File | What it is |
|---|---|
| `build_db.py` | creates + fills the database (4 tables, 999 rows in the biggest, seed 42) |
| `sql_tools.py` | `run_sql` (SELECT-only, read-only, row limit), `calculator`, `list_tables` |
| `agent.py` | the hand-written agent loop + `generate_sql` tool (step cap, token cap, status) |
| `agentlab/lm.py` | Ollama wrapper + token ledger |
| `grading.py` | answer checking, pass@1, pass^3, failure types |
| `make_questions.py`, `questions.json` | 18 questions with expected answers from our own SQL |
| `run_eval.py` | runs each question 3 times, writes the run log and summary |
| `tests/` | unit tests (fake model backend) |
| `results/<variant>/runs.jsonl` | run log: one record per run (question, tool calls, SQL, answer, status, tokens, time) |
| `results/<variant>/summary.md` / `summary.json` | numbers per variant |
| `report.md` | the 1-2 page report |
| `AI_LOG.md` | short AI-assistant log |
| `Learn.txt` | explanation of how/why everything was done (for the viva) |

## Settings

Step cap 8, token budget 20 000, temperature 0.3 (no seed, so the 3 trials can differ),
max 400 generated tokens per call, SELECT row limit 50. Change them in `agent.py` / `agentlab/lm.py`.
Because the model is not deterministic, your numbers will be close to, not identical to, the report.
