#!/usr/bin/env python3
"""
Phase 1: 15K Benchmark Runner — Full Response Capture
======================================================
Runs 15,000 test cases against Logos 10 1B via Ollama.
Saves FULL model responses (including <think> blocks) in JSONL format.

Key differences from massive_benchmark_runner.py:
  - num_predict=512 (was 128) — captures full <think> reasoning
  - Saves complete logos_response (was claim_preview[:120])
  - JSONL format (one record per line) for crash resilience
  - Resume by counting existing JSONL lines

Usage:
  python benchmark_15k_runner.py                          # Full run
  python benchmark_15k_runner.py --resume                 # Resume from crash
  python benchmark_15k_runner.py --limit 10               # First 10 only (test)
  python benchmark_15k_runner.py --category ADVERSARIAL   # Single category
  python benchmark_15k_runner.py --model fine_tuned_1b_identity     # Different model
  python benchmark_15k_runner.py --dry-run                # Show what would run
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path

import requests

from modelfile_sweep import query_model_with_config
from dual_firewall import expected_recommendation_for_category

# ─── Config ──────────────────────────────────────────────────────

BENCHMARKS_DIR = Path(__file__).parent
SUITE_PATH = BENCHMARKS_DIR / "massive_benchmark_15k.json"
RESPONSES_PATH = BENCHMARKS_DIR / "benchmark_15k_responses.jsonl"
CHECKPOINT_PATH = BENCHMARKS_DIR / "benchmark_15k_runner_checkpoint.json"

DEFAULT_MODEL = "fine_tuned_1b"

RUNNER_OPTIONS = {
    "temperature": 0.1,
    "num_ctx": 4096,
    "num_predict": 512,     # Modelfile has 256, raised to capture full reasoning
    "repeat_penalty": 1.5,  # Match Modelfile (1.5) — prevents repetition loops
    "top_k": 30,            # Match Modelfile (30, not 40)
    "top_p": 0.9,
}

# Category abbreviation map
CAT_MAP = {
    "ADV": "ADVERSARIAL", "IG": "ILLICIT_GAP", "COR": "CORRECTION",
    "MYS": "MYSTERY", "LG": "LICIT_GAP", "BAP": "BAPTISM_PROTOCOL",
    "KEN": "KENOTIC_LIMITATION", "CTRL": "CONTROL_LEGITIMATE",
}


def get_expected(category):
    """Get expected recommendation for a category."""
    if category == "CONTROL_LEGITIMATE":
        return "PASS"
    return expected_recommendation_for_category(category)


# ─── JSONL I/O ────────────────────────────────────────────────────

def load_completed_ids():
    """Load set of completed test IDs from existing JSONL."""
    ids = set()
    if RESPONSES_PATH.exists():
        with open(RESPONSES_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    ids.add(record["id"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return ids


def append_record(record):
    """Atomic append of one JSONL line."""
    with open(RESPONSES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_checkpoint(completed_count, stats, elapsed):
    """Save lightweight checkpoint for progress tracking."""
    checkpoint = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completed_count": completed_count,
        "elapsed_seconds": round(elapsed, 1),
        "category_stats": {k: dict(v) for k, v in stats.items()},
    }
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


# ─── Runner ──────────────────────────────────────────────────────

def run(model, resume=False, limit=None, category_filter=None, dry_run=False):
    """Run Phase 1: query Logos for all test cases, save full responses."""

    # Load suite
    if not SUITE_PATH.exists():
        print(f"  ERROR: Suite not found at {SUITE_PATH}")
        print(f"  Run: python massive_benchmark_15k_generator.py")
        sys.exit(1)

    with open(SUITE_PATH, encoding="utf-8") as f:
        suite = json.load(f)

    # Apply filters
    if category_filter:
        target_cat = CAT_MAP.get(category_filter.upper(), category_filter.upper())
        suite = [t for t in suite if t["category"] == target_cat]
        print(f"  Filtered to {target_cat}: {len(suite)} tests")

    if limit:
        suite = suite[:limit]

    total = len(suite)

    # Resume: skip already-completed tests
    completed_ids = set()
    if resume:
        completed_ids = load_completed_ids()
        print(f"  Resuming: {len(completed_ids)} already completed")

    remaining = [t for t in suite if t["id"] not in completed_ids]

    if dry_run:
        print(f"\n  DRY RUN — would execute:")
        print(f"    Model: {model}")
        print(f"    Total tests: {total}")
        print(f"    Already done: {len(completed_ids)}")
        print(f"    Remaining: {len(remaining)}")
        print(f"    Options: {RUNNER_OPTIONS}")
        cats = Counter(t["category"] for t in remaining)
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"    {cat:<25} {count:>5}")
        est_hours = len(remaining) * 2.0 / 3600
        print(f"\n    Estimated time: {est_hours:.1f} hours (at ~2s/test)")
        return

    if not remaining:
        print("  All tests already completed!")
        return

    # ─── Main loop ─────────────────────────────────────────────

    stats = defaultdict(lambda: {"correct": 0, "total": 0, "errors": 0})
    start_time = time.time()
    completed_in_session = 0

    print(f"\n{'=' * 74}")
    print(f"  15K BENCHMARK RUNNER — Phase 1 (Full Response Capture)")
    print(f"  Model: {model}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Tests: {len(remaining)} remaining / {total} total")
    print(f"  Options: temp={RUNNER_OPTIONS['temperature']}, "
          f"np={RUNNER_OPTIONS['num_predict']}, "
          f"rp={RUNNER_OPTIONS['repeat_penalty']}")
    print(f"  Output: {RESPONSES_PATH}")
    print(f"{'=' * 74}\n")

    for i, item in enumerate(remaining):
        test_id = item["id"]
        category = item["category"]
        expected = get_expected(category)
        subcategory = item.get("subcategory")

        # Query Logos via Ollama
        error_msg = None
        try:
            result = query_model_with_config(
                model, item["claim"], RUNNER_OPTIONS, None  # Use Modelfile system prompt
            )
            content = result["content"]
            duration_ns = result.get("duration_ns", 0)
        except Exception as e:
            content = f"ERROR: {e}"
            duration_ns = 0
            error_msg = str(e)

        # Build record
        record = {
            "id": test_id,
            "category": category,
            "subcategory": subcategory,
            "claim": item["claim"],
            "expected": expected,
            "logos_response": content,
            "logos_duration_ns": duration_ns,
            "model": model,
            "timestamp": datetime.now().isoformat(),
        }
        if error_msg:
            record["error"] = error_msg

        # Atomic write
        append_record(record)

        # Track stats
        stats[category]["total"] += 1
        if error_msg:
            stats[category]["errors"] += 1
        completed_ids.add(test_id)
        completed_in_session += 1

        # Progress display
        elapsed = time.time() - start_time
        rate = completed_in_session / elapsed if elapsed > 0 else 0
        remaining_count = len(remaining) - (i + 1)
        eta_seconds = remaining_count / rate if rate > 0 else 0
        eta = str(timedelta(seconds=int(eta_seconds)))

        total_done = len(completed_ids)
        has_think = "<think>" in content or "<logos_think>" in content
        think_marker = "T" if has_think else "."
        err_marker = "E" if error_msg else " "

        resp_len = len(content)

        print(f"  [{total_done:>6}/{total}] {test_id:<18} "
              f"{category[:8]:<8} exp={expected:<5} "
              f"{think_marker}{err_marker} "
              f"len={resp_len:>4} "
              f"| {rate:.1f}/s | ETA {eta}")
        sys.stdout.flush()

        # Checkpoint every 100 tests
        if completed_in_session % 100 == 0:
            save_checkpoint(total_done, stats, elapsed)
            total_errors = sum(s["errors"] for s in stats.values())
            print(f"\n  ── Checkpoint ({total_done}/{total}) | "
                  f"Rate: {rate:.2f}/s | "
                  f"Errors: {total_errors} | "
                  f"Elapsed: {timedelta(seconds=int(elapsed))}")
            # Category snapshot
            for cat in sorted(stats.keys()):
                s = stats[cat]
                print(f"     {cat:<25} {s['total']:>5} done"
                      f"  ({s['errors']} errors)")
            print()

        # Small delay to avoid overloading Ollama
        time.sleep(0.02)

    # ─── Final Summary ─────────────────────────────────────────

    elapsed_total = time.time() - start_time
    total_done = len(completed_ids)
    total_errors = sum(s["errors"] for s in stats.values())

    # Clean up checkpoint
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()

    print(f"\n{'=' * 74}")
    print(f"  PHASE 1 COMPLETE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 74}")
    print(f"  Total: {total_done} responses captured")
    print(f"  Errors: {total_errors}")
    print(f"  Elapsed: {timedelta(seconds=int(elapsed_total))}")
    print(f"  Rate: {completed_in_session / elapsed_total:.2f} tests/sec")
    print(f"  Output: {RESPONSES_PATH}")
    print(f"  Size: {RESPONSES_PATH.stat().st_size / (1024 * 1024):.1f} MB")

    print(f"\n  Category breakdown:")
    for cat in sorted(stats.keys()):
        s = stats[cat]
        print(f"    {cat:<25} {s['total']:>5} done  ({s['errors']} errors)")

    print(f"\n  Next step: python benchmark_15k_evaluator.py")
    print(f"{'=' * 74}\n")


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Phase 1: 15K Benchmark Runner — Full Response Capture"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing JSONL")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit to first N tests")
    parser.add_argument("--category", default=None,
                        help="Filter to single category (e.g. ADV, IG, MYS)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would run without executing")

    args = parser.parse_args()

    run(
        model=args.model,
        resume=args.resume,
        limit=args.limit,
        category_filter=args.category,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
