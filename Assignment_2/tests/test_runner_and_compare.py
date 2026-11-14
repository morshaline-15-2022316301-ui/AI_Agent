import csv
import os
import tempfile
import unittest

import compare
import runner
import token_counter
from tests.fakes import FakeBackend

ROWS = [
    {"id": "1", "category": "question", "english": "a" * 40, "bangla": "b" * 120},
    {"id": "2", "category": "long", "english": "c" * 80, "bangla": "d" * 160},
]


class RunnerTests(unittest.TestCase):
    def run_it(self):
        be = FakeBackend(overhead=0)
        tc = token_counter.TokenCounter(be, "SYS")
        tmp = tempfile.mkdtemp()
        res = runner.run_all(ROWS, tc, os.path.join(tmp, "results.jsonl"))
        return be, res, tmp

    def test_one_result_per_language_per_pair(self):
        be, res, _ = self.run_it()
        self.assertEqual(len(res), 4)
        self.assertEqual(sorted((r["id"], r["language"]) for r in res),
                         [("1", "bangla"), ("1", "english"), ("2", "bangla"), ("2", "english")])

    def test_same_settings_and_system_prompt_for_both_languages(self):
        be, _, _ = self.run_it()
        self.assertEqual(len({c["system"] for c in be.calls}), 1)
        calls = be.calls[1:]          # call 0 is the tiny baseline probe (max_tokens=1)
        first = calls[0]["opts"]
        for c in calls:
            self.assertEqual(c["opts"], first)

    def test_every_input_and_output_is_recorded(self):
        _, res, tmp = self.run_it()
        for r in res:
            for k in ("id", "language", "prompt", "output", "input_tokens", "output_tokens", "cost_usd", "latency_s"):
                self.assertIn(k, r)
        runner.write_results_csv(res, os.path.join(tmp, "results.csv"))
        with open(os.path.join(tmp, "results.csv"), encoding="utf-8-sig") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 4)


def result(i, lang, inp, out):
    import cost
    return {"id": str(i), "category": "question" if i == 1 else "long", "language": lang,
            "input_tokens": inp, "net_input_tokens": inp - 10, "output_tokens": out,
            "cost_usd": cost.cost_usd(inp, out), "latency_s": 1.0 if lang == "english" else 2.0}


RESULTS = [result(1, "english", 30, 10), result(1, "bangla", 90, 20),
           result(2, "english", 50, 10), result(2, "bangla", 100, 30)]


class CompareTests(unittest.TestCase):
    def test_pair_ratios(self):
        pairs = compare.build_pairs(RESULTS)
        self.assertEqual(len(pairs), 2)
        self.assertAlmostEqual(pairs[0]["input_ratio"], 3.0)
        self.assertAlmostEqual(pairs[1]["input_ratio"], 2.0)
        self.assertAlmostEqual(pairs[0]["output_ratio"], 2.0)
        self.assertAlmostEqual(pairs[0]["total_cost_ratio"],
                               (90 * 0.15 + 20 * 0.60) / (30 * 0.15 + 10 * 0.60))

    def test_summary_numbers(self):
        s = compare.summarize(compare.build_pairs(RESULTS))
        self.assertAlmostEqual(s["input_ratio"]["mean"], 2.5)
        self.assertAlmostEqual(s["input_ratio"]["median"], 2.5)
        self.assertEqual(s["input_ratio"]["min"], 2.0)
        self.assertEqual(s["input_ratio"]["max"], 3.0)
        self.assertAlmostEqual(s["overall_input_ratio"], 190 / 80)
        self.assertAlmostEqual(s["total_tokens"]["english_input"], 80)
        self.assertAlmostEqual(s["latency"]["english_mean"], 1.0)
        self.assertAlmostEqual(s["latency"]["bangla_mean"], 2.0)

    def test_bootstrap_interval_is_sane_and_reproducible(self):
        values = [2.0, 2.5, 3.0, 3.5, 4.0, 2.2, 2.8, 3.1]
        lo, hi = compare.bootstrap_ci(values, seed=1)
        mean = sum(values) / len(values)
        self.assertLessEqual(lo, mean)
        self.assertGreaterEqual(hi, mean)
        self.assertGreater(lo, min(values))
        self.assertLess(hi, max(values))
        self.assertEqual((lo, hi), compare.bootstrap_ci(values, seed=1))

    def test_category_table(self):
        cats = compare.by_category(compare.build_pairs(RESULTS))
        self.assertAlmostEqual(cats["question"]["input_ratio_mean"], 3.0)
        self.assertAlmostEqual(cats["long"]["input_ratio_mean"], 2.0)


if __name__ == "__main__":
    unittest.main()
