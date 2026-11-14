# Assignment 1 report - SQL calculation agent

Model: `hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M` (Qwen2.5 3B, Ollama, local; the repo default is now the official tag `qwen2.5:3b`, the numbers below were measured with the `hf.co` build). Temperature 0.3, no seed.
18 questions x 3 trials = 54 runs per variant. Step cap 8, token budget 20 000.

## Architecture
```
question -> [agent loop, max 8 steps, 20k tokens]
              model (JSON mode) -> {"tool": ..., "args": ...} | {"final": ..., "answerable": ...}
                 generate_sql(question) -> own model call with schema -> SQL text
                 run_sql(sql)           -> SELECT-only, single statement, read-only SQLite (mode=ro), 50-row limit
                 calculator(expr)       -> safe arithmetic
                 list_tables()          -> tables and columns
              tool result goes back to the model; errors too, so it can retry
         -> status: ok | step_cap | budget_cap | error
```
Design choice: `generate_sql` makes its **own model call** (schema + rules in that prompt), so the agent prompt stays small and the 3B model sees the real column names when writing SQL. Cost: an extra model call per question.
Database: customers (120), products (30), orders (400), order_items (999 rows), seed 42. Expected answers come from independent SQL (`make_questions.py`).

## Numbers (3 trials per question)
| variant | pass@1 | pass^3 | pass@3 (any) | mean tokens/run | mean time/run | statuses |
|---|---|---|---|---|---|---|
| baseline (schema only) | 0.741 (40/54) | 0.556 (10/18) | 0.889 (16/18) | 2538 | 7.6 s | 54 ok |
| improved (rules + examples) | 0.704 (38/54) | 0.500 (9/18) | 0.833 (15/18) | 2971 | 8.5 s | 52 ok, 2 step_cap |

pass@1 = fraction of all 54 runs that passed; pass^3 = fraction of questions that passed all 3 runs. Spread: only 10 of 18 questions are solved 3/3 in baseline (9 of 18 in improved; see `results/*/summary.md` for each question); the rest are flaky, so one run would have been misleading. By category (baseline): simple 12/12, join 12/12, grouping 6/9, calculation 6/15, cannot_answer 4/6 - the multi-step calculation questions are the weak spot.

## Three most common failure types (both variants together, 30 failed runs)
1. **Wrong refusal** (14 runs: 5 baseline, 9 improved): the answer exists but the agent says the data is missing. Example (improved): "What is the name of the most expensive product?" - the SQL writer answered `NOT_AVAILABLE` and the agent concluded "product_name column does not exist" in all 3 runs, although `products.name` exists (baseline solved this 3/3). Another: "How many products are in the Books category?" - the writer invented a `categories` table, the query failed, the agent concluded "The Books category does not exist".
2. **Wrong SQL (logic or SQL errors)** (11 runs: 7 wrong logic + 4 SQL error then wrong): the SQL runs but gives the wrong number, or fails and the retry is also wrong. Example: "What percent of all orders are cancelled?" - baseline divided by the count of *completed or pending* orders only and answered 18.69% in all 3 runs (expected 15.75); one improved run used integer division in SQL and answered 15%. "Average order value" gave $213.40 / 2745% above the minimum instead of $532.97 / 7006.21%.
3. **Hallucinated answer** (2 runs, both baseline; tied with 2 step_cap runs, both improved): on a question the data cannot answer, the agent made up a number. Example: "average age of customers" -> computed "approximately 45279 years" from `signup_date`; "profit margin" -> "$0.0".
(Also: 2 step_cap runs - "average order value" and "profit margin", where the model kept writing new SQL until the cap - and 1 run that answered with the placeholder text "[calculated value]" instead of a number.)

## One change and before/after
Change: the SQL-writer prompt (`SQL_WRITER_IMPROVED`): rules (revenue formula, no invented columns, no status filter, answer `NOT_AVAILABLE` when data is missing) + 3 example queries. Everything else (model, questions, loop) is identical.
- Intended effect: on the 2 "cannot answer" questions the graded pass count went 4/6 -> 5/6 (q17 2/3 -> 3/3, q18 2/3 -> 2/3). Look closer: 2 of the 4 baseline "passes" (q17 trials 1 and 3) set `answerable: false` but still wrote "about 45278 years" in the answer text, and our grader trusts the flag. Read strictly, baseline is about 2/6 -> 5/6, so the real gain on this type is larger than the table suggests.
- Other gains: q09 1/3 -> 2/3, q12 0/3 -> 2/3 (the examples led to a `CAST(... AS REAL)` query), q15 1/3 -> 3/3.
- Losses: q10 3/3 -> 0/3, q02 3/3 -> 1/3, q13 2/3 -> 0/3, q03 3/3 -> 2/3. The `NOT_AVAILABLE` rule made the model refuse questions that are answerable (wrong refusals 5 -> 9 runs).
- Net effect: pass@1 0.741 -> 0.704 (40 -> 38 passing runs); on the 16 answerable questions 36/48 (0.75) -> 33/48 (0.69); pass^3 0.556 -> 0.500; step_cap 0 -> 2; tokens per run +17% (2538 -> 2971).
- Honest conclusion: the change reduced made-up numbers but traded them for wrong refusals, and the net effect is slightly negative. With 3 trials and temperature 0.3, a 1-2 run difference can be noise. We also saw this directly: an earlier full run of the same two variants (its log was overwritten by this re-run) gave pass@1 0.741 / 0.704 again but pass^3 0.556 for both and different per-question results. A next step would be to keep the examples but drop the `NOT_AVAILABLE` shortcut and let the agent decide using the SQL error.
- Surprising case: q10 ("name of the most expensive product") is a one-line query. Baseline got it right 3/3, but with the stricter prompt the writer replied `NOT_AVAILABLE` 3/3 - a longer, more careful prompt made the 3B model worse on the easiest kind of question.

## Limits
Small test set (18 questions), 3 trials, one model, results vary run to run (the numbers above are from the final re-run; yours will be close, not identical). Grading is by number/text match (0.5% tolerance), so a correct answer in an unusual format could be marked wrong. For "cannot answer" questions the grader trusts the model's `answerable: false` flag, so an answer that declines in the flag but still states a number can be graded as a pass.
