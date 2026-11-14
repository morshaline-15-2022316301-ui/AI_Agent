# Quality check - 10 pairs (is the Bangla answer as correct and useful as the English one?)

Model: `qwen2.5:3b`, outputs from `results/results.csv`. Drafted by the AI assistant (Claude Code) from the outputs. One reader's judgement, not a native-speaker panel.

| Pair | English answer | Bangla answer | Verdict |
|---|---|---|---|
| 1 capital of Bangladesh | "The capital of Bangladesh is Dhaka." (correct) | "রাজধানী হল আগ্রা (Dhaka)." (says Agra, then Dhaka) | Bangla worse - wrong/confused |
| 7 independence year | 1971 (correct) | "১৯৭৫ সালে" (wrong year) | Bangla worse - wrong |
| 9 why is the sky blue | correct scattering explanation | nonsense, mixes in Japanese and Korean characters | Bangla worse |
| 13 poem about rain | decent short poem | broken poem, cut by max_tokens | Bangla worse |
| 23 photosynthesis | correct | nonsense definition ("Satzglied"), cut by max_tokens | Bangla worse |
| 31 15 + 27 | 42 | "32 হয়। সমাধান: 15 + 27 = 42" (contradicts itself, adds nonsense) | Bangla worse |
| 34 7 pens at 12 taka | 84 taka | 84 টাকা, with the working shown | equal |
| 39 summarise library sentence | correct | correct ("শুক্রবার মেরামতের জন্য লাইব্রেরি বন্ধ, শনিবার সকালে খুলবে") | equal |
| 45 birthday plan (long) | clear plan | incoherent, cut by max_tokens | Bangla worse |
| 49 average score (long) | 245 / 3 = 81.67 (correct) | computes 81.67 but concludes "80 থেকে কম" (wrong), a stray Chinese character | Bangla worse |

Result: 2 equal, 8 clearly worse. Pattern: only short, simple replies survive (pens, summary); facts, explanations, poems and longer answers are much worse in Bangla for this 3B model.
