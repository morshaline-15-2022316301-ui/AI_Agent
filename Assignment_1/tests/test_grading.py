import unittest

import grading


def rec(final="", answerable=True, sql_ok=True, status="ok", result_rows=None, errors=0):
    calls = []
    for _ in range(errors):
        calls.append({"name": "run_sql", "ok": False, "result": "no such column"})
    if sql_ok:
        calls.append({"name": "run_sql", "ok": True, "result": result_rows or "[[120]]"})
    return {"final_answer": final, "answerable": answerable, "status": status, "tool_calls": calls}


class GradeTests(unittest.TestCase):
    def test_number_match(self):
        q = {"type": "answer", "expected": [120]}
        self.assertTrue(grading.grade(q, rec("There are 120 customers."))[0])
        self.assertFalse(grading.grade(q, rec("There are 121 customers."))[0])

    def test_number_with_commas_and_money(self):
        q = {"type": "answer", "expected": [1234.5]}
        self.assertTrue(grading.grade(q, rec("Revenue is $1,234.50"))[0])

    def test_all_expected_values_needed(self):
        q = {"type": "answer", "expected": [10.5, 20.25]}
        self.assertFalse(grading.grade(q, rec("average 10.5"))[0])
        self.assertTrue(grading.grade(q, rec("average 10.5 and 20.25 percent"))[0])

    def test_text_match_case_insensitive(self):
        q = {"type": "answer", "expected": ["Books"]}
        self.assertTrue(grading.grade(q, rec("The top category is books."))[0])

    def test_answer_without_a_successful_tool_call_fails(self):
        q = {"type": "answer", "expected": [120]}
        ok, why = grading.grade(q, rec("120", sql_ok=False))
        self.assertFalse(ok)
        self.assertEqual(why, "no_tool_use")

    def test_non_ok_status_fails(self):
        q = {"type": "answer", "expected": [120]}
        self.assertFalse(grading.grade(q, rec("120", status="step_cap"))[0])

    def test_refuse_question_passes_when_model_declines(self):
        q = {"type": "refuse", "expected": []}
        self.assertTrue(grading.grade(q, rec("No age column.", answerable=False, sql_ok=False))[0])
        self.assertFalse(grading.grade(q, rec("The average age is 33", answerable=True))[0])


class MetricTests(unittest.TestCase):
    def test_pass_at_1_and_pass_pow_k(self):
        # q1: 3/3 pass, q2: 1/3 pass, q3: 0/3
        results = {"q1": [True, True, True], "q2": [True, False, False], "q3": [False, False, False]}
        m = grading.metrics(results)
        self.assertAlmostEqual(m["pass_at_1"], 4 / 9)
        self.assertAlmostEqual(m["pass_pow_k"], 1 / 3)
        self.assertAlmostEqual(m["pass_at_k_any"], 2 / 3)


class FailureTypeTests(unittest.TestCase):
    def test_types(self):
        ans = {"type": "answer", "expected": [120]}
        self.assertEqual(grading.classify_failure(ans, rec("x", status="step_cap")), "step_cap")
        self.assertEqual(grading.classify_failure(ans, rec("x", status="error")), "backend_error")
        self.assertEqual(grading.classify_failure(ans, rec("120", sql_ok=False)), "no_tool_use")
        self.assertEqual(grading.classify_failure(ans, rec("no data", answerable=False)), "wrong_refusal")
        self.assertEqual(grading.classify_failure(ans, rec("7", errors=1, result_rows="[[999]]")), "sql_error_then_wrong")
        self.assertEqual(grading.classify_failure(ans, rec("7", result_rows="[[999]]")), "wrong_sql_logic")
        self.assertEqual(grading.classify_failure(ans, rec("7", result_rows="[[120]]")), "answer_misreported")
        ref = {"type": "refuse", "expected": []}
        self.assertEqual(grading.classify_failure(ref, rec("33", answerable=True)), "hallucinated_answer")


if __name__ == "__main__":
    unittest.main()
