import hashlib
import os
import sqlite3
import tempfile
import unittest

import build_db


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "shop.db")
        build_db.build(self.path)

    def counts(self, path):
        con = sqlite3.connect(path)
        out = {}
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            out[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        con.close()
        return out

    def test_at_least_three_related_tables(self):
        self.assertGreaterEqual(len(self.counts(self.path)), 3)

    def test_biggest_table_has_100_rows_or_more(self):
        self.assertGreaterEqual(max(self.counts(self.path).values()), 100)

    def test_same_seed_gives_same_data(self):
        other = os.path.join(self.tmp, "again.db")
        build_db.build(other)
        self.assertEqual(self.dump(self.path), self.dump(other))

    def dump(self, path):
        con = sqlite3.connect(path)
        text = "\n".join(con.iterdump())
        con.close()
        return hashlib.sha256(text.encode()).hexdigest()

    def test_foreign_keys_are_consistent(self):
        con = sqlite3.connect(self.path)
        bad = con.execute(
            "SELECT COUNT(*) FROM order_items oi LEFT JOIN orders o ON o.id=oi.order_id "
            "WHERE o.id IS NULL"
        ).fetchone()[0]
        self.assertEqual(bad, 0)


if __name__ == "__main__":
    unittest.main()
