"""The agent loop, written by hand (no agent SDK / framework).

One turn = ask the model for ONE json action -> run the tool -> show the
result back to the model. Stops on: final answer (ok), step cap, token
budget, or backend error.
"""
import json
import re
import time

import sql_tools
from agentlab.lm import Ledger

MAX_STEPS = 8
TOKEN_BUDGET = 20000
OBS_LIMIT = 1500  # max characters of a tool result shown to the model

SYSTEM = """You are a data analyst agent for a SQLite shop database (tables: customers, products, orders, order_items).
You must NEVER guess or invent numbers. Every number in your answer must come from a tool result.

TOOLS (call exactly one per turn):
1. generate_sql  args: {"question": "<plain English question for the SQL writer>"}  -> returns a SQL SELECT query
2. run_sql       args: {"sql": "<SELECT query>"}  -> returns rows, or an error message
3. calculator    args: {"expression": "<arithmetic>"}  -> exact arithmetic (use it for percentages and differences)
4. list_tables   args: {}  -> tables and column names

Each turn reply with ONE JSON object and nothing else:
  {"tool": "<tool name>", "args": {...}}
When you have the answer:
  {"final": "<one clear sentence containing the numbers>", "answerable": true}
If the database does not contain the data needed (for example a column that does not exist), do not make up a number. Finish with:
  {"final": "<explain what is missing>", "answerable": false}

Typical flow: generate_sql -> run_sql -> (calculator if you need a percentage or difference) -> final.
If run_sql returns an error, call generate_sql again and put the error text in the question."""

SQL_WRITER_BASELINE = """You write SQLite queries. Database schema:

{schema}

Reply with ONE SQL SELECT query only. No explanation, no markdown."""

SQL_WRITER_IMPROVED = """You write SQLite queries. Database schema:

{schema}

Rules:
- Use ONLY the tables and columns shown above. Never invent a column.
- Revenue = SUM(order_items.quantity * order_items.unit_price). It lives in order_items; join orders / products / customers through the ids.
- Do not filter on orders.status unless the question mentions a status.
- Dates are text 'YYYY-MM-DD'; the year is substr(order_date, 1, 4).
- If the question needs data that is not in the schema (age, profit, cost, ratings...), reply exactly: NOT_AVAILABLE

Examples:
Q: How many products are there?
SELECT COUNT(*) FROM products
Q: Total revenue of customer 5?
SELECT SUM(oi.quantity * oi.unit_price) FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE o.customer_id = 5
Q: Number of orders per city?
SELECT c.city, COUNT(*) FROM orders o JOIN customers c ON c.id = o.customer_id GROUP BY c.city

Reply with ONE SQL SELECT query only. No explanation, no markdown."""


def parse_action(text):
    """First JSON object in the model's reply, or None."""
    text = text.strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _short(obj):
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= OBS_LIMIT else s[:OBS_LIMIT] + "...(cut)"


def _generate_sql(question, backend, ledger, variant):
    """Tool 1: its own model call that turns a question into SQL."""
    template = SQL_WRITER_IMPROVED if variant == "improved" else SQL_WRITER_BASELINE
    messages = [{"role": "system", "content": template.format(schema=sql_tools.schema_text())},
                {"role": "user", "content": str(question)}]
    resp = backend.chat(messages, json_mode=False)
    ledger.add(resp)
    sql = sql_tools.clean_sql(resp["content"])
    return sql


def run_agent(question, backend, db_path, max_steps=MAX_STEPS, token_budget=TOKEN_BUDGET,
              variant="improved"):
    ledger = Ledger()
    t0 = time.time()
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    rec = {"question": question, "variant": variant, "tool_calls": [], "sql_written": [],
           "final_answer": None, "answerable": None, "status": None, "error": None,
           "bad_json": 0, "steps": 0}

    status = "step_cap"  # if the for-loop ends without break, we hit the cap
    for step in range(1, max_steps + 1):
        rec["steps"] = step
        try:
            resp = backend.chat(messages, json_mode=True)
        except Exception as e:  # network down, model missing, timeout...
            status, rec["error"] = "error", f"{type(e).__name__}: {e}"
            break
        ledger.add(resp)
        content = resp["content"]
        messages.append({"role": "assistant", "content": content})
        action = parse_action(content)

        if action is None:
            rec["bad_json"] += 1
            messages.append({"role": "user", "content":
                             'Invalid reply. Answer with ONE JSON object: {"tool": ..., "args": ...} or {"final": ...}.'})
        elif "final" in action:
            rec["final_answer"] = str(action["final"])
            rec["answerable"] = bool(action.get("answerable", True))
            status = "ok"
            break
        else:
            name, args = action.get("tool"), action.get("args") or {}
            ok, result = _call_tool(name, args, backend, ledger, db_path, variant, rec)
            rec["tool_calls"].append({"name": name, "args": args, "ok": ok, "result": _short(result)})
            messages.append({"role": "user", "content": f"Tool result ({name}): {_short(result)}"})

        if ledger.total >= token_budget:
            status = "budget_cap"
            break

    rec["status"] = status
    rec["prompt_tokens"] = ledger.prompt_tokens
    rec["completion_tokens"] = ledger.completion_tokens
    rec["total_tokens"] = ledger.total
    rec["model_calls"] = len(ledger.calls)
    rec["time_s"] = round(time.time() - t0, 2)
    return rec


def _call_tool(name, args, backend, ledger, db_path, variant, rec):
    """Returns (ok, result). Never raises for bad tool input."""
    if not isinstance(args, dict):
        return False, "args must be a JSON object"
    if name == "generate_sql":
        if "question" not in args:
            return False, 'generate_sql needs {"question": ...}'
        try:
            sql = _generate_sql(args["question"], backend, ledger, variant)
        except Exception as e:
            return False, f"SQL writer failed: {e}"
        rec["sql_written"].append(sql)
        return True, sql
    if name == "run_sql":
        result = sql_tools.run_sql(db_path, args.get("sql", ""))
        return result["ok"], result if result["ok"] else result["error"]
    if name == "calculator":
        result = sql_tools.calculator(args.get("expression", ""))
        return result["ok"], result["result"] if result["ok"] else result["error"]
    if name == "list_tables":
        return True, sql_tools.list_tables(db_path)["tables"]
    return False, f"Unknown tool {name!r}. Use generate_sql, run_sql, calculator or list_tables."
