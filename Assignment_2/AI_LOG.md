# AI-assistant log (Assignment 2)

1. **What it wrote:** Claude Code (Sonnet 5.5) wrote the tests first, then `cost.py`, `token_counter.py`, `runner.py`, `compare.py`, `build_dataset.py`, the first draft of the 50 Bangla prompts, and the report/README text; it also reran the experiment on `qwen2.5:3b` after the dataset was corrected.
2. **Which test proves it:** `tests/test_counting_and_cost.py` (template baseline, fresh state, cache retry, dropped-chunk recovery, cost arithmetic), `tests/test_runner_and_compare.py` (same settings for both languages, ratios, bootstrap), `tests/test_dataset.py` (50 aligned pairs); all 21 tests pass.
3. **What I reviewed:** I reviewed and edited the Bangla prompts in `dataset.tsv` myself (the AI had also proofread them twice); I also read the 10-pair quality verdicts in `quality_check.md` (the AI drafted them).
