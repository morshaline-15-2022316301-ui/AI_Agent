# AI-assistant log (Assignment 1)

- Claude Code (Sonnet 5.5) wrote the tests first (`tests/`), I ran them and saw them fail (ModuleNotFoundError), then it wrote `build_db.py`, `sql_tools.py`, `agent.py`, `grading.py`.
- Tests that prove the key parts: `test_sql_tools.py` (read-only safety), `test_agent.py` (step cap, budget cap, error retry, bad JSON), `test_grading.py` (pass@1 / pass^3 maths), `test_db.py` (seeded rebuild).
- One test had a mistake (wrong sample data for the `sql_error_then_wrong` case); it was fixed in the test, not in the code. Expected answers in `questions.json` come from independent SQL in `make_questions.py`. I reviewed the code, the questions and the failure analysis.
