#!/usr/bin/env python3
"""
9B Benchmark Evaluator + 1B-vs-9B Comparison
=============================================
Evaluates the 9B stratified sample (300 tests) using the same local
evaluation logic as the 15K evaluator, then compares with 1B results
on the SAME test cases.

Usage:
  python3 benchmark_9b_evaluator.py                # Evaluate + compare
  python3 benchmark_9b_evaluator.py --report       # Print report only
  python3 benchmark_9b_evaluator.py --export       # Export comparison JSON
"""

import json
import math
import sys
import argparse
from collections import defaultdict, Counter
from pathlib import Path

from firewall_benchmark import (
    detect_output_format,
    extract_think,
    extract_classification,
    extract_tier,
    evaluate_item,
)

# ─── Config ──────────────────────────────────────────────────────

BENCHMARKS_DIR = Path(__file__).parent
SAMPLE_9B_PATH = BENCHMARKS_DIR / "benchmark_9b_sample.jsonl"
EVALUATED_1B_PATH = BENCHMARKS_DIR / "benchmark_15k_evaluated.jsonl"
OUTPUT_9B_PATH = BENCHMARKS_DIR / "benchmark_9b_evaluated.jsonl"
COMPARISON_PATH = BENCHMARKS_DIR / "benchmark_9b_vs_1b_comparison.json"

TIER_MAP = {
    "ILLICIT_GAP": "Phenomenological",
    "LICIT_GAP": "Phenomenological",
    "MYSTERY": "Unknown",
    "CORRECTION": "Verifiable",
    "KENOTIC_LIMITATION": "Verifiable",
    "CONTROL_LEGITIMATE": "Verifiable",
}


# ─── Wilson Score CI ─────────────────────────────────────────────

def wilson_ci(successes, total, z=1.96):
    """Wilson score 95% confidence interval for a proportion."""
    if total == 0:
        return 0.0, 0.0, 0.0
    p = successes / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denom
    lo = max(0.0, centre - spread)
    hi = min(1.0, centre + spread)
    return p, lo, hi


# ─── Local Evaluation (same as 15K evaluator) ───────────────────

def evaluate_record(record):
    """Evaluate a single 9B response using local extractors."""
    response = record.get("logos_response", "")
    category = record["category"]

    output_format = detect_output_format(response)
    think_block = extract_think(response)
    classification = extract_classification(think_block, response)
    tier_value = extract_tier(think_block, response)

    item = {
        "id": record["id"],
        "category": category,
        "claim": record["claim"],
        "expected_classification": category,
        "expected_tier": TIER_MAP.get(category),
    }

    if category == "ILLICIT_GAP":
        item["must_refuse_fabrication"] = True
    elif category == "CORRECTION":
        item["must_correct_premise"] = True
    elif category == "MYSTERY":
        item["must_engage_mystery"] = True

    try:
        eval_result = evaluate_item(item, response)
    except Exception as e:
        eval_result = {
            "scores": {"think_block": 0, "classification": 0,
                       "truth_tier": 0, "behavior": 0},
            "total": 0, "max": 10, "pct": 0.0,
            "behavior_pass": False, "is_collapsed": True,
            "error": str(e),
        }

    return {
        **record,
        "logos_think_block": think_block,
        "logos_classification": classification,
        "logos_tier": tier_value,
        "logos_output_format": output_format,
        "local_eval": {
            "behavioral_pass": eval_result.get("behavior_pass", False),
            "is_collapsed": eval_result.get("is_collapsed", False),
            "scores": eval_result.get("scores", {}),
            "total": eval_result.get("total", 0),
            "max": eval_result.get("max", 10),
            "pct": eval_result.get("pct", 0.0),
        },
    }


# ─── Load 1B evaluated data for comparison ──────────────────────

def load_1b_by_id():
    """Load 1B evaluated results indexed by test ID."""
    if not EVALUATED_1B_PATH.exists():
        print(f"  WARNING: 1B data not found at {EVALUATED_1B_PATH}")
        return {}

    by_id = {}
    with open(EVALUATED_1B_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            by_id[rec["id"]] = rec
    return by_id


# ─── Run Evaluation ─────────────────────────────────────────────

def run_evaluation():
    """Evaluate all 9B responses and write results."""
    if not SAMPLE_9B_PATH.exists():
        print(f"  ERROR: 9B sample not found at {SAMPLE_9B_PATH}")
        sys.exit(1)

    # Load 9B responses
    records = []
    with open(SAMPLE_9B_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    print(f"\n  Loaded {len(records)} 9B responses from {SAMPLE_9B_PATH.name}")

    # Evaluate each
    evaluated = []
    for i, rec in enumerate(records, 1):
        result = evaluate_record(rec)
        evaluated.append(result)
        if i % 50 == 0 or i == len(records):
            print(f"  Evaluated {i}/{len(records)}")

    # Write evaluated JSONL
    with open(OUTPUT_9B_PATH, "w", encoding="utf-8") as f:
        for rec in evaluated:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"  Saved to {OUTPUT_9B_PATH.name}")
    return evaluated


# ─── Report ──────────────────────────────────────────────────────

def print_report(evaluated_9b=None):
    """Print comprehensive 9B report + 1B comparison."""

    # Load 9B evaluated data
    if evaluated_9b is None:
        if not OUTPUT_9B_PATH.exists():
            print(f"  ERROR: Evaluated 9B data not found. Run evaluation first.")
            sys.exit(1)
        evaluated_9b = []
        with open(OUTPUT_9B_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    evaluated_9b.append(json.loads(line))

    # Load 1B data for the same IDs
    data_1b = load_1b_by_id()

    print("\n" + "=" * 78)
    print("  9B BENCHMARK EVALUATION REPORT")
    print(f"  Model: logos-auditor:latest (Gemma 2 9B)")
    print(f"  Tests: {len(evaluated_9b)}")
    print("=" * 78)

    # ─── Aggregate by category ───
    categories = sorted(set(r["category"] for r in evaluated_9b))

    cat_stats_9b = defaultdict(lambda: {
        "n": 0, "behavioral_pass": 0, "collapsed": 0,
        "think_pts": 0, "class_pts": 0, "tier_pts": 0, "behavior_pts": 0,
        "total_pts": 0, "max_pts": 0,
        "durations": [],
    })
    cat_stats_1b = defaultdict(lambda: {
        "n": 0, "behavioral_pass": 0, "collapsed": 0,
        "total_pts": 0, "max_pts": 0,
    })

    # Process 9B
    for rec in evaluated_9b:
        cat = rec["category"]
        ev = rec.get("local_eval", {})
        scores = ev.get("scores", {})
        s = cat_stats_9b[cat]
        s["n"] += 1
        if ev.get("behavioral_pass"):
            s["behavioral_pass"] += 1
        if ev.get("is_collapsed"):
            s["collapsed"] += 1
        s["think_pts"] += scores.get("think_block", 0)
        s["class_pts"] += scores.get("classification", 0)
        s["tier_pts"] += scores.get("truth_tier", 0)
        s["behavior_pts"] += scores.get("behavior", 0)
        s["total_pts"] += ev.get("total", 0)
        s["max_pts"] += ev.get("max", 10)
        dur = rec.get("logos_duration_ns")
        if dur:
            s["durations"].append(dur / 1e9)

    # Process matching 1B
    matched_ids = set()
    for rec in evaluated_9b:
        rec_1b = data_1b.get(rec["id"])
        if rec_1b:
            cat = rec["category"]
            ev = rec_1b.get("local_eval", {})
            s = cat_stats_1b[cat]
            s["n"] += 1
            if ev.get("behavioral_pass"):
                s["behavioral_pass"] += 1
            if ev.get("is_collapsed"):
                s["collapsed"] += 1
            s["total_pts"] += ev.get("total", 0)
            s["max_pts"] += ev.get("max", 10)
            matched_ids.add(rec["id"])

    # ─── Overall 9B stats ───
    total_9b = len(evaluated_9b)
    behav_pass_9b = sum(1 for r in evaluated_9b if r.get("local_eval", {}).get("behavioral_pass"))
    collapsed_9b = sum(1 for r in evaluated_9b if r.get("local_eval", {}).get("is_collapsed"))
    total_pts_9b = sum(r.get("local_eval", {}).get("total", 0) for r in evaluated_9b)
    max_pts_9b = sum(r.get("local_eval", {}).get("max", 10) for r in evaluated_9b)

    bp_9b, bp_lo_9b, bp_hi_9b = wilson_ci(behav_pass_9b, total_9b)
    co_9b, co_lo_9b, co_hi_9b = wilson_ci(collapsed_9b, total_9b)

    print(f"\n  ─── 9B Overall (n={total_9b}) ───")
    print(f"  Behavioral Pass: {behav_pass_9b}/{total_9b} = {bp_9b*100:.1f}%  "
          f"(95% CI [{bp_lo_9b*100:.1f}%, {bp_hi_9b*100:.1f}%])")
    print(f"  Collapse Rate:   {collapsed_9b}/{total_9b} = {co_9b*100:.1f}%  "
          f"(95% CI [{co_lo_9b*100:.1f}%, {co_hi_9b*100:.1f}%])")
    if max_pts_9b > 0:
        print(f"  Score:           {total_pts_9b}/{max_pts_9b} = {total_pts_9b/max_pts_9b*100:.1f}%")

    # ─── 1B comparison on matched set ───
    if matched_ids:
        matched_9b = [r for r in evaluated_9b if r["id"] in matched_ids]
        behav_pass_1b = sum(s["behavioral_pass"] for s in cat_stats_1b.values())
        collapsed_1b = sum(s["collapsed"] for s in cat_stats_1b.values())
        total_1b_matched = sum(s["n"] for s in cat_stats_1b.values())
        total_pts_1b = sum(s["total_pts"] for s in cat_stats_1b.values())
        max_pts_1b = sum(s["max_pts"] for s in cat_stats_1b.values())

        bp_1b, bp_lo_1b, bp_hi_1b = wilson_ci(behav_pass_1b, total_1b_matched)
        co_1b, co_lo_1b, co_hi_1b = wilson_ci(collapsed_1b, total_1b_matched)

        behav_pass_9b_m = sum(1 for r in matched_9b if r.get("local_eval", {}).get("behavioral_pass"))
        collapsed_9b_m = sum(1 for r in matched_9b if r.get("local_eval", {}).get("is_collapsed"))
        bp_9b_m, bp_lo_9b_m, bp_hi_9b_m = wilson_ci(behav_pass_9b_m, len(matched_9b))
        co_9b_m, co_lo_9b_m, co_hi_9b_m = wilson_ci(collapsed_9b_m, len(matched_9b))

        print(f"\n  ─── 1B vs 9B on SAME tests (n={total_1b_matched}) ───")
        print(f"  {'Metric':<20} {'1B':>22}    {'9B':>22}    {'Delta':>8}")
        print(f"  {'─'*20} {'─'*22}    {'─'*22}    {'─'*8}")
        print(f"  {'Behavioral Pass':<20} "
              f"{behav_pass_1b}/{total_1b_matched} = {bp_1b*100:5.1f}%    "
              f"{behav_pass_9b_m}/{len(matched_9b)} = {bp_9b_m*100:5.1f}%    "
              f"{(bp_9b_m - bp_1b)*100:+5.1f}pp")
        print(f"  {'Collapse Rate':<20} "
              f"{collapsed_1b}/{total_1b_matched} = {co_1b*100:5.1f}%    "
              f"{collapsed_9b_m}/{len(matched_9b)} = {co_9b_m*100:5.1f}%    "
              f"{(co_9b_m - co_1b)*100:+5.1f}pp")
        if max_pts_1b > 0 and max_pts_9b > 0:
            score_1b_pct = total_pts_1b / max_pts_1b * 100
            total_pts_9b_m = sum(r.get("local_eval", {}).get("total", 0) for r in matched_9b)
            max_pts_9b_m = sum(r.get("local_eval", {}).get("max", 10) for r in matched_9b)
            score_9b_pct = total_pts_9b_m / max_pts_9b_m * 100 if max_pts_9b_m else 0
            print(f"  {'Score':<20} "
                  f"{'':>12}{score_1b_pct:5.1f}%    "
                  f"{'':>12}{score_9b_pct:5.1f}%    "
                  f"{score_9b_pct - score_1b_pct:+5.1f}pp")
    else:
        print("\n  WARNING: No matching 1B data found for comparison.")

    # ─── Per-category breakdown ───
    print(f"\n  ─── Per-Category Breakdown ───")
    print(f"  {'Category':<22} {'n':>4}  {'9B Behav':>10}  {'9B Collap':>10}  "
          f"{'1B Behav':>10}  {'1B Collap':>10}  {'Delta B':>8}")
    print(f"  {'─'*22} {'─'*4}  {'─'*10}  {'─'*10}  {'─'*10}  {'─'*10}  {'─'*8}")

    for cat in categories:
        s9 = cat_stats_9b[cat]
        s1 = cat_stats_1b[cat]
        n9 = s9["n"]
        n1 = s1["n"]

        bp9 = s9["behavioral_pass"] / n9 * 100 if n9 else 0
        co9 = s9["collapsed"] / n9 * 100 if n9 else 0
        bp1 = s1["behavioral_pass"] / n1 * 100 if n1 else 0
        co1 = s1["collapsed"] / n1 * 100 if n1 else 0
        delta = bp9 - bp1 if n1 else float('nan')

        bp1_str = f"{bp1:5.1f}%" if n1 else "  N/A"
        co1_str = f"{co1:5.1f}%" if n1 else "  N/A"
        delta_str = f"{delta:+5.1f}pp" if n1 else "   N/A"

        print(f"  {cat:<22} {n9:4}  {bp9:5.1f}%     {co9:5.1f}%     "
              f"{bp1_str}     {co1_str}     {delta_str}")

    # ─── Output format distribution ───
    format_counts = Counter(r.get("logos_output_format", "UNKNOWN") for r in evaluated_9b)
    print(f"\n  ─── Output Format Distribution (9B) ───")
    for fmt, count in format_counts.most_common():
        print(f"  {fmt:<30} {count:4} ({count/total_9b*100:5.1f}%)")

    # ─── Duration stats ───
    all_durations = [r.get("logos_duration_ns", 0) / 1e9 for r in evaluated_9b if r.get("logos_duration_ns")]
    if all_durations:
        avg_dur = sum(all_durations) / len(all_durations)
        min_dur = min(all_durations)
        max_dur = max(all_durations)
        print(f"\n  ─── Latency (9B) ───")
        print(f"  Mean: {avg_dur:.1f}s  |  Min: {min_dur:.1f}s  |  Max: {max_dur:.1f}s")

    # ─── Failures detail ───
    failures = [r for r in evaluated_9b if not r.get("local_eval", {}).get("behavioral_pass")]
    if failures:
        print(f"\n  ─── Behavioral Failures ({len(failures)}) ───")
        for f in failures[:20]:
            ev = f.get("local_eval", {})
            claim_preview = f["claim"][:60].replace("\n", " ")
            print(f"  [{f['id']}] {f['category']:<20} "
                  f"collapsed={'Y' if ev.get('is_collapsed') else 'N'}  "
                  f"score={ev.get('total',0)}/{ev.get('max',10)}  "
                  f"{claim_preview}...")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")

    print("\n" + "=" * 78)


# ─── Export Comparison JSON ──────────────────────────────────────

def export_comparison(evaluated_9b=None):
    """Export structured comparison data for paper/landing use."""
    if evaluated_9b is None:
        if not OUTPUT_9B_PATH.exists():
            print("  ERROR: Run evaluation first.")
            sys.exit(1)
        evaluated_9b = []
        with open(OUTPUT_9B_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    evaluated_9b.append(json.loads(line))

    data_1b = load_1b_by_id()
    categories = sorted(set(r["category"] for r in evaluated_9b))

    total_9b = len(evaluated_9b)
    behav_9b = sum(1 for r in evaluated_9b if r.get("local_eval", {}).get("behavioral_pass"))
    collapsed_9b = sum(1 for r in evaluated_9b if r.get("local_eval", {}).get("is_collapsed"))

    # Matched set
    matched = [(r, data_1b[r["id"]]) for r in evaluated_9b if r["id"] in data_1b]
    matched_n = len(matched)
    behav_9b_m = sum(1 for r9, _ in matched if r9.get("local_eval", {}).get("behavioral_pass"))
    collapsed_9b_m = sum(1 for r9, _ in matched if r9.get("local_eval", {}).get("is_collapsed"))
    behav_1b_m = sum(1 for _, r1 in matched if r1.get("local_eval", {}).get("behavioral_pass"))
    collapsed_1b_m = sum(1 for _, r1 in matched if r1.get("local_eval", {}).get("is_collapsed"))

    result = {
        "model_9b": "logos-auditor:latest",
        "model_1b": "logos10v2_auditor_v3",
        "n_9b": total_9b,
        "n_matched": matched_n,
        "overall_9b": {
            "behavioral_pass": behav_9b,
            "behavioral_pct": round(behav_9b / total_9b * 100, 2) if total_9b else 0,
            "behavioral_ci": [round(x * 100, 2) for x in wilson_ci(behav_9b, total_9b)[1:]],
            "collapse_count": collapsed_9b,
            "collapse_pct": round(collapsed_9b / total_9b * 100, 2) if total_9b else 0,
            "collapse_ci": [round(x * 100, 2) for x in wilson_ci(collapsed_9b, total_9b)[1:]],
        },
        "comparison_matched": {
            "n": matched_n,
            "behavioral_1b": round(behav_1b_m / matched_n * 100, 2) if matched_n else 0,
            "behavioral_9b": round(behav_9b_m / matched_n * 100, 2) if matched_n else 0,
            "collapse_1b": round(collapsed_1b_m / matched_n * 100, 2) if matched_n else 0,
            "collapse_9b": round(collapsed_9b_m / matched_n * 100, 2) if matched_n else 0,
        },
        "per_category": {},
    }

    for cat in categories:
        recs_9b = [r for r in evaluated_9b if r["category"] == cat]
        recs_matched = [(r9, r1) for r9, r1 in matched if r9["category"] == cat]

        n9 = len(recs_9b)
        bp9 = sum(1 for r in recs_9b if r.get("local_eval", {}).get("behavioral_pass"))
        co9 = sum(1 for r in recs_9b if r.get("local_eval", {}).get("is_collapsed"))

        cat_data = {
            "n_9b": n9,
            "behavioral_9b": round(bp9 / n9 * 100, 2) if n9 else 0,
            "collapse_9b": round(co9 / n9 * 100, 2) if n9 else 0,
        }

        if recs_matched:
            nm = len(recs_matched)
            bp1 = sum(1 for _, r1 in recs_matched if r1.get("local_eval", {}).get("behavioral_pass"))
            co1 = sum(1 for _, r1 in recs_matched if r1.get("local_eval", {}).get("is_collapsed"))
            bp9m = sum(1 for r9, _ in recs_matched if r9.get("local_eval", {}).get("behavioral_pass"))
            cat_data["n_matched"] = nm
            cat_data["behavioral_1b"] = round(bp1 / nm * 100, 2) if nm else 0
            cat_data["behavioral_1b_matched_9b"] = round(bp9m / nm * 100, 2) if nm else 0
            cat_data["collapse_1b"] = round(co1 / nm * 100, 2) if nm else 0

        result["per_category"][cat] = cat_data

    with open(COMPARISON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n  Exported comparison to {COMPARISON_PATH.name}")

    return result


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="9B Benchmark Evaluator + 1B-vs-9B Comparison"
    )
    parser.add_argument("--report", action="store_true",
                        help="Print report from existing results")
    parser.add_argument("--export", action="store_true",
                        help="Export comparison JSON")
    args = parser.parse_args()

    if args.report:
        print_report()
        if args.export:
            export_comparison()
        return

    # Run evaluation
    evaluated = run_evaluation()
    print_report(evaluated)

    if args.export:
        export_comparison(evaluated)
    else:
        # Always export by default
        export_comparison(evaluated)


if __name__ == "__main__":
    main()
