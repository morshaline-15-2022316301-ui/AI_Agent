"""Tool implementations: read-only SQL executor, calculator, schema helpers."""
import ast
import operator
import re
import sqlite3

import build_db

MAX_ROWS = 50


def open_readonly(db_path):
    """SQLite read-only mode: even if our checks failed, writes are impossible."""
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def run_sql(db_path, sql, max_rows=MAX_ROWS):
    """Run ONE select statement. Returns a dict; never raises."""
    if not isinstance(sql, str) or not sql.strip():
        return {"ok": False, "error": "Empty SQL. Send a SELECT statement."}
    statement = sql.strip().rstrip(";").strip()
    if ";" in statement:
        return {"ok": False, "error": "Only ONE statement is allowed (no ';' inside)."}
    if not re.match(r"(?is)^select\b", statement):
        return {"ok": False, "error": "Only SELECT statements are allowed."}
    try:
        con = open_readonly(db_path)
        try:
            cur = con.execute(statement)
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(max_rows + 1)
        finally:
            con.close()
    except sqlite3.Error as e:
        return {"ok": False, "error": f"SQL error: {e}"}
    truncated = len(rows) > max_rows
    return {"ok": True, "columns": columns, "rows": [list(r) for r in rows[:max_rows]],
            "truncated": truncated}


def clean_sql(text):
    """Model output -> bare SQL (remove ```sql fences and the final ';')."""
    t = text.strip()
    m = re.search(r"```(?:sql)?\s*(.*?)```", t, re.S | re.I)
    if m:
        t = m.group(1).strip()
    return t.rstrip(";").strip()


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.USub: operator.neg, ast.UAdd: operator.pos}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("round", "abs"):
        fn = round if node.func.id == "round" else abs
        return fn(*[_eval(a) for a in node.args])
    raise ValueError("unsupported expression")


def calculator(expression):
    """Safe arithmetic: + - * / ** % ( ) round() abs(). No names, no code."""
    try:
        result = _eval(ast.parse(str(expression).strip(), mode="eval"))
    except ZeroDivisionError:
        return {"ok": False, "error": "division by zero"}
    except Exception as e:  # syntax errors, unsupported nodes
        return {"ok": False, "error": f"cannot calculate: {e}"}
    if isinstance(result, float):
        result = round(result, 6)
    return {"ok": True, "result": result}


def schema_text():
    """The CREATE TABLE statements (what the SQL writer sees)."""
    return build_db.SCHEMA.strip()


def list_tables(db_path):
    con = open_readonly(db_path)
    try:
        out = {}
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            out[t] = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
    finally:
        con.close()
    return {"ok": True, "tables": out}
