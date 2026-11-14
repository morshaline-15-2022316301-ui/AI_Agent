"""Send all 50 English + 50 Bangla prompts with identical settings; record everything.

    python3 runner.py                (writes results/results.jsonl and results/results.csv)
    python3 runner.py --resume       (skip rows already done)
"""
import argparse
import csv
import json
import os
import sys

import cost
import token_counter
from agentlab.lm import DEFAULT_MODEL, OllamaBackend

HERE = os.path.dirname(os.path.abspath(__file__))
# The SAME system prompt for both languages. It does not mention any language.
SYSTEM_PROMPT = "You are a helpful assistant. Keep your answers short."
FIELDS = ["id", "language", "prompt", "output", "input_tokens", "output_tokens", "cost_usd", "latency_s",
          "category", "net_input_tokens", "truncated", "retries"]


def load_dataset(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def run_all(rows, counter, jsonl_path=None, done=None, log=print):
    done = done or set()
    if counter.baseline_input_tokens is None:
        counter.measure_baseline()
    out = open(jsonl_path, "a" if done else "w", encoding="utf-8") if jsonl_path else None
    results = []
    for row in rows:
        # English and Bangla of the same pair are run back to back (same conditions)
        for lang in ("english", "bangla"):
            if (row["id"], lang) in done:
                continue
            r = counter.count(row[lang])
            res = {"id": row["id"], "language": lang, "prompt": row[lang], "output": r["output"],
                   "input_tokens": r["input_tokens"], "output_tokens": r["output_tokens"],
                   "cost_usd": cost.cost_usd(r["input_tokens"], r["output_tokens"]),
                   "latency_s": round(r["latency_s"], 3), "category": row["category"],
                   "net_input_tokens": r["net_input_tokens"], "truncated": r["truncated"],
                   "retries": r["retries"]}
            results.append(res)
            if out:
                out.write(json.dumps(res, ensure_ascii=False) + "\n")
                out.flush()
            log(f"#{row['id']:>2} {lang:7s} in={res['input_tokens']:4d} out={res['output_tokens']:4d} "
                f"{res['latency_s']:.1f}s{' TRUNCATED' if res['truncated'] else ''}")
    if out:
        out.close()
    return results


def write_results_csv(results, path):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow({**r, "cost_usd": format(r["cost_usd"], ".8f")})


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    jsonl = os.path.join(a.out, "results.jsonl")
    previous = read_jsonl(jsonl) if a.resume and os.path.exists(jsonl) else []
    done = {(r["id"], r["language"]) for r in previous}

    rows = load_dataset(os.path.join(HERE, "dataset.tsv"))
    counter = token_counter.TokenCounter(OllamaBackend(model=a.model), SYSTEM_PROMPT,
                                         temperature=0, seed=42, max_tokens=a.max_tokens)
    counter.measure_baseline()
    meta = {"model": a.model, "system_prompt": SYSTEM_PROMPT, "temperature": 0, "seed": 42,
            "max_tokens": a.max_tokens, "baseline_input_tokens_tiny_prompt": counter.baseline_input_tokens,
            "template_overhead_tokens": counter.template_overhead}
    json.dump(meta, open(os.path.join(a.out, "run_meta.json"), "w"), indent=2)
    print("meta:", meta)
    new = run_all(rows, counter, jsonl, done)
    allres = previous + new
    order = {r["id"]: i for i, r in enumerate(rows)}
    allres.sort(key=lambda r: (order[r["id"]], r["language"] != "english"))
    write_results_csv(allres, os.path.join(a.out, "results.csv"))
    print(f"wrote {len(allres)} rows to {a.out}/results.csv")


if __name__ == "__main__":
    sys.exit(main())
