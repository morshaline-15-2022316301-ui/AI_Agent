"""Notional (made-up) prices from the course. Dollars per million tokens."""
INPUT_PER_M = 0.15
OUTPUT_PER_M = 0.60


def cost_usd(input_tokens, output_tokens):
    return input_tokens * INPUT_PER_M / 1_000_000 + output_tokens * OUTPUT_PER_M / 1_000_000
