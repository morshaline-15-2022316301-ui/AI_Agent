import os
import sqlite3
import tempfile
import unittest

import build_db
import sql_tools


class ExecutorSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "shop.db")
        build_db.build(cls.path)

    def test_select_works(self):
        r = sql_tools.run_sql(self.path, "SELECT COUNT(*) AS n FROM customers")
        self.assertTrue(r["ok"])
        self.assertEqual(r["columns"], ["n"])
        self.assertEqual(r["rows"][0][0], 120)

    def test_non_select_statements_are_rejected(self):
        for bad in [
            "DROP TABLE customers",
            "DELETE FROM customers",
            "UPDATE customers SET name='x'",
            "INSERT INTO customers (name) VALUES ('x')",
            "drop table customers",
            "  \n DELETE FROM orders",
        ]:
            r = sql_tools.run_sql(self.path, bad)
            self.assertFalse(r["ok"], bad)
            self.assertIn("SELECT", r["error"])

    def test_multiple_statements_are_rejected(self):
        r = sql_tools.run_sql(self.path, "SELECT 1; DROP TABLE customers")
        self.assertFalse(r["ok"])
        r = sql_tools.run_sql(self.path, "SELECT 1; SELECT 2")
        self.assertFalse(r["ok"])

    def test_trailing_semicolon_is_fine(self):
        self.assertTrue(sql_tools.run_sql(self.path, "SELECT 1;")["ok"])

    def test_data_is_unchanged_after_attacks(self):
        sql_tools.run_sql(self.path, "DROP TABLE customers")
        sql_tools.run_sql(self.path, "SELECT 1; DELETE FROM orders")
        self.assertEqual(sql_tools.run_sql(self.path, "SELECT COUNT(*) FROM customers")["rows"][0][0], 120)

    def test_database_is_opened_read_only(self):
        con = sql_tools.open_readonly(self.path)
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("DELETE FROM customers")
        con.close()

    def test_row_limit_is_applied(self):
        r = sql_tools.run_sql(self.path, "SELECT * FROM order_items", max_rows=10)
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["rows"]), 10)
        self.assertTrue(r["truncated"])

    def test_sql_error_comes_back_as_text(self):
        r = sql_tools.run_sql(self.path, "SELECT nope FROM customers")
        self.assertFalse(r["ok"])
        self.assertIn("no such column", r["error"])


class CalculatorTests(unittest.TestCase):
    def test_basic_math(self):
        self.assertEqual(sql_tools.calculator("(10 + 5) * 2")["result"], 30)
        self.assertAlmostEqual(sql_tools.calculator("(150-100)/100*100")["result"], 50.0)

    def test_round(self):
        self.assertEqual(sql_tools.calculator("round(10/3, 2)")["result"], 3.33)

    def test_rejects_code(self):
        self.assertFalse(sql_tools.calculator("__import__('os').system('ls')")["ok"])
        self.assertFalse(sql_tools.calculator("open('x')")["ok"])

    def test_division_by_zero(self):
        self.assertFalse(sql_tools.calculator("1/0")["ok"])


class CleanSqlTests(unittest.TestCase):
    def test_strips_code_fences(self):
        self.assertEqual(sql_tools.clean_sql("```sql\nSELECT 1;\n```"), "SELECT 1")

    def test_plain(self):
        self.assertEqual(sql_tools.clean_sql("  SELECT 2  "), "SELECT 2")


if __name__ == "__main__":
    unittest.main()
