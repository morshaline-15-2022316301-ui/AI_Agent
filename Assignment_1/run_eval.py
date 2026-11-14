"""Run every question N times, grade, and write the run log + summary.

    python3 run_eval.py --variant improved --trials 3
Outputs (in results/<variant>/): runs.jsonl, summary.json, summary.md
"""
import argparse
import json
import os
import sqlite3
import statistics
import time
from collections import Counter, defaultdict

import agent
import build_db
import grading
from agentlab.lm import DEFAULT_MODEL, OllamaBackend

HERE = os.path.dirname(os.path.abspath(__file__))


def evaluate(questions, backend, db_path, trials, variant, runs_path=None, max_steps=agent.MAX_STEPS,
             token_budget=agent.TOKEN_BUDGET, log=print):
    results, failures, records = defaultdict(list), [], []
    out = open(runs_path, "w") if runs_path else None
    for q in questions:
        for t in range(1, trials + 1):
            rec = agent.run_agent(q["question"], backend, db_path, max_steps, token_budget, variant)
            passed, reason = grading.grade(q, rec)
            rec.update({"question_id": q["id"], "trial": t, "expected": q["expected"],
                        "passed": passed, "grade_reason": reason})
            if not passed:
                rec["failure_type"] = grading.classify_failure(q, rec)
                failures.append(rec)
            results[q["id"]].append(passed)
            records.append(rec)
            if out:
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
            log(f"{q['id']} trial {t}: {'PASS' if passed else 'FAIL'} ({reason}) "
                f"steps={rec['steps']} tokens={rec['total_tokens']} {rec['time_s']}s")
    if out:
        out.close()
    return results, failures, records


def summarize(questions, results, failures, records, model, variant, trials):
    m = grading.metrics(results)
    types = Counter(f["failure_type"] for f in failures)
    examples = {}
    for f in failures:
        examples.setdefault(f["failure_type"], f)
    per_q = {q["id"]: {"question": q["question"], "category": q["category"],
                       "passes": sum(results[q["id"]]), "trials": trials} for q in questions}
    by_cat = defaultdict(list)
    for q in questions:
        by_cat[q["category"]] += results[q["id"]]
    return {
        "model": model, "variant": variant, "trials": trials, **m,
        "per_question": per_q,
        "per_category_pass_rate": {c: sum(v) / len(v) for c, v in by_cat.items()},
        "failure_types": dict(types.most_common()),
        "failure_examples": {t: {"question": e["question"], "final_answer": e["final_answer"],
                                 "sql_written": e["sql_written"], "status": e["status"],
                                 "expected": e["expected"]} for t, e in examples.items()},
        "tokens_mean_per_run": statistics.mean(r["total_tokens"] for r in records),
        "time_mean_per_run_s": statistics.mean(r["time_s"] for r in records),
        "status_counts": dict(Counter(r["status"] for r in records)),
    }


def to_markdown(s):
    L = [f"# Results: variant `{s['variant']}`", "",
         f"- model: `{s['model']}`",
         f"- questions: {s['questions']}, trials each: {s['trials']}",
         f"- **pass@1 = {s['pass_at_1']:.3f}**  (average success of a single run)",
         f"- **pass^{s['trials']} = {s['pass_pow_k']:.3f}**  (question solved in ALL {s['trials']} runs)",
         f"- pass@{s['trials']} (any of {s['trials']}) = {s['pass_at_k_any']:.3f}",
         f"- mean tokens per run: {s['tokens_mean_per_run']:.0f}; mean time per run: {s['time_mean_per_run_s']:.1f}s",
         f"- run statuses: {s['status_counts']}", "",
         "| id | category | passes | question |", "|---|---|---|---|"]
    for qid, p in s["per_question"].items():
        L.append(f"| {qid} | {p['category']} | {p['passes']}/{p['trials']} | {p['question'][:70]} |")
    L += ["", "## Failure types (most common first)", ""]
    for t, n in s["failure_types"].items():
        e = s["failure_examples"][t]
        L += [f"- **{t}**: {n} runs. Example: \"{e['question'][:70]}\" -> SQL {e['sql_written']} "
              f"-> answer \"{(e['final_answer'] or '')[:100]}\" (expected {e['expected']})"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["baseline", "improved"], default="improved")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--temperature", type=float, default=0.3)
    ap.add_argument("--only", help="comma separated question ids (quick test)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    db = os.path.join(HERE, "data", "shop.db")
    if not os.path.exists(db):
        build_db.build(db)
    questions = json.load(open(os.path.join(HERE, "questions.json")))
    if a.only:
        questions = [q for q in questions if q["id"] in a.only.split(",")]
    out_dir = a.out or os.path.join(HERE, "results", a.variant)
    os.makedirs(out_dir, exist_ok=True)

    backend = OllamaBackend(model=a.model, temperature=a.temperature)
    t0 = time.time()
    results, failures, records = evaluate(questions, backend, db, a.trials, a.variant,
                                          os.path.join(out_dir, "runs.jsonl"))
    s = summarize(questions, results, failures, records, a.model, a.variant, a.trials)
    json.dump(s, open(os.path.join(out_dir, "summary.json"), "w"), indent=2, ensure_ascii=False)
    open(os.path.join(out_dir, "summary.md"), "w").write(to_markdown(s))
    print(to_markdown(s))
    print(f"total time {time.time() - t0:.0f}s -> {out_dir}")


if __name__ == "__main__":
    main()
