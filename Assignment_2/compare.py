"""Compare Bangla with English: per pair, per category and overall. Writes comparison.csv,
summary.json, summary.md and ratio_chart.svg.

    python3 compare.py
"""
import csv
import json
import os
import random
import statistics

import cost
import runner

HERE = os.path.dirname(os.path.abspath(__file__))


def build_pairs(results):
    by = {}
    for r in results:
        by.setdefault(r["id"], {})[r["language"]] = r
    pairs = []
    for pid, d in by.items():
        en, bn = d["english"], d["bangla"]
        en_cost = cost.cost_usd(en["input_tokens"], en["output_tokens"])
        bn_cost = cost.cost_usd(bn["input_tokens"], bn["output_tokens"])
        pairs.append({
            "id": pid, "category": en["category"],
            "en_input": en["input_tokens"], "bn_input": bn["input_tokens"],
            "input_ratio": bn["input_tokens"] / en["input_tokens"],
            "en_net_input": en["net_input_tokens"], "bn_net_input": bn["net_input_tokens"],
            "net_input_ratio": bn["net_input_tokens"] / en["net_input_tokens"],
            "en_output": en["output_tokens"], "bn_output": bn["output_tokens"],
            "output_ratio": bn["output_tokens"] / en["output_tokens"] if en["output_tokens"] else float("nan"),
            "en_cost": en_cost, "bn_cost": bn_cost, "total_cost_ratio": bn_cost / en_cost,
            "en_latency": en["latency_s"], "bn_latency": bn["latency_s"],
            "en_truncated": en.get("truncated", False), "bn_truncated": bn.get("truncated", False),
        })
    return pairs


def bootstrap_ci(values, n=10000, seed=0, alpha=0.05):
    """95% bootstrap interval of the mean."""
    rng = random.Random(seed)
    k = len(values)
    means = sorted(sum(rng.choices(values, k=k)) / k for _ in range(n))
    return means[int(n * alpha / 2)], means[int(n * (1 - alpha / 2)) - 1]


def spread(values):
    lo, hi = bootstrap_ci(values)
    return {"mean": statistics.mean(values), "median": statistics.median(values),
            "min": min(values), "max": max(values), "ci95_low": lo, "ci95_high": hi,
            "stdev": statistics.pstdev(values)}


def by_category(pairs):
    cats = {}
    for p in pairs:
        cats.setdefault(p["category"], []).append(p)
    return {c: {"n": len(ps),
                "input_ratio_mean": statistics.mean(p["input_ratio"] for p in ps),
                "output_ratio_mean": statistics.mean(p["output_ratio"] for p in ps),
                "total_cost_ratio_mean": statistics.mean(p["total_cost_ratio"] for p in ps)}
            for c, ps in cats.items()}


def summarize(pairs):
    s = lambda key: sum(p[key] for p in pairs)
    return {
        "pairs": len(pairs),
        "input_ratio": spread([p["input_ratio"] for p in pairs]),
        "net_input_ratio": spread([p["net_input_ratio"] for p in pairs]),
        "output_ratio": spread([p["output_ratio"] for p in pairs if p["output_ratio"] == p["output_ratio"]]),
        "total_cost_ratio": spread([p["total_cost_ratio"] for p in pairs]),
        "overall_input_ratio": s("bn_input") / s("en_input"),
        "overall_net_input_ratio": s("bn_net_input") / s("en_net_input"),
        "overall_output_ratio": s("bn_output") / s("en_output"),
        "overall_total_cost_ratio": s("bn_cost") / s("en_cost"),
        "total_tokens": {"english_input": s("en_input"), "bangla_input": s("bn_input"),
                         "english_output": s("en_output"), "bangla_output": s("bn_output")},
        "total_cost_usd": {"english": s("en_cost"), "bangla": s("bn_cost"),
                           "english_input_only": cost.cost_usd(s("en_input"), 0),
                           "bangla_input_only": cost.cost_usd(s("bn_input"), 0)},
        "latency": {"english_mean": statistics.mean(p["en_latency"] for p in pairs),
                    "bangla_mean": statistics.mean(p["bn_latency"] for p in pairs)},
        "truncated": {"english": sum(p["en_truncated"] for p in pairs),
                      "bangla": sum(p["bn_truncated"] for p in pairs)},
    }


COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2"]


def chart_svg(pairs, cats):
    """Bar per pair (input-token ratio), coloured by category. Plain SVG, no libraries."""
    names = sorted(cats)
    color = {c: COLORS[i % len(COLORS)] for i, c in enumerate(names)}
    W, H, L, B, T = 900, 420, 50, 50, 40
    top = max(p["input_ratio"] for p in pairs) * 1.1
    bw = (W - L - 20) / len(pairs)
    y = lambda v: H - B - (H - B - T) * v / top
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif" font-size="11">',
           f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<text x="{L}" y="20" font-size="14" font-weight="bold">Bangla / English input-token ratio per pair (1.0 = same cost)</text>']
    for v in range(0, int(top) + 1):
        out.append(f'<line x1="{L}" x2="{W-20}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#ddd"/>'
                   f'<text x="{L-6}" y="{y(v)+4:.1f}" text-anchor="end">{v}x</text>')
    for i, p in enumerate(pairs):
        x = L + i * bw
        out.append(f'<rect x="{x+1:.1f}" y="{y(p["input_ratio"]):.1f}" width="{bw-2:.1f}" '
                   f'height="{H-B-y(p["input_ratio"]):.1f}" fill="{color[p["category"]]}"><title>pair {p["id"]} '
                   f'({p["category"]}): {p["input_ratio"]:.2f}x</title></rect>')
        if i % 5 == 4:
            out.append(f'<text x="{x+bw/2:.1f}" y="{H-B+14}" text-anchor="middle">{p["id"]}</text>')
    out.append(f'<line x1="{L}" x2="{W-20}" y1="{y(1):.1f}" y2="{y(1):.1f}" stroke="black" stroke-dasharray="4"/>')
    mean = statistics.mean(p["input_ratio"] for p in pairs)
    out.append(f'<line x1="{L}" x2="{W-20}" y1="{y(mean):.1f}" y2="{y(mean):.1f}" stroke="#555" stroke-dasharray="2 3"/>'
               f'<text x="{W-24}" y="{y(mean)-4:.1f}" text-anchor="end">mean {mean:.2f}x</text>')
    lx = L
    for c in names:
        cm = cats[c]["input_ratio_mean"]
        out.append(f'<rect x="{lx}" y="{H-22}" width="10" height="10" fill="{color[c]}"/>'
                   f'<text x="{lx+14}" y="{H-13}">{c} (mean {cm:.2f}x)</text>')
        lx += 140
    out.append(f'<text x="{W/2}" y="{H-B+30}" text-anchor="middle">pair id</text></svg>')
    return "\n".join(out)


def to_markdown(s, cats):
    f = lambda d: (f"{d['mean']:.2f} / {d['median']:.2f} / {d['min']:.2f} / {d['max']:.2f} "
                   f"/ [{d['ci95_low']:.2f}, {d['ci95_high']:.2f}]")
    t, c = s["total_tokens"], s["total_cost_usd"]
    L = ["# Summary (auto-generated by compare.py)", "",
         "Spread columns = mean / median / min / max / 95% bootstrap interval of the per-pair ratio.", "",
         "| Measure | English | Bangla | Ratio (Bangla/English) |", "|---|---|---|---|",
         f"| Input tokens, total (gross) | {t['english_input']} | {t['bangla_input']} | {s['overall_input_ratio']:.2f} |",
         f"| Output tokens, total | {t['english_output']} | {t['bangla_output']} | {s['overall_output_ratio']:.2f} |",
         f"| Cost, total (USD, notional) | {c['english']:.6f} | {c['bangla']:.6f} | {s['overall_total_cost_ratio']:.2f} |",
         f"| Input cost only (USD) | {c['english_input_only']:.6f} | {c['bangla_input_only']:.6f} | {s['overall_input_ratio']:.2f} |",
         f"| Latency, mean s/call | {s['latency']['english_mean']:.2f} | {s['latency']['bangla_mean']:.2f} | "
         f"{s['latency']['bangla_mean']/s['latency']['english_mean']:.2f} |",
         f"| Answers cut by max_tokens | {s['truncated']['english']} | {s['truncated']['bangla']} | |", "",
         "| Per-pair ratio | mean / median / min / max / 95% CI |", "|---|---|",
         f"| Input (gross) | {f(s['input_ratio'])} |",
         f"| Input (net, template removed) | {f(s['net_input_ratio'])} |",
         f"| Output | {f(s['output_ratio'])} |",
         f"| Total cost | {f(s['total_cost_ratio'])} |", "",
         "| Category | pairs | mean input ratio | mean output ratio | mean total-cost ratio |", "|---|---|---|---|---|"]
    for name, v in sorted(cats.items(), key=lambda kv: -kv[1]["input_ratio_mean"]):
        L.append(f"| {name} | {v['n']} | {v['input_ratio_mean']:.2f} | {v['output_ratio_mean']:.2f} | "
                 f"{v['total_cost_ratio_mean']:.2f} |")
    return "\n".join(L) + "\n"


def main():
    res_dir = os.path.join(HERE, "results")
    results = runner.read_jsonl(os.path.join(res_dir, "results.jsonl"))
    pairs = build_pairs(results)
    order = {r["id"]: i for i, r in enumerate(runner.load_dataset(os.path.join(HERE, "dataset.tsv")))}
    pairs.sort(key=lambda p: order[p["id"]])
    cats = by_category(pairs)
    s = summarize(pairs)

    cols = ["id", "category", "en_input", "bn_input", "input_ratio", "en_net_input", "bn_net_input",
            "net_input_ratio", "en_output", "bn_output", "output_ratio", "en_cost", "bn_cost", "total_cost_ratio"]
    with open(os.path.join(HERE, "comparison.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for p in pairs:
            w.writerow([round(p[c], 6) if isinstance(p[c], float) else p[c] for c in cols])
    json.dump({"summary": s, "categories": cats}, open(os.path.join(res_dir, "summary.json"), "w"), indent=2)
    md = to_markdown(s, cats)
    open(os.path.join(res_dir, "summary.md"), "w").write(md)
    open(os.path.join(HERE, "ratio_chart.svg"), "w").write(chart_svg(pairs, cats))
    lowest = min(pairs, key=lambda p: p["input_ratio"])
    highest = max(pairs, key=lambda p: p["input_ratio"])
    print(md)
    print(f"lowest input ratio: pair {lowest['id']} {lowest['input_ratio']:.2f}; "
          f"highest: pair {highest['id']} {highest['input_ratio']:.2f}")


if __name__ == "__main__":
    main()
