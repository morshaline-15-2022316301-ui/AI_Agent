import csv
import os
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "dataset.tsv"), encoding="utf-8-sig", newline="") as f:
            cls.rows = list(csv.DictReader(f, delimiter="\t"))

    def test_columns(self):
        self.assertEqual(list(self.rows[0].keys()), ["id", "category", "english", "bangla"])

    def test_fifty_aligned_pairs(self):
        self.assertEqual(len(self.rows), 50)
        self.assertEqual(len({r["id"] for r in self.rows}), 50)

    def test_no_empty_cells(self):
        for r in self.rows:
            for k, v in r.items():
                self.assertTrue(v.strip(), f"empty {k} in id {r['id']}")

    def test_bangla_column_really_is_bangla(self):
        for r in self.rows:
            bn = sum(1 for ch in r["bangla"] if "ঀ" <= ch <= "৿")
            self.assertGreater(bn, 3, r["id"])
            self.assertFalse(any("ঀ" <= ch <= "৿" for ch in r["english"]), r["id"])

    def test_mixed_categories_and_lengths(self):
        cats = {r["category"] for r in self.rows}
        self.assertTrue({"question", "instruction", "explanation", "arithmetic", "summarise", "long"} <= cats)
        lengths = sorted(len(r["english"]) for r in self.rows)
        self.assertGreater(lengths[-1], 4 * lengths[0])      # not all the same length
        longs = [r for r in self.rows if r["category"] == "long"]
        self.assertGreaterEqual(len(longs), 5)
        for r in longs:                                       # 3 to 5 sentences
            n = sum(r["english"].count(c) for c in ".?!")
            self.assertTrue(3 <= n <= 5, f"{r['id']} has {n} sentences")


if __name__ == "__main__":
    unittest.main()
