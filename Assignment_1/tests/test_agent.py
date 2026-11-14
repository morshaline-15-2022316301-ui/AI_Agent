import json
import os
import tempfile
import unittest

import agent
import build_db
from tests.fakes import FakeBackend


def tool(name, **args):
    return json.dumps({"tool": name, "args": args})


def final(text, answerable=True):
    return json.dumps({"final": text, "answerable": answerable})


class AgentLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.db = os.path.join(cls.tmp, "shop.db")
        build_db.build(cls.db)

    def test_happy_path_uses_tool_results(self):
        be = FakeBackend([
            tool("generate_sql", question="How many customers?"),
            "SELECT COUNT(*) FROM customers",       # the SQL-generator call
            tool("run_sql", sql="SELECT COUNT(*) FROM customers"),
            final("There are 120 customers."),
        ])
        rec = agent.run_agent("How many customers are there?", be, self.db)
        self.assertEqual(rec["status"], "ok")
        self.assertIn("120", rec["final_answer"])
        self.assertEqual([t["name"] for t in rec["tool_calls"]], ["generate_sql", "run_sql"])
        self.assertEqual(rec["sql_written"], ["SELECT COUNT(*) FROM customers"])
        self.assertGreater(rec["total_tokens"], 0)

    def test_step_cap_stops_the_loop(self):
        be = FakeBackend([tool("list_tables")] * 20)
        rec = agent.run_agent("q", be, self.db, max_steps=3)
        self.assertEqual(rec["status"], "step_cap")
        self.assertEqual(rec["steps"], 3)

    def test_budget_cap_stops_the_loop(self):
        be = FakeBackend([tool("list_tables")] * 20, prompt_tokens=900, completion_tokens=200)
        rec = agent.run_agent("q", be, self.db, max_steps=10, token_budget=2000)
        self.assertEqual(rec["status"], "budget_cap")
        self.assertLess(rec["steps"], 10)

    def test_sql_error_is_given_back_and_model_retries(self):
        be = FakeBackend([
            tool("run_sql", sql="SELECT nope FROM customers"),
            tool("run_sql", sql="SELECT COUNT(*) FROM customers"),
            final("120 customers"),
        ])
        rec = agent.run_agent("q", be, self.db)
        self.assertEqual(rec["status"], "ok")
        # the 2nd model call must have seen the error text from the first tool call
        second_call_text = json.dumps(be.calls[1]["messages"])
        self.assertIn("no such column", second_call_text)

    def test_destructive_sql_is_blocked_inside_the_loop(self):
        be = FakeBackend([tool("run_sql", sql="DROP TABLE customers"), final("done")])
        rec = agent.run_agent("q", be, self.db)
        self.assertFalse(rec["tool_calls"][0]["ok"])
        from sql_tools import run_sql
        self.assertTrue(run_sql(self.db, "SELECT COUNT(*) FROM customers")["ok"])

    def test_bad_json_is_recovered(self):
        be = FakeBackend(["this is not json", final("ok then")])
        rec = agent.run_agent("q", be, self.db)
        self.assertEqual(rec["status"], "ok")
        self.assertEqual(rec["bad_json"], 1)

    def test_unknown_tool_is_reported_to_model(self):
        be = FakeBackend([tool("hack_the_planet"), final("sorry", answerable=False)])
        rec = agent.run_agent("q", be, self.db)
        self.assertEqual(rec["status"], "ok")
        self.assertFalse(rec["tool_calls"][0]["ok"])
        self.assertIs(rec["answerable"], False)

    def test_backend_exception_gives_error_status(self):
        be = FakeBackend([RuntimeError("ollama down")])
        rec = agent.run_agent("q", be, self.db)
        self.assertEqual(rec["status"], "error")
        self.assertIn("ollama down", rec["error"])

    def test_calculator_tool(self):
        be = FakeBackend([tool("calculator", expression="(150-100)/100*100"), final("50 percent")])
        rec = agent.run_agent("q", be, self.db)
        self.assertEqual(rec["tool_calls"][0]["name"], "calculator")
        self.assertTrue(rec["tool_calls"][0]["ok"])


if __name__ == "__main__":
    unittest.main()
