import unittest

import cost
import token_counter
from tests.fakes import FakeBackend

SYSTEM = "You are a helpful assistant."


class CostTests(unittest.TestCase):
    def test_notional_prices(self):
        self.assertAlmostEqual(cost.cost_usd(1_000_000, 0), 0.15)
        self.assertAlmostEqual(cost.cost_usd(0, 1_000_000), 0.60)
        self.assertAlmostEqual(cost.cost_usd(2000, 500), 2000 * 0.15e-6 + 500 * 0.60e-6)

    def test_zero(self):
        self.assertEqual(cost.cost_usd(0, 0), 0)


class TokenCounterTests(unittest.TestCase):
    def test_baseline_overhead_is_measured_once(self):
        be = FakeBackend(overhead=20)
        tc = token_counter.TokenCounter(be, SYSTEM)
        tc.measure_baseline()
        # tiny prompt "." -> 20 overhead + 1 token for the "."
        self.assertEqual(tc.baseline_input_tokens, 21)
        self.assertEqual(tc.template_overhead, 20)

    def test_count_returns_gross_net_and_output(self):
        be = FakeBackend(overhead=20, out_tokens=9)
        tc = token_counter.TokenCounter(be, SYSTEM)
        tc.measure_baseline()
        r = tc.count("x" * 40)                      # 10 prompt tokens + 20 overhead
        self.assertEqual(r["input_tokens"], 30)
        self.assertEqual(r["net_input_tokens"], 10)
        self.assertEqual(r["output_tokens"], 9)
        self.assertFalse(r["truncated"])

    def test_truncation_is_flagged(self):
        be = FakeBackend(done_reason="length")
        tc = token_counter.TokenCounter(be, SYSTEM)
        self.assertTrue(tc.count("hello world")["truncated"])

    def test_every_call_unloads_model_for_a_fresh_state(self):
        be = FakeBackend()
        tc = token_counter.TokenCounter(be, SYSTEM)
        tc.count("a")
        tc.count("b")
        self.assertEqual(be.unloads, 2)

    def test_cached_prompt_is_detected_and_retried(self):
        be = FakeBackend(overhead=20, drop_prompt_count_times=1)
        tc = token_counter.TokenCounter(be, SYSTEM)
        r = tc.count("x" * 40)
        self.assertEqual(r["input_tokens"], 30)     # got a real count on the retry
        self.assertEqual(r["retries"], 1)
        self.assertEqual(len(be.calls), 2)

    def test_recovers_counts_when_ollama_drops_final_chunk(self):
        class Broken(FakeBackend):
            REAL = 13   # real reply length in tokens
            def chat(self, system, user, **opts):
                r = super().chat(system, user, **opts)
                if user == "bad" and opts["max_tokens"] >= self.REAL:
                    r.update(prompt_eval_count=None, eval_count=0, done=False)
                elif user == "bad":
                    r.update(eval_count=opts["max_tokens"], done_reason="length")
                return r
        tc = token_counter.TokenCounter(Broken(overhead=20), SYSTEM, max_retries=1)
        r = tc.count("bad")
        self.assertEqual(r["output_tokens"], 13)
        self.assertEqual(r["input_tokens"], 20 + 1)
        self.assertTrue(r["recovered"])

    def test_gives_up_after_retries(self):
        be = FakeBackend(drop_prompt_count_times=10)
        tc = token_counter.TokenCounter(be, SYSTEM, max_retries=2)
        with self.assertRaises(RuntimeError):
            tc.count("hello")


if __name__ == "__main__":
    unittest.main()
