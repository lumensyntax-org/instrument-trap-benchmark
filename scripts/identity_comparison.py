#!/usr/bin/env python3
"""
Identity Comparison Benchmark
==============================
Runs the epistemological firewall benchmark against 3 identity variants
of the same base model (fine_tuned_1b_identity 1B):

  1. fine_tuned_1b_identity  — "Logos Auditor" identity (authority)
  2. fine_tuned_1b_water   — "Water" identity (medium/transport)
  3. fine_tuned_1b_naked   — No system prompt (raw fine-tuned behavior)

Hypothesis: Water identity will show less over-rejection, better MYSTERY
handling, and non-recursive BAPTISM_PROTOCOL responses.

Uses firewall_benchmark.py evaluation functions.
"""

import json
import os
import re
import sys
import time
import requests
from datetime import datetime

# Import evaluation functions from firewall_benchmark
sys.path.insert(0, os.path.dirname(__file__))
from firewall_benchmark import (
    detect_output_format, extract_think, extract_classification,
    extract_tier, evaluate_item, classify_near_match
)

OLLAMA_URL = "http://localhost:11434/api/chat"
SUITE_PATH = os.path.join(os.path.dirname(__file__), "firewall_benchmark.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "identity_comparison_results")

MODELS = [
    ("fine_tuned_1b_identity",  "Authority (trained)"),
    ("fine_tuned_1b_water",   "Water (prompted)"),
    ("fine_tuned_1b_naked",   "Naked (no prompt)"),
    ("fine_tuned_1b_medium",  "Water (trained)"),
]


def query_model(model, claim):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": claim}],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096,
            "num_predict": 384,
            "repeat_penalty": 1.5,
            "top_k": 30,
            "top_p": 0.9
        }
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=90)
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"], data.get("eval_duration", 0)
    except Exception as e:
        return f"ERROR: {e}", 0


def run_single_model(model_name, label, suite):
    """Run benchmark for a single model."""
    print(f"\n{'='*65}")
    print(f"  MODEL: {model_name} ({label})")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*65}\n")

    results = []
    cat_stats = {}

    for i, item in enumerate(suite):
        response, duration = query_model(model_name, item["claim"])
        ev = evaluate_item(item, response)

        entry = {
            "id": item["id"],
            "category": item["category"],
            "claim": item["claim"][:80],
            "response_preview": response[:200],
            "full_response": response,
            "duration_ns": duration,
            "evaluation": ev
        }
        results.append(entry)

        cat = item["category"]
        if cat not in cat_stats:
            cat_stats[cat] = {
                "scores": [], "think": 0, "class_exact": 0,
                "class_near": 0, "behavior_pass": 0,
                "collapsed": 0, "total": 0
            }
        cat_stats[cat]["scores"].append(ev["pct"])
        cat_stats[cat]["total"] += 1
        if ev["think_present"]:
            cat_stats[cat]["think"] += 1
        if ev["found_classification"] and ev["expected_classification"] and \
           ev["found_classification"].upper() == ev["expected_classification"].upper():
            cat_stats[cat]["class_exact"] += 1
        elif ev["found_classification"] and ev["expected_classification"] and \
             classify_near_match(ev["found_classification"].upper(), ev["expected_classification"].upper()):
            cat_stats[cat]["class_near"] += 1
        if ev.get("behavior_pass"):
            cat_stats[cat]["behavior_pass"] += 1
        if ev.get("is_collapsed"):
            cat_stats[cat]["collapsed"] += 1

        cls_mark = "=" if (ev["found_classification"] or "").upper() == (ev["expected_classification"] or "").upper() else "~" if ev["found_classification"] and ev["expected_classification"] and classify_near_match(ev["found_classification"].upper(), ev["expected_classification"].upper()) else "x"
        bhv = "B" if ev.get("behavior_pass") else "."
        fmt = ev.get("output_format", "?")[:8]
        print(f"  [{i+1:2}/{len(suite)}] {item['id']:<8} {ev['pct']:>5.1f}%  "
              f"cls[{cls_mark}]={ev['found_classification'] or '?':<20} "
              f"{bhv} {fmt}")
        sys.stdout.flush()
        time.sleep(0.2)

    return results, cat_stats


def compute_summary(results, cat_stats):
    """Compute summary statistics."""
    n = len(results)
    if n == 0:
        return {}

    overall = sum(r["evaluation"]["pct"] for r in results) / n
    think_n = sum(1 for r in results if r["evaluation"]["think_present"])
    cls_exact = sum(
        1 for r in results
        if r["evaluation"]["found_classification"] and r["evaluation"]["expected_classification"]
        and r["evaluation"]["found_classification"].upper() == r["evaluation"]["expected_classification"].upper()
    )
    cls_near = sum(
        1 for r in results
        if r["evaluation"]["found_classification"] and r["evaluation"]["expected_classification"]
        and r["evaluation"]["found_classification"].upper() != r["evaluation"]["expected_classification"].upper()
        and classify_near_match(r["evaluation"]["found_classification"].upper(), r["evaluation"]["expected_classification"].upper())
    )
    bhv_n = sum(1 for r in results if r["evaluation"].get("behavior_pass"))
    collapse_n = sum(1 for r in results if r["evaluation"].get("is_collapsed"))

    cats = {}
    for cat, s in sorted(cat_stats.items()):
        avg = sum(s["scores"]) / len(s["scores"]) if s["scores"] else 0
        cats[cat] = {
            "avg_pct": round(avg, 1),
            "cls_exact_pct": round(s["class_exact"] / s["total"] * 100, 1) if s["total"] else 0,
            "cls_near_pct": round(s["class_near"] / s["total"] * 100, 1) if s["total"] else 0,
            "behavior_pct": round(s["behavior_pass"] / s["total"] * 100, 1) if s["total"] else 0,
            "structure_pct": round(s["think"] / s["total"] * 100, 1) if s["total"] else 0,
            "collapse_n": s["collapsed"],
            "total": s["total"]
        }

    return {
        "overall_pct": round(overall, 1),
        "classification_exact_pct": round(cls_exact / n * 100, 1),
        "classification_near_pct": round(cls_near / n * 100, 1),
        "classification_total_pct": round((cls_exact + cls_near) / n * 100, 1),
        "behavioral_accuracy_pct": round(bhv_n / n * 100, 1),
        "structure_compliance_pct": round(think_n / n * 100, 1),
        "collapse_rate_pct": round(collapse_n / n * 100, 1),
        "categories": cats
    }


def print_comparison(all_summaries):
    """Print side-by-side comparison."""
    print(f"\n{'='*80}")
    print(f"  IDENTITY COMPARISON — SIDE BY SIDE")
    print(f"{'='*80}\n")

    # Header
    labels = [label for _, label in MODELS]
    header = f"  {'METRIC':<30}"
    for label in labels:
        header += f" {label:>14}"
    print(header)
    print(f"  {'-'*72}")

    # Overall metrics
    metrics = [
        ("Overall Score", "overall_pct"),
        ("Classification (exact)", "classification_exact_pct"),
        ("Classification (total)", "classification_total_pct"),
        ("Behavioral Accuracy", "behavioral_accuracy_pct"),
        ("Structure Compliance", "structure_compliance_pct"),
        ("Collapse Rate", "collapse_rate_pct"),
    ]
    for name, key in metrics:
        row = f"  {name:<30}"
        vals = []
        for model_name, label in MODELS:
            s = all_summaries.get(model_name, {})
            v = s.get(key, 0)
            vals.append(v)
            row += f" {v:>13.1f}%"
        # Mark best
        if key == "collapse_rate_pct":
            best_idx = vals.index(min(vals))
        else:
            best_idx = vals.index(max(vals))
        print(row)
    print()

    # Per-category comparison
    categories = set()
    for model_name, _ in MODELS:
        s = all_summaries.get(model_name, {})
        categories.update(s.get("categories", {}).keys())

    print(f"  {'CATEGORY':<22}", end="")
    for label in labels:
        print(f" {label:>14}", end="")
    print()
    print(f"  {'-'*72}")

    for cat in sorted(categories):
        # Average score
        row = f"  {cat:<22}"
        for model_name, label in MODELS:
            s = all_summaries.get(model_name, {})
            cat_data = s.get("categories", {}).get(cat, {})
            avg = cat_data.get("avg_pct", 0)
            row += f" {avg:>13.1f}%"
        print(row)

        # Behavioral accuracy per category
        row_bhv = f"    {'(behavioral)':<20}"
        for model_name, label in MODELS:
            s = all_summaries.get(model_name, {})
            cat_data = s.get("categories", {}).get(cat, {})
            bhv = cat_data.get("behavior_pct", 0)
            row_bhv += f" {bhv:>13.1f}%"
        print(row_bhv)

    print(f"\n{'='*80}")


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    with open(SUITE_PATH) as f:
        suite = json.load(f)

    print(f"\n  Loaded {len(suite)} test cases from {SUITE_PATH}")
    print(f"  Models: {', '.join(m for m, _ in MODELS)}")

    all_results = {}
    all_summaries = {}

    for model_name, label in MODELS:
        results, cat_stats = run_single_model(model_name, label, suite)
        summary = compute_summary(results, cat_stats)
        all_results[model_name] = results
        all_summaries[model_name] = summary

        # Save per-model results
        out_path = os.path.join(RESULTS_DIR, f"{model_name}_results.json")
        with open(out_path, "w") as f:
            json.dump({
                "model": model_name,
                "label": label,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "summary": summary,
                "details": results
            }, f, indent=2, ensure_ascii=False)
        print(f"\n  Saved: {out_path}")

    # Print comparison
    print_comparison(all_summaries)

    # Save comparison
    comparison_path = os.path.join(RESULTS_DIR, "comparison.json")
    with open(comparison_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hypothesis": "Water identity reduces over-rejection and recursion",
            "models": {m: l for m, l in MODELS},
            "summaries": all_summaries
        }, f, indent=2, ensure_ascii=False)
    print(f"\n  Comparison saved: {comparison_path}")


if __name__ == "__main__":
    main()
