"""Grading, pass@1 / pass^k and failure classification."""
import json
import re

NUM_RE = re.compile(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?")
REFUSAL_WORDS = ("not available", "does not contain", "doesn't contain", "no such column",
                 "cannot", "can't", "not possible", "no column", "missing", "not in the database")


def extract_numbers(text):
    return [float(m.replace(",", "")) for m in NUM_RE.findall(text or "")]


def _num_found(expected, numbers):
    tol = max(0.011, abs(expected) * 0.005)  # 0.5% or one cent
    return any(abs(n - expected) <= tol for n in numbers)


def _matches(expected_list, text):
    nums = extract_numbers(text)
    for e in expected_list:
        if isinstance(e, (int, float)):
            if not _num_found(float(e), nums):
                return False
        elif str(e).lower() not in (text or "").lower():
            return False
    return True


def _good_sql_calls(record):
    return [c for c in record.get("tool_calls", []) if c["name"] == "run_sql" and c["ok"]]


def grade(question, record):
    """-> (passed, reason)"""
    if record["status"] != "ok":
        return False, record["status"]
    text = record.get("final_answer") or ""
    if question["type"] == "refuse":
        declined = record.get("answerable") is False or any(w in text.lower() for w in REFUSAL_WORDS) \
            and record.get("answerable") is not True
        return (True, "declined") if declined else (False, "hallucinated_answer")
    if not _good_sql_calls(record):
        return False, "no_tool_use"
    if _matches(question["expected"], text):
        return True, "match"
    return False, "wrong_answer"


def metrics(results):
    """results: {question_id: [bool, bool, bool]} -> pass@1, pass^k, pass@k(any)."""
    n_q = len(results)
    trials = [t for ts in results.values() for t in ts]
    return {
        "questions": n_q,
        "trials_per_question": len(next(iter(results.values()))),
        "pass_at_1": sum(trials) / len(trials),
        "pass_pow_k": sum(all(ts) for ts in results.values()) / n_q,
        "pass_at_k_any": sum(any(ts) for ts in results.values()) / n_q,
    }


def classify_failure(question, record):
    """Group failed runs into a few named types."""
    if record["status"] in ("step_cap", "budget_cap"):
        return record["status"]
    if record["status"] == "error":
        return "backend_error"
    if question["type"] == "refuse":
        return "hallucinated_answer"
    if record.get("answerable") is False:
        return "wrong_refusal"
    good = _good_sql_calls(record)
    if not good:
        return "no_tool_use"
    errors = [c for c in record["tool_calls"] if c["name"] == "run_sql" and not c["ok"]]
    last_numbers = extract_numbers(good[-1]["result"])
    exp = [e for e in question["expected"] if isinstance(e, (int, float))]
    if exp and all(_num_found(float(e), last_numbers) for e in exp):
        return "answer_misreported"  # the SQL result was right, the final sentence was wrong
    if errors:
        return "sql_error_then_wrong"
    return "wrong_sql_logic"
